"""Remote-side bootstrap for an isolated, loopback-only RTX 5090 API server."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

MODEL_REPO = "FastVideo/FastH3-Omni-NVFP4-QAD"
MODEL_ALIAS = "fasth3-omniref"


def run(command: list[str], **kwargs) -> None:
    print("Running:", " ".join(str(part) for part in command), flush=True)
    subprocess.run(command, check=True, **kwargs)


def doctor(root: Path) -> None:
    """Fail before downloads or builds when native GPU prerequisites are absent."""
    for executable in ("nvidia-smi", "nvcc", "git", "g++"):
        if shutil.which(executable) is None:
            raise RuntimeError(f"Missing {executable}; use an AutoDL CUDA 13 development image.")
    run(["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader"])
    version = subprocess.check_output(["nvcc", "--version"], text=True)
    print(version, flush=True)
    import re
    match = re.search(r"release (\d+)\.", version)
    if match is None or int(match[1]) < 13:
        raise RuntimeError("This bootstrap uses cu130 and requires CUDA Toolkit 13+ (nvcc), not just the driver.")
    target = root if root.exists() else root.parent
    while not target.exists():
        target = target.parent
    print(f"Free disk: {shutil.disk_usage(target).free / 2**30:.1f} GiB", flush=True)
    if Path("/proc/meminfo").exists():
        print(Path("/proc/meminfo").read_text().splitlines()[0], flush=True)
    for limit in ("/sys/fs/cgroup/memory.max", "/sys/fs/cgroup/memory/memory.limit_in_bytes"):
        if Path(limit).exists():
            print(f"Container memory limit: {Path(limit).read_text().strip()}", flush=True)
            break


def bootstrap(root: Path, repo: Path) -> None:
    doctor(root)
    root.mkdir(parents=True, exist_ok=True)
    uv = shutil.which("uv")
    if uv is None:
        tools = root / "tools"
        if not (tools / "bin/python").exists():
            run([sys.executable, "-m", "venv", str(tools)])
        run([str(tools / "bin/python"), "-m", "pip", "install", "uv"])
        uv = str(tools / "bin/uv")
    environment = dict(os.environ, UV_CACHE_DIR=str(root / "uv-cache"))
    venv = root / "venv"
    if not (venv / "bin/python").exists():
        run([uv, "venv", str(venv), "--python", "3.12"], env=environment)
    python = str(venv / "bin/python")
    run([uv, "pip", "install", "--python", python, "--torch-backend", "cu130", "-e", str(repo)], env=environment)
    run([uv, "pip", "install", "--python", python, "scikit-build-core", "cmake", "ninja", "packaging", "setuptools"],
        env=environment)
    # The source archive excludes .git. Restore only pinned kernel headers, not unrelated eval submodules.
    submodules = json.loads((repo / "remote5090-submodules.json").read_text())
    for relative, spec in submodules.items():
        target = repo / relative
        if target.exists() and any(target.iterdir()):
            continue
        target.mkdir(parents=True, exist_ok=True)
        run(["git", "init", str(target)])
        run(["git", "-C", str(target), "fetch", "--depth", "1", spec["url"], spec["revision"]])
        run(["git", "-C", str(target), "checkout", "--detach", "FETCH_HEAD"])
    environment.update({"TORCH_CUDA_ARCH_LIST": "12.0a", "MAX_JOBS": "4"})
    environment["CMAKE_ARGS"] = ("-DCMAKE_CUDA_ARCHITECTURES=120a -DFASTVIDEO_KERNEL_BUILD_TK=OFF "
                                 "-DFASTVIDEO_KERNEL_BUILD_ATTN_QAT_INFER=ON")
    environment["PATH"] = str(venv / "bin") + os.pathsep + environment["PATH"]
    run([uv, "pip", "install", "--python", python, "--no-build-isolation", "--reinstall", "--no-deps",
         str(repo / "fastvideo-kernel")], env=environment, cwd=repo)
    run([python, "-c", "import torch; assert torch.cuda.is_available(); "
         "assert torch.cuda.get_device_capability(0) == (12, 0); "
         "print(torch.cuda.get_device_name(0)); import fastvideo_kernel; import fp4attn_cuda; import fp4quant_cuda"],
        env=environment, cwd=repo)


def prepare(root: Path, repo: Path, model: str, revision: str | None, port: int,
            adaln_table: str | None) -> Path:
    """Download to the persistent cache and write a fully resolved serving config."""
    from huggingface_hub import snapshot_download
    import yaml

    local = Path(model).expanduser()
    if local.is_dir():
        model_dir = local.resolve()
    else:
        model_dir = Path(snapshot_download(repo_id=model, revision=revision, cache_dir=str(root / "hf-cache"),
                                          ignore_patterns=["transformer/*", "vae_decoder_nvfp4/*"]))
    required = ("transformer_ref", "text_encoder", "tokenizer", "processor", "vae", "audio_vae",
                "scheduler", "audio_scheduler", "fastvideo_inference.json")
    missing = [name for name in required if not (model_dir / name).exists()]
    if missing:
        raise RuntimeError(f"Incomplete checkpoint: {missing}. Pass a complete FastVideo-format Omni NVFP4 model.")
    if not (model_dir / "transformer_ref/nvfp4_weights.safetensors").is_file():
        raise RuntimeError("The 5090 path requires the packed NVFP4 transformer_ref export.")
    table = Path(adaln_table).expanduser().resolve() if adaln_table else None
    if table is not None and not table.is_file():
        raise RuntimeError(f"AdaLN table does not exist: {table}")
    decoder = model_dir / "vae_decoder_nvfp4_fast/decoder-nvfp4.safetensors"
    if not decoder.is_file():
        raise RuntimeError(f"Missing fast NVFP4 decoder: {decoder}")
    config = yaml.safe_load((repo / "examples/serving/openai_fasth3_omniref_rtx5090.yaml").read_text())
    config["generator"]["model_path"] = str(model_dir)
    config["generator"]["pipeline"]["vae_tiling"] = True
    config["generator"]["pipeline"]["experimental"]["h3_vae_nvfp4_decoder"] = str(decoder)
    config["server"].update(host="127.0.0.1", port=port, output_dir=str(root / "outputs"))
    config_path = root / "serve-5090.yaml"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False))
    (root / "prepared.json").write_text(json.dumps({
        "model_dir": str(model_dir), "revision": model_dir.name, "adaln_table": str(table) if table else None,
        "repo": str(repo), "port": port,
    }, indent=2))
    return config_path


def server_env(root: Path, table: str | None) -> dict[str, str]:
    environment = dict(os.environ)
    # Do not inherit a different H3 recipe from the SSH login shell.
    for key in tuple(environment):
        if key.startswith(("FASTVIDEO_H3_", "FASTVIDEO_VSA_")):
            environment.pop(key)
    environment.update({
        "CUDA_VISIBLE_DEVICES": "0", "FASTVIDEO_ATTENTION_BACKEND": "VIDEO_SPARSE_ATTN_H3",
        "FASTVIDEO_H3_VSA_FP4": "1", "FASTVIDEO_H3_VSA_FP4_PREFIX": "fp8",
        "FASTVIDEO_H3_VSA_FP4_TWO_LEVEL_P": "1", "FASTVIDEO_H3_VSA_FP4_K_SMOOTH": "1",
        "FASTVIDEO_H3_GATE_CHUNK_ROWS": "8192", "FASTVIDEO_ULYSSES_A2A": "auto",
        "FASTVIDEO_MINIMAX_H3_EXACT_KERNELS": "all", "FASTVIDEO_MINIMAX_H3_FUSIONS": "all",
        "FASTVIDEO_H3_VSA_HEADS_FIRST_TILE": "1", "FASTVIDEO_H3_VAE_TILE_PARALLEL": "1",
        "FASTVIDEO_H3_REF2VA_MEMO_ENTRIES": "16", "FASTVIDEO_VSA_TRITON": "1",
        "FASTVIDEO_VSA_PTX_BLACKWELL": "0", "FASTVIDEO_FA4": "0", "FASTVIDEO_H3_VAE_TILE_BATCH": "4",
    })
    if table:
        environment["FASTVIDEO_H3_ADALN_TABLE"] = table
    else:
        # Supported host cache computes exact modulation on demand. It retains the large CPU projections;
        # unlike a precomputed table it needs no separate calibration artifact but uses more host RAM.
        environment["FASTVIDEO_H3_ADALN_CACHE"] = "1"
    environment["PATH"] = str(root / "venv/bin") + os.pathsep + environment["PATH"]
    return environment


def start(root: Path, repo: Path, port: int, wait_seconds: int) -> None:
    with socket.socket() as probe:
        if probe.connect_ex(("127.0.0.1", port)) == 0:
            raise RuntimeError(f"Port {port} is already occupied. Use connect or a different --remote-port; no process was stopped.")
    settings = json.loads((root / "prepared.json").read_text())
    log_path = root / "server.log"
    with log_path.open("ab") as log:
        process = subprocess.Popen([
            str(root / "venv/bin/fastvideo"), "serve", "--config", str(root / "serve-5090.yaml")
        ], cwd=repo, env=server_env(root, settings["adaln_table"]), stdin=subprocess.DEVNULL,
            stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    (root / "server.pid").write_text(str(process.pid))
    print(f"Server PID {process.pid}; log: {log_path}", flush=True)
    deadline = time.monotonic() + wait_seconds
    while time.monotonic() < deadline:
        if process.poll() is not None:
            print(log_path.read_text(errors="replace")[-12000:], flush=True)
            raise RuntimeError(f"Server exited with {process.returncode}")
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/v1/models", timeout=5) as response:
                result = json.load(response)
            if any(item.get("id") == MODEL_ALIAS for item in result.get("data", [])):
                print("5090 API ready; a successful clip is still required for GPU acceptance.", flush=True)
                return
        except (OSError, ValueError, urllib.error.URLError):
            pass
        print(f"Waiting for model load; see {log_path}", flush=True)
        time.sleep(10)
    raise RuntimeError(f"Startup deadline reached. Server remains running; inspect {log_path} and use connect later.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("doctor", "bootstrap", "launch"))
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--model", default=MODEL_REPO)
    parser.add_argument("--revision")
    parser.add_argument("--adaln-table")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--wait", type=int, default=1800)
    args = parser.parse_args()
    root, repo = args.root.resolve(), args.repo.resolve()
    if args.action == "doctor":
        doctor(root)
    elif args.action == "bootstrap":
        bootstrap(root, repo)
    else:
        prepare(root, repo, args.model, args.revision, args.port, args.adaln_table)
        start(root, repo, args.port, args.wait)


if __name__ == "__main__":
    main()
