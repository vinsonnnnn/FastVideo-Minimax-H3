"""CPU regression tests for the remote reference-to-video boundary and SSH tooling."""

import base64
import importlib.util
import io
import json
import subprocess
import sys
import tarfile
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from dreamverse.remote_studio import MAX_BODY_BYTES, build_mock_clip, create_app

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def reference():
    buffer = io.BytesIO()
    Image.new("RGB", (32, 32), "red").save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()


def test_real_reference_submission_poll_and_range_download(reference):
    calls = []

    def handler(request):
        calls.append(request)
        if request.url.path == "/v1/models":
            return httpx.Response(200, json={"data": [{"id": "fasth3-omniref"}]})
        if request.method == "POST":
            assert json.loads(request.content) == {
                "model": "fasth3-omniref", "prompt": "a person smiles", "seed": 7,
                "image_reference": [{"image_url": reference}],
            }
            return httpx.Response(200, json={"id": "video_123", "status": "queued"})
        if request.url.path.endswith("/content"):
            assert request.headers["range"] == "bytes=0-7"
            return httpx.Response(206, content=b"testclip", headers={
                "Content-Type": "video/mp4", "Content-Range": "bytes 0-7/100", "Accept-Ranges": "bytes",
            })
        return httpx.Response(200, json={"id": "video_123", "status": "completed"})

    with TestClient(create_app(transport=httpx.MockTransport(handler))) as client:
        assert client.get("/api/status").json()["mock"] is False
        job = client.post("/api/generations", json={"prompt": " a person smiles ", "reference": reference, "seed": 7})
        assert job.status_code == 201
        assert client.get("/api/generations/video_123").json()["status"] == "completed"
        download = client.get("/api/generations/video_123/content", headers={"Range": "bytes=0-7"})
        assert download.status_code == 206
        assert download.headers["content-range"] == "bytes 0-7/100"
        assert download.content == b"testclip"
    assert len(calls) == 5


@pytest.mark.parametrize("bad", ["/etc/passwd", "http://127.0.0.1/secret", "data:image/png;base64,!!!",
                                  "data:image/jpeg;base64,dGVzdA=="])
def test_invalid_reference_rejected_before_upstream(bad):
    def unexpected(request):
        pytest.fail("invalid media must not reach the GPU service")
    with TestClient(create_app(transport=httpx.MockTransport(unexpected))) as client:
        assert client.post("/api/generations", json={"prompt": "hello", "reference": bad}).status_code == 400


def test_request_size_and_cross_origin_are_bounded(reference):
    with TestClient(create_app()) as client:
        assert client.post("/api/generations", content=b"x" * (MAX_BODY_BYTES + 1)).status_code == 413
        assert client.post("/api/generations", headers={"Origin": "https://example.com"}, json={
            "prompt": "hello", "reference": reference,
        }).status_code == 403
        assert client.get("/api/status", headers={"Host": "attacker.example"}).status_code == 403


def test_upstream_errors_do_not_retry_submission(reference):
    posts = []

    def handler(request):
        if request.method == "GET":
            return httpx.Response(200, json={"data": [{"id": "fasth3-omniref"}]})
        posts.append(request)
        raise httpx.ReadTimeout("connection lost after server accepted the job")

    with TestClient(create_app(transport=httpx.MockTransport(handler))) as client:
        assert client.post("/api/generations", json={"prompt": "hello", "reference": reference}).status_code == 502
    assert len(posts) == 1


def test_gpu_error_is_preserved(reference):
    def handler(request):
        if request.method == "GET":
            return httpx.Response(200, json={"data": [{"id": "fasth3-omniref"}]})
        return httpx.Response(400, json={"error": {"message": "reference not supported"}})
    with TestClient(create_app(transport=httpx.MockTransport(handler))) as client:
        response = client.post("/api/generations", json={"prompt": "hello", "reference": reference})
        assert response.status_code == 400
        assert response.json()["error"]["message"] == "reference not supported"


def test_mock_is_labeled_and_contains_decodable_audio_video(reference, tmp_path):
    import imageio_ffmpeg
    with TestClient(create_app(mock=True)) as client:
        assert client.get("/api/status").json()["mock"] is True
        assert client.get("/").status_code == 200
        job = client.post("/api/generations", json={"prompt": "hello", "reference": reference}).json()
        assert job["mock"] is True
        path = tmp_path / "clip.mp4"
        path.write_bytes(client.get(f"/api/generations/{job['id']}/content").content)
        subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-v", "error", "-i", str(path), "-map", "0:v:0",
                        "-map", "0:a:0", "-f", "null", "-"], check=True, capture_output=True)
        assert client.get("/api/generations/missing/content").status_code == 404


@pytest.mark.parametrize("value", ["ssh host reboot", "ssh -o ProxyCommand=evil host", "ssh -p 0 host",
                                    "ssh host;touch /tmp/evil", "ssh -- -bad", "ssh -i -bad host"])
def test_ssh_rejects_remote_commands_and_unvalidated_options(value):
    module = load_script("remote5090")
    with pytest.raises(ValueError):
        module.parse_ssh(value)


def test_ssh_and_server_recipe():
    local = load_script("remote5090")
    assert local.parse_ssh("ssh -p 12345 -i '/tmp/key with spaces' root@host")[-1] == "root@host"
    server = load_script("remote5090_server")
    environment = server.server_env(Path("/tmp/remote5090"), None)
    assert environment["FASTVIDEO_H3_ADALN_CACHE"] == "1"
    assert "FASTVIDEO_H3_ADALN_TABLE" not in environment
    table_environment = server.server_env(Path("/tmp/remote5090"), "/tmp/table.pt")
    assert table_environment["FASTVIDEO_H3_ADALN_TABLE"] == "/tmp/table.pt"
    assert "FASTVIDEO_H3_ADALN_CACHE" not in table_environment
    assert table_environment["FASTVIDEO_H3_VSA_FP4_PREFIX"] == "fp8"


def test_dry_run_does_not_connect_or_install():
    result = subprocess.run([sys.executable, str(SCRIPTS / "remote5090.py"), "--ssh", "ssh -p 12345 root@example.com",
                             "--dry-run", "up"], capture_output=True, text=True, check=True)
    plan = json.loads(result.stdout)
    assert plan["remote_port"] == 8000
    assert plan["source_files"] > 0


def test_source_snapshot_omits_keys_weights_and_env_files(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    files = ["apps/example.py", "apps/.env", "apps/secret.key", "apps/weights.safetensors"]
    for name in files:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("private")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    assert load_script("remote5090").source_files(tmp_path) == [Path("apps/example.py")]


def test_source_archive_contains_current_connector_and_pinned_headers(tmp_path):
    module = load_script("remote5090")
    archive_path = tmp_path / "source.tar.gz"
    module.make_archive(module.REPO, archive_path)
    with tarfile.open(archive_path) as archive:
        assert "apps/dreamverse/dreamverse/remote_studio_static/studio.js" in archive.getnames()
        assert "apps/dreamverse/scripts/remote5090_server.py" in archive.getnames()
        modules = json.load(archive.extractfile("remote5090-submodules.json"))
        assert set(modules) == {"fastvideo-kernel/include/cutlass", "fastvideo-kernel/include/tk"}
        assert all(len(spec["revision"]) == 40 for spec in modules.values())


@pytest.mark.parametrize("valid", [True, False])
def test_smoke_only_passes_when_both_media_streams_decode(reference, tmp_path, monkeypatch, valid):
    module = load_script("remote5090")
    image = tmp_path / "reference.png"
    image.write_bytes(base64.b64decode(reference.split(",", 1)[1]))
    clip = tmp_path / "mock.mp4"
    if valid:
        build_mock_clip(clip)
    else:
        clip.write_bytes(b"not an MP4")

    def response(url, payload=None, timeout=30):
        if url.endswith("/models"):
            return {"data": [{"id": "fasth3-omniref"}]}
        assert payload["image_reference"][0]["image_url"].startswith("data:image/png;base64,")
        return {"id": "video_mock_fixture", "status": "completed"}

    monkeypatch.setattr(module, "request_json", response)
    monkeypatch.setattr(module.urllib.request, "urlopen", lambda *a, **kw: io.BytesIO(clip.read_bytes()))
    output = tmp_path / "receipt"
    if valid:
        module.smoke("http://127.0.0.1:18000", image, output, 60)
    else:
        with pytest.raises(subprocess.CalledProcessError):
            module.smoke("http://127.0.0.1:18000", image, output, 60)
    receipt = json.loads((output / "smoke.json").read_text())
    assert receipt["success"] is valid
    assert receipt["job_id"] == "video_mock_fixture"
