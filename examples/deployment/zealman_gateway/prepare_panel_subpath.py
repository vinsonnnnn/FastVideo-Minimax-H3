"""Publish an existing branded panel bundle below a URL path.

The source release stays untouched. This adapts static URLs and installs a
browser adapter for dynamic API, upload, media and WebSocket requests.
"""
import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Existing branded release containing index.html")
    parser.add_argument("output", type=Path, help="New release directory")
    parser.add_argument("--base-path", default="/lichtv/")
    args = parser.parse_args()
    base = args.base_path
    if not re.fullmatch(r"/(?:[A-Za-z0-9_-]+/)+", base):
        parser.error("base-path must start and end with / and contain safe directory names")
    if args.output.exists():
        parser.error("output already exists; choose a new release directory")
    if not (args.source / "index.html").is_file():
        parser.error("source must contain index.html")
    shutil.copytree(args.source, args.output)
    resources = Path(__file__).parent / "panel_branding"
    shutil.copy2(resources / "base-path.js", args.output / "base-path.js")
    adapter_hash = hashlib.sha256((args.output / "base-path.js").read_bytes()).hexdigest()
    pattern = re.compile(r"(?<=[\"'`(])/((?:assets|image|html|fonts|libs)/|(?:brand\.svg|studio(?:-home|-workspace|-members|-checkout)?\.(?:js|css)|studio-covers\.svg)(?=[\"'`?#)]))")
    for path in args.output.rglob("*"):
        if path.suffix not in (".html", ".css", ".js"):
            continue
        text = pattern.sub(lambda match: base + match.group(1), path.read_text())
        if "ApiDocsPage-" in path.name:
            text = text.replace("window.location.origin", "(window.location.origin+window.__LICHTV_BASE_PATH__.slice(0,-1))")
        path.write_text(text)
    index = args.output / "index.html"
    html = index.read_text().replace(
        "<head>",
        '<head>\n    <base href="' + base + '">\n'
        '    <script src="' + base + 'base-path.js?v=' + adapter_hash[:12] + '" data-base-path="' + base + '"></script>',
        1,
    )
    index.write_text(html)
    manifest = args.output / "release.json"
    release = json.loads(manifest.read_text()) if manifest.exists() else {}
    release["base_path"] = base
    release["path_adapter_sha256"] = adapter_hash
    manifest.write_text(json.dumps(release, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"base_path": base, "output": str(args.output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
