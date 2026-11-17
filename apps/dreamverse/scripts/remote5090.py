"""Sync this checkout, boot an RTX 5090 API, test a clip, and open a local workbench.

Example: python3 apps/dreamverse/scripts/remote5090.py --ssh 'ssh -p 12345 root@host' up
Uses SSH keys/agent; passwords and private-key contents are never accepted as arguments.
"""

from __future__ import annotations

import argparse
import base64
import contextlib
import datetime
import io
import json
import mimetypes
import os
import re
import shlex
import socket
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SERVER_SCRIPT = "apps/dreamverse/scripts/remote5090_server.py"
SOURCES = {"fastvideo", "fastvideo-kernel", "apps", "examples", "scripts"}
ROOT_FILES = {"pyproject.toml", "uv.lock", "README.md", "LICENSE", "MANIFEST.in", "setup.cfg", "setup.py"}


def parse_ssh(value: str) -> list[str]:
    parts = shlex.split(value)
    if parts and parts[0] == "ssh":
        parts = parts[1:]
    options: list[str] = []
    while parts and parts[0].startswith("-"):
        option = parts.pop(0)
        if option not in {"-p", "-i", "-F", "-J"} or not parts:
            raise ValueError("SSH supports -p PORT, -i KEY_PATH, -F CONFIG and -J JUMP_HOST only; no remote commands.")
        item = parts.pop(0)
        if item.startswith("-") or (option == "-p" and (not item.isdigit() or not 1 <= int(item) <= 65535)):
            raise ValueError(f"Invalid SSH option: {option}")
        options.extend([option, item])
    if len(parts) != 1 or not re.fullmatch(r"[A-Za-z0-9_@.:[\]-]+", parts[0]) or parts[0].startswith("-"):
        raise ValueError("Provide an SSH host or user@host, without a remote command or shell operators.")
    return ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", *options, parts[0]]


def remote(ssh: list[str], command: list[str], **kwargs):
    return subprocess.run([*ssh, shlex.join(command)], check=True, **kwargs)


def source_files(repo: Path) -> list[Path]:
    listed = subprocess.check_output(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=repo)
    paths = []
    for item in listed.decode().split("\0"):
        if not item:
            continue
        relative = Path(item)
        if relative.parts[0] not in SOURCES and item not in ROOT_FILES:
            continue
        if any(part.startswith(".env") or part in {".git", ".aws", ".codex", ".agents", "node_modules", "__pycache__"}
               for part in relative.parts):
            continue
        if relative.suffix in {".pem", ".key", ".pt", ".pth", ".safetensors", ".mp4", ".png", ".jpg", ".jpeg", ".gif"}:
            continue
        if relative.name in {"id_rsa", "id_ed25519", "id_ecdsa", "credentials", "authorized_keys"}:
            continue
        path = repo / relative
        if path.is_file() and not path.is_symlink():
            paths.append(relative)
    return sorted(set(paths))


def make_archive(repo: Path, target: Path) -> None:
    modules = {}
    for name, url in (("cutlass", "https://github.com/NVIDIA/cutlass.git"),
                      ("tk", "https://github.com/HazyResearch/ThunderKittens.git")):
        relative = f"fastvideo-kernel/include/{name}"
        tree = subprocess.check_output(["git", "ls-tree", "HEAD", relative], cwd=repo, text=True)
        if not tree.startswith("160000 commit "):
            raise RuntimeError(f"No pinned git submodule revision for {relative}")
        modules[relative] = {"url": url, "revision": tree.split()[2]}
    with tarfile.open(target, "w:gz") as archive:
        for relative in source_files(repo):
            archive.add(repo / relative, arcname=str(relative), recursive=False)
        payload = json.dumps(modules).encode()
        entry = tarfile.TarInfo("remote5090-submodules.json")
        entry.size = len(payload)
        archive.addfile(entry, io.BytesIO(payload))


def sync(ssh: list[str], root: str) -> str:
    release = root + "/releases/" + datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S%f")
    # Every deployment gets a fresh directory. Existing code, weights and outputs are not deleted.
    extract = ("import pathlib,sys,tarfile; p=pathlib.Path(sys.argv[1]); "
               "p.mkdir(parents=True,exist_ok=False); "
               "tarfile.open(fileobj=sys.stdin.buffer,mode='r|gz').extractall(p)")
    with tempfile.TemporaryDirectory(prefix="fastvideo-sync-") as directory:
        archive = Path(directory) / "source.tar.gz"
        make_archive(REPO, archive)
        print(f"Uploading source ({archive.stat().st_size / 2**20:.1f} MiB) to {release}", flush=True)
        with archive.open("rb") as source:
            remote(ssh, ["python3", "-c", extract, release], stdin=source)
    return release


def local_python() -> Path:
    environment = REPO / ".remote5090-local"
    python = environment / "bin/python"
    if not python.exists():
        subprocess.run([sys.executable, "-m", "venv", str(environment)], check=True)
    subprocess.run([str(python), "-m", "pip", "install", "-r",
                    str(REPO / "apps/dreamverse/remote-studio-requirements.in")], check=True)
    return python


def assert_free(port: int) -> None:
    if not 1 <= port <= 65535:
        raise ValueError("Port must be between 1 and 65535")
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", port))


@contextlib.contextmanager
def tunnel(ssh: list[str], local_port: int, remote_port: int):
    assert_free(local_port)
    # SSH options must precede the destination.
    command = [*ssh[:-1], "-o", "ExitOnForwardFailure=yes", "-o", "ServerAliveInterval=15", "-o",
               "ServerAliveCountMax=3", "-N", "-L", f"127.0.0.1:{local_port}:127.0.0.1:{remote_port}", ssh[-1]]
    process = subprocess.Popen(command, stdin=subprocess.DEVNULL)
    try:
        for _ in range(150):
            if process.poll() is not None:
                raise RuntimeError("SSH tunnel exited; check SSH authentication and forwarding permissions.")
            with socket.socket() as probe:
                if probe.connect_ex(("127.0.0.1", local_port)) == 0:
                    break
            time.sleep(0.1)
        else:
            raise RuntimeError("SSH forwarding did not become ready")
        yield
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def request_json(url: str, payload: dict | None = None, timeout: int = 30) -> dict:
    request = urllib.request.Request(url, data=json.dumps(payload).encode() if payload is not None else None,
                                     headers={"Content-Type": "application/json"})
    try:
        with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(request, timeout=timeout) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code}: {exc.read(8192).decode(errors='replace')}") from exc


def smoke(upstream: str, reference: Path, output: Path, timeout: int) -> None:
    mime = mimetypes.guess_type(reference.name)[0]
    if mime not in {"image/png", "image/jpeg", "image/webp"} or reference.stat().st_size > 15 * 1024 * 1024:
        raise ValueError("Smoke reference must be a PNG/JPEG/WebP image <= 15 MiB")
    models = request_json(upstream + "/v1/models")["data"]
    if len(models) != 1:
        raise RuntimeError("Expected exactly one served model")
    payload = {"model": models[0]["id"], "prompt": "The people in the reference turn toward the camera and smile. "
               "A gentle camera push in, soft room ambience, no scene cut.", "seed": 1234,
               "image_reference": [{"image_url": f"data:{mime};base64," + base64.b64encode(reference.read_bytes()).decode()}]}
    output.mkdir(parents=True, exist_ok=True)
    receipt = {"model": models[0]["id"], "reference": str(reference.resolve()), "seed": 1234,
               "started_at": datetime.datetime.now(datetime.timezone.utc).isoformat(), "success": False}
    receipt_path = output / "smoke.json"
    receipt_path.write_text(json.dumps(receipt, indent=2))
    # A POST is intentionally made once. Timeout does not imply that the server rejected the job.
    job = request_json(upstream + "/v1/videos", payload, timeout=120)
    job_id = job["id"]
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", job_id):
        raise RuntimeError("Invalid job ID from server")
    receipt.update(job_id=job_id, job=job)
    receipt_path.write_text(json.dumps(receipt, indent=2))
    deadline = time.monotonic() + timeout
    while job["status"] in {"queued", "in_progress"}:
        if time.monotonic() >= deadline:
            raise RuntimeError(f"Smoke deadline reached; job {job_id} may still be running. Do not resubmit automatically.")
        print(f"GPU test {job_id}: {job['status']}", flush=True)
        time.sleep(5)
        job = request_json(f"{upstream}/v1/videos/{job_id}")
    receipt["job"] = job
    receipt_path.write_text(json.dumps(receipt, indent=2))
    if job["status"] != "completed":
        raise RuntimeError(f"GPU generation failed: {job.get('error', job)}")
    video = output / f"{job_id}.mp4"
    with urllib.request.urlopen(f"{upstream}/v1/videos/{job_id}/content", timeout=120) as response, video.open("wb") as dest:
        import shutil
        shutil.copyfileobj(response, dest)
    # Decode both streams; a completed job or HTTP 200 alone is not acceptance.
    import imageio_ffmpeg
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-v", "error", "-i", str(video), "-map", "0:v:0", "-map", "0:a:0",
                    "-f", "null", "-"], check=True, timeout=180, capture_output=True)
    receipt.update(success=True, video=str(video.resolve()),
                   completed_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
    receipt_path.write_text(json.dumps(receipt, indent=2))
    print(f"GPU smoke passed: {video}; inspect appearance, speech and continuity manually.", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ssh", help="e.g. 'ssh -p 12345 root@host'")
    parser.add_argument("--remote-root", default="/root/autodl-tmp/fastvideo-5090")
    parser.add_argument("--remote-port", type=int, default=8000)
    parser.add_argument("--tunnel-port", type=int, default=18000)
    parser.add_argument("--web-port", type=int, default=5299)
    parser.add_argument("--reference", type=Path, default=REPO / "assets/images/couple.jpg")
    parser.add_argument("--output", type=Path, default=REPO / "outputs/remote5090")
    parser.add_argument("--model", default="FastVideo/FastH3-Omni-NVFP4-QAD")
    parser.add_argument("--revision", help="Pin a Hugging Face checkpoint revision")
    parser.add_argument("--adaln-table", help="Existing AdaLN table path on the server; otherwise use host caching")
    parser.add_argument("--timeout", type=int, default=3600)
    parser.add_argument("--skip-smoke", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("action", choices=("doctor", "up", "connect", "smoke", "mock"))
    args = parser.parse_args()
    ssh = parse_ssh(args.ssh) if args.ssh else None
    if args.action != "mock" and ssh is None:
        parser.error("--ssh is required")
    if args.action == "mock" and ssh is not None:
        parser.error("mock does not use SSH; omit --ssh")
    if not Path(args.remote_root).is_absolute() or args.remote_root == "/":
        parser.error("--remote-root must be an absolute dedicated directory, not /")
    for port in (args.remote_port, args.tunnel_port, args.web_port):
        if not 1 <= port <= 65535:
            parser.error("ports must be between 1 and 65535")
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    if args.dry_run:
        print(json.dumps({"action": args.action, "ssh": ssh, "remote_root": args.remote_root,
                          "remote_port": args.remote_port, "tunnel_port": args.tunnel_port, "web_port": args.web_port,
                          "model": args.model, "revision": args.revision, "smoke": not args.skip_smoke,
                          "source_files": len(source_files(REPO)), "credentials_uploaded": False}, indent=2))
        return
    if args.action == "doctor":
        # Preflight is read-only and needs no remote checkout.
        script = (REPO / SERVER_SCRIPT).read_bytes()
        remote(ssh, ["python3", "-", "doctor", "--root", args.remote_root, "--repo", args.remote_root], input=script)
        return
    assert_free(args.web_port if args.action != "smoke" else args.tunnel_port)
    if args.action in {"up", "connect"}:
        assert_free(args.tunnel_port)
    python = local_python()
    if args.action == "up":
        if not args.skip_smoke and not args.reference.is_file():
            parser.error("--reference must exist for the GPU smoke test")
        script = (REPO / SERVER_SCRIPT).read_bytes()
        remote(ssh, ["python3", "-", "doctor", "--root", args.remote_root, "--repo", args.remote_root], input=script)
        port_check = ("import socket,sys; s=socket.socket(); "
                      "result=s.connect_ex(('127.0.0.1',int(sys.argv[1]))); s.close(); "
                      "sys.exit('Remote port is occupied; use connect or another --remote-port') if result == 0 else None")
        remote(ssh, ["python3", "-c", port_check, str(args.remote_port)])
        release = sync(ssh, args.remote_root)
        base = [release + "/" + SERVER_SCRIPT]
        common = ["--root", args.remote_root, "--repo", release, "--port", str(args.remote_port)]
        remote(ssh, ["python3", *base, "bootstrap", *common])
        launch = [args.remote_root + "/venv/bin/python", *base, "launch", *common, "--model", args.model,
                  "--wait", str(args.timeout)]
        if args.revision:
            launch.extend(["--revision", args.revision])
        if args.adaln_table:
            launch.extend(["--adaln-table", args.adaln_table])
        remote(ssh, launch)
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(REPO / "apps/dreamverse")
    upstream = f"http://127.0.0.1:{args.tunnel_port}"
    with tunnel(ssh, args.tunnel_port, args.remote_port) if ssh else contextlib.nullcontext():
        if args.action == "smoke" or (args.action == "up" and not args.skip_smoke):
            # Run under the isolated CPU environment, which supplies the FFmpeg binary.
            subprocess.run([str(python), str(Path(__file__).resolve()), "_smoke", upstream, str(args.reference),
                            str(args.output), str(args.timeout)], check=True)
        if args.action != "smoke":
            command = [str(python), "-m", "dreamverse.remote_studio", "--upstream", upstream, "--port", str(args.web_port)]
            if args.action == "mock":
                command.append("--mock")
            print(f"Workbench: http://127.0.0.1:{args.web_port} (Ctrl+C closes the local workbench and tunnel)", flush=True)
            subprocess.run(command, env=environment, check=True)


if __name__ == "__main__":
    try:
        if len(sys.argv) > 1 and sys.argv[1] == "_smoke":
            smoke(sys.argv[2], Path(sys.argv[3]), Path(sys.argv[4]), int(sys.argv[5]))
        else:
            main()
    except KeyboardInterrupt:
        print("Local session closed. The remote GPU service remains running.", file=sys.stderr)
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)
