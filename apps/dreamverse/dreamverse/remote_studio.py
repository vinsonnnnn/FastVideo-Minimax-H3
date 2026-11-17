"""CPU-only reference-to-video workbench for a FastVideo server over SSH."""

from __future__ import annotations

import argparse
import asyncio
import base64
import binascii
import io
import re
import shutil
import subprocess
import tempfile
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlparse

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from PIL import Image
from pydantic import BaseModel, ConfigDict, Field

STATIC_ROOT = Path(__file__).with_name("remote_studio_static")
MAX_BODY_BYTES = 22 * 1024 * 1024
JOB_ID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")


class ShotRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    prompt: str = Field(min_length=1, max_length=12000)
    reference: str
    seed: int = Field(default=1234, ge=0, le=2**32 - 1)


def validate_reference(value: str) -> None:
    """Only accept bounded, decoded still images; no remote URLs or local paths."""
    match = re.fullmatch(r"data:image/(png|jpeg|webp);base64,(.+)", value, re.DOTALL)
    if match is None:
        raise HTTPException(400, "请上传 PNG、JPEG 或 WebP 参考图。")
    try:
        data = base64.b64decode(match[2], validate=True)
        if len(data) > 15 * 1024 * 1024:
            raise ValueError("参考图超过 15 MiB。")
        with Image.open(io.BytesIO(data)) as image:
            expected = {"png": "PNG", "jpeg": "JPEG", "webp": "WEBP"}[match[1]]
            if image.format != expected or getattr(image, "is_animated", False):
                raise ValueError("图片格式与声明不一致，或图片包含动画。")
            if image.width * image.height > 16_777_216:
                raise ValueError("图片超过 1600 万像素。")
            if not 0.25 <= image.width / image.height <= 4:
                raise ValueError("参考图宽高比应介于 1:4 和 4:1。")
            image.verify()
    except (ValueError, OSError, binascii.Error, Image.DecompressionBombError) as exc:
        raise HTTPException(400, f"参考图校验失败：{exc}") from exc


def build_mock_clip(destination: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        try:
            import imageio_ffmpeg
            ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        except ImportError as exc:
            raise RuntimeError("模拟模式需要 ffmpeg 或 imageio-ffmpeg。") from exc
    subprocess.run([
        ffmpeg, "-y", "-v", "error", "-f", "lavfi", "-i", "testsrc2=size=320x192:rate=24", "-f", "lavfi", "-i",
        "sine=frequency=440:sample_rate=24000", "-t", "1", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt",
        "yuv420p", "-c:a", "aac", "-movflags", "+faststart",
        str(destination)
    ],
                   check=True,
                   timeout=60,
                   capture_output=True)


def create_app(upstream: str = "http://127.0.0.1:18000",
               *,
               mock: bool = False,
               transport: httpx.AsyncBaseTransport | None = None) -> FastAPI:
    """The upstream address is operator-owned, never supplied by browser requests."""
    parsed = urlparse(upstream)
    if parsed.scheme not in {"http", "https"
                             } or not parsed.hostname or parsed.username or parsed.query or parsed.fragment:
        raise ValueError("upstream must be an HTTP(S) server URL without credentials, query or fragment")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        with tempfile.TemporaryDirectory(prefix="fastvideo-remote-mock-") as directory:
            app.state.mock_path = Path(directory) / "mock.mp4"
            if mock:
                await asyncio.to_thread(build_mock_clip, app.state.mock_path)
            async with httpx.AsyncClient(base_url=upstream.rstrip("/"),
                                         transport=transport,
                                         timeout=httpx.Timeout(120, connect=10),
                                         trust_env=False,
                                         follow_redirects=False) as client:
                app.state.client = client
                yield

    app = FastAPI(title="FastVideo 5090 remote test", lifespan=lifespan)
    jobs: dict[str, dict] = {}

    @app.middleware("http")
    async def local_browser_only(request: Request, call_next):
        # Bind to loopback and reject cross-site writes, including DNS rebinding.
        if request.url.hostname not in {"127.0.0.1", "localhost", "::1", "testserver"}:
            return JSONResponse({"detail": "Use the localhost workbench address."}, status_code=403)
        origin = request.headers.get("origin")
        if request.method not in {"GET", "HEAD"} and origin and origin != str(request.base_url).rstrip("/"):
            return JSONResponse({"detail": "Cross-origin writes are not supported."}, status_code=403)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        return response

    async def upstream_json(method: str, path: str, **kwargs):
        try:
            result = await app.state.client.request(method, path, **kwargs)
        except httpx.HTTPError as exc:
            raise HTTPException(502, "无法连接推理后端，请检查 SSH 隧道和服务器日志。") from exc
        try:
            body = result.json()
        except ValueError as exc:
            raise HTTPException(502, "推理后端没有返回 JSON，请确认服务地址和端口。") from exc
        if result.is_error:
            return JSONResponse(body, status_code=result.status_code)
        if result.is_redirect:
            raise HTTPException(502, "推理后端返回重定向，请配置最终服务地址。")
        return body

    @app.get("/")
    async def index():
        return FileResponse(STATIC_ROOT / "index.html")

    @app.get("/studio.js")
    async def javascript():
        return FileResponse(STATIC_ROOT / "studio.js")

    @app.get("/api/status")
    async def status():
        if mock:
            return {"mock": True, "model": "mock-pattern", "ready": True}
        result = await upstream_json("GET", "/v1/models")
        if isinstance(result, Response):
            return result
        models = result.get("data", [])
        if len(models) != 1:
            raise HTTPException(502, "测试工作台要求推理服务只暴露一个模型。")
        return {"mock": False, "model": models[0]["id"], "ready": True}

    @app.post("/api/generations", status_code=201)
    async def generate(request: Request):
        # Read incrementally so chunked uploads obey the same cap as Content-Length.
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > MAX_BODY_BYTES:
                raise HTTPException(413, "请求超过 22 MiB。")
        try:
            shot = ShotRequest.model_validate_json(bytes(body))
        except ValueError as exc:
            raise HTTPException(422, "需要 prompt、reference 和有效 seed。") from exc
        if not shot.prompt.strip():
            raise HTTPException(422, "镜头描述不能为空。")
        validate_reference(shot.reference)
        if mock:
            job_id = "mock_" + uuid.uuid4().hex
            jobs[job_id] = {"id": job_id, "status": "completed", "prompt": shot.prompt, "mock": True}
            return jobs[job_id]
        info = await status()
        if isinstance(info, Response):
            return info
        return await upstream_json("POST",
                                   "/v1/videos",
                                   json={
                                       "model": info["model"],
                                       "prompt": shot.prompt.strip(),
                                       "seed": shot.seed,
                                       "image_reference": [{
                                           "image_url": shot.reference
                                       }],
                                   })

    def checked_id(job_id: str) -> str:
        if JOB_ID.fullmatch(job_id) is None:
            raise HTTPException(400, "Invalid job ID")
        return job_id

    @app.get("/api/generations/{job_id}")
    async def retrieve(job_id: str):
        checked_id(job_id)
        if mock:
            if job_id not in jobs:
                raise HTTPException(404, "Job not found")
            return jobs[job_id]
        return await upstream_json("GET", f"/v1/videos/{job_id}")

    @app.get("/api/generations/{job_id}/content")
    async def content(job_id: str, request: Request):
        checked_id(job_id)
        if mock:
            if job_id not in jobs:
                raise HTTPException(404, "Job not found")
            return FileResponse(app.state.mock_path, media_type="video/mp4")
        headers = {key: request.headers[key] for key in ("range", "if-range") if key in request.headers}
        try:
            remote_request = app.state.client.build_request("GET", f"/v1/videos/{job_id}/content", headers=headers)
            remote = await app.state.client.send(remote_request, stream=True)
        except httpx.HTTPError as exc:
            raise HTTPException(502, "视频下载连接失败，请检查 SSH 隧道。") from exc
        if remote.is_error or remote.is_redirect:
            await remote.aclose()
            raise HTTPException(remote.status_code if remote.is_error else 502, "视频暂不可下载。")

        async def chunks() -> AsyncIterator[bytes]:
            try:
                async for chunk in remote.aiter_bytes():
                    yield chunk
            finally:
                await remote.aclose()

        forwarded = {
            key: remote.headers[key]
            for key in ("content-type", "content-range", "accept-ranges", "content-disposition")
            if key in remote.headers
        }
        return StreamingResponse(chunks(), status_code=remote.status_code, headers=forwarded)

    return app


def cli() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream", default="http://127.0.0.1:18000")
    parser.add_argument("--port", type=int, default=5299)
    parser.add_argument("--mock", action="store_true")
    args = parser.parse_args()
    import uvicorn
    uvicorn.run(create_app(args.upstream, mock=args.mock), host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    cli()
