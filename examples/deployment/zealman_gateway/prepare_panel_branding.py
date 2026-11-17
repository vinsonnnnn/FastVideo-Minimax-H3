"""Prepare an independent presentation layer for the installed panel bundle.

Original files and third-party license comments are copied without removing
copyright notices. Workflow identifiers, local-storage keys, node classes and
backend paths are deliberately preserved.
"""
import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path


def call_end(source, opening):
    depth = 0
    quote = None
    escaped = False
    for index in range(opening, len(source)):
        char = source[index]
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char in "\"'`":
            quote = char
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return index + 1
    raise ValueError("Unbalanced JSX call; refusing to patch bundle")


def remove_calls(source, tag, matches):
    edits = []
    for match in re.finditer(r"\b[\w$]+\.jsxs?\(\"" + tag + r"\",", source):
        end = call_end(source, source.index("(", match.start()))
        fragment = source[match.start():end]
        if matches(fragment):
            edits.append((match.start(), end))
    # Nested matches must not remove surrounding application components.
    selected = [(start, end) for start, end in edits
                if not any(start < other_start < other_end <= end for other_start, other_end in edits)]
    for start, end in reversed(selected):
        source = source[:start] + "null" + source[end:]
    return source


def patch_bundle(source, name):
    if name.startswith("vendor"):
        return source
    source = re.sub(r'(?<=children:)"(?:ZEALMAN|Zealman)"', '"LichTV"', source)
    if name.startswith("appcomfyuistart-"):
        for old, new in {
            "Started successfully": "让灵感，成为镜头",
            "ComfyUI Start": "开启你的创作空间",
            "ComfyUI已成功启动,打开ComfyUI界面即可开始使用。": "从角色设定到分镜成片，在一个工作台完成创作。",
            "现在您也可以使用API接口进行AI创作。": "生成服务已就绪 · 支持多参考图、对白与音视频创作",
        }.items():
            source = source.replace(old, new)
    # These prose fragments also occur in single-quoted strings and templates.
    for old, new in {
        "Zealman 镜像问题反馈 QQ 群": "平台反馈",
        "Zealman 公共镜像应用": "公共镜像应用",
        "Zealman 镜像机": "镜像实例",
        "zealman镜像API接口说明（v9.0）": "LichTV 工作流接口说明",
        "zealman API 控制台": "LichTV 工作流控制台",
        "Zealman 面板": "制作面板",
        "Zealman H3 中文提示词": "H3 中文提示词",
    }.items():
        source = source.replace(old, new)
    source = remove_calls(source, "a", lambda part: any(value in part for value in [
        "space.bilibili.com/295578108", "pan.quark.cn/s/cde3c555a0a4", "referral_code=",
    ]))
    if name.startswith("About-"):
        source = remove_calls(source, "div", lambda part:
                              'className:"p-5 bg-gray-50' in part[:140]
                              and 'children:"联系与反馈"' in part)
        source = remove_calls(source, "div", lambda part:
                              'className:"p-4 bg-gray-50' in part[:140]
                              and 'children:"镜像大全"' in part)
    if name.startswith("index-"):
        source = re.sub(r'qqGroups:\[\{name:"AutoDL3群".*?\}\]', "qqGroups:[]", source, count=1)
        source = source.replace("qqGroups:Array.isArray(e.qqGroups)?e.qqGroups:Qe.qqGroups", "qqGroups:[]")
        source = re.sub(r'_i=\[\{id:"autodl",label:"AutoDL镜像".*?\}\]', "_i=[]", source, count=1)
        marker = 'const He="quick-generate"===s?d:s;'
        if source.count(marker) != 1:
            raise ValueError("Panel navigation changed; review the adapter before publishing")
        bridge = '''je.useEffect(()=>{const handler=event=>{const detail=event.detail||{};if(typeof detail.page!=="string")return;De(detail.page==="quick-generate"&&typeof detail.subPage==="string"?detail.subPage:detail.page)};window.addEventListener("liancheng:navigate",handler);return()=>window.removeEventListener("liancheng:navigate",handler)},[De]);je.useEffect(()=>{window.__LIANCHENG_NAV_READY__=Boolean(k&&P);return()=>{window.__LIANCHENG_NAV_READY__=false}},[k,P]);je.useEffect(()=>{if(m&&k)window.dispatchEvent(new CustomEvent("liancheng:page",{detail:{page:s,subPage:d}}))},[s,d,m,k]);'''
        source = source.replace(marker, bridge + marker)
    if name.startswith("ApiDocsPage-"):
        source = remove_calls(source, "span", lambda part: '"镜像qq群 "' in part)
        source = re.sub(r'<span class="sub">镜像qq群 \$\{[^}]*\}</span>', "", source)
        source = source.replace("zealman-api-docs-", "lichtv-api-docs-")
        source = source.replace("zealman_00001", "studio_00001").replace("zealman_00002", "studio_00002")
    if name.startswith("WorkflowToAPI-"):
        source = re.sub(r'zealman-ComfyUI QQ群 \$\{[^}]*\}', "LichTV 工作流控制台", source)
    if name.startswith("VideoCanvasPage-"):
        source = remove_calls(source, "div", lambda part: 'className:"h3-qq",' in part[:85])
        source = remove_calls(source, "div", lambda part: 'className:"h3-mirror-links",' in part[:100])
        source = re.sub(r'const Yd=\[\{name:"AutoDL3群".*?\}\];', "const Yd=[];", source, count=1)
        source = source.replace('window.open("https://www.bilibili.com/video/BV1BXp76gEJZ"', 'window.open("/html/tutorial.html"')
        image_help = re.search(r'\bn\.jsx\(zd,\{label:"接口地址在哪？"', source)
        if image_help:
            end = call_end(source, source.index("(", image_help.start()))
            source = source[:image_help.start()] + 'n.jsx("p",{children:"在首页查看工作台接口地址；本机隧道测试使用当前浏览器地址。"})' + source[end:]
        marker = 'return c?n.jsx(jd,{project:c'
        if source.count(marker) != 1:
            raise ValueError("Canvas project controller changed; review the adapter")
        project_bridge = '''e.useEffect(()=>{const handler=async event=>{const action=event.detail||{};const reply=data=>window.dispatchEvent(new CustomEvent("liancheng:canvas-result",{detail:{requestId:action.requestId,...data}}));try{if(action.action==="create"){const project=xs(String(action.title||"未命名项目").slice(0,40));pi(project.id);d({activeId:project.id,projects:[project,...o.projects]});s(project.id);reply({id:project.id})}else if(action.action==="open"){let store=o;const id=action.id||o.activeId||o.projects[0]?.id;if(!store.projects.some(project=>project.id===id)){const files=await nn();if(files?.canvas&&Array.isArray(files.canvas.projects))store=files.canvas}if(!store.projects.some(project=>project.id===id))throw new Error("没有找到该项目，请刷新项目列表");d({...store,activeId:id});s(id);reply({id})}}catch(error){reply({error:error.message||"项目操作失败"})}};window.__LIANCHENG_CANVAS_READY__=true;window.addEventListener("liancheng:canvas-project",handler);return()=>{window.__LIANCHENG_CANVAS_READY__=false;window.removeEventListener("liancheng:canvas-project",handler)}},[o]);'''
        source = source.replace(marker, project_bridge + marker)
    replacements = {
        "炼城 AI": "LichTV",
        "炼成 AI": "LichTV",
        "炼城": "Lich",
        "炼成": "Lich",
        "ZEALMAN": "LichTV",
        "Zealman": "LichTV",
        "Control Panel 3.0": "短剧制作平台",
        "zealman面板地址": "制作平台地址",
        "zealman插件": "工作流插件",
        "zealman API 控制台": "LichTV 工作流控制台",
        "zealman镜像API接口说明（v9.0）": "LichTV 工作流接口说明",
        "Zealman 公共镜像应用": "公共镜像应用",
        "Zealman 面板": "制作面板",
        "MINIMAX-H3 群主随便耍耍版 U00": "MINIMAX-H3 多参考版 U00",
        "MINIMAX-H3 群主无限版 U0X": "MINIMAX-H3 扩展版 U0X",
        "家人们快来看!我跟你们讲,今天找群主定制并发镜像只要100元，先到先得": "欢迎使用语音合成，请输入需要生成的台词。",
        "zealman-h3-batch 格式的 JSON": "批量任务格式的 JSON",
        "将调用本机工作流「U00-minimax_h3提示词QWEN3.8群主版」。": "将调用本机提示词辅助工作流。",
    }

    def literal(match):
        try:
            value = json.loads(match.group())
        except ValueError:
            return match.group()
        original = value
        for old, new in replacements.items():
            if old in ("ZEALMAN", "Zealman", "Control Panel 3.0") and value != old:
                continue
            value = value.replace(old, new)
        if "<d>" in value:
            value = value.replace("群主", "师父")
        return json.dumps(value, ensure_ascii=False) if value != original else match.group()

    return re.sub(r'"(?:[^"\\]|\\.)*"', literal, source)


def version_assets(output):
    """Give every module a fresh URL, including lazy imports and preloads."""
    files = sorted(path for path in (output / "assets").iterdir() if path.suffix in (".js", ".css"))
    digest = hashlib.sha256(Path(__file__).read_bytes())
    for path in files:
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    for name in ("studio.css", "studio-home.js", "studio-home.css", "studio-covers.svg",
                 "studio-workspace.js", "studio-workspace.css", "studio-members.js", "studio-members.css", "studio-checkout.js"):
        digest.update((output / name).read_bytes())
    version = digest.hexdigest()[:12]
    mapping = {path.name: "lc-" + version + "-" + path.name for path in files}
    for path in files + [output / "index.html"]:
        source = path.read_text()
        for old, new in mapping.items():
            source = source.replace(old, new)
        path.write_text(source)
    for path in files:
        path.rename(path.with_name(mapping[path.name]))
    workspace_js = output / "studio-home.js"
    workspace_js.write_text(workspace_js.read_text().replace("/studio-workspace.js'", "/studio-workspace.js?v=" + version + "'"))
    workspace_js.write_text(workspace_js.read_text().replace("/studio-members.js'", "/studio-members.js?v=" + version + "'"))
    checkout_js = output / "studio-members.js"
    checkout_js.write_text(checkout_js.read_text().replace("/studio-checkout.js'", "/studio-checkout.js?v=" + version + "'"))
    index = output / "index.html"
    html = index.read_text().replace("</head>", '<meta name="application-version" content="' + version + '">\n'
                                     '<link rel="stylesheet" href="/studio.css?v=' + version + '">\n'
                                     '<link rel="stylesheet" href="/studio-home.css?v=' + version + '">\n'
                                     '<link rel="stylesheet" href="/studio-workspace.css?v=' + version + '">\n'
                                     '<link rel="stylesheet" href="/studio-members.css?v=' + version + '">\n'
                                     '<script type="module" src="/studio-home.js?v=' + version + '"></script>\n</head>')
    index.write_text(html)
    (output / "release.json").write_text(json.dumps({"version": version, "assets": mapping}, ensure_ascii=False))
    return version


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original", type=Path, help="Exported panel directory containing dist/")
    parser.add_argument("output", type=Path, help="New directory; original export is never modified")
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("Output already exists; choose a new release directory")
    shutil.copytree(args.original / "dist", args.output)
    changed = []
    for path in (args.output / "assets").glob("*.js"):
        before = path.read_text()
        after = patch_bundle(before, path.name)
        if before != after:
            path.write_text(after)
            changed.append(path.name)
    index = args.output / "index.html"
    html = index.read_text().replace('lang="en"', 'lang="zh-CN"')
    html = html.replace("<title>ComfyUI Control Panel</title>", "<title>LichTV</title>")
    html = html.replace('href="/favicon.ico" type="image/x-icon"', 'href="/brand.svg" type="image/svg+xml"')
    theme_boot = "<script>try{if(localStorage.getItem('liancheng-creator-design')!=='1'){localStorage.setItem('zealman-theme','dark');localStorage.setItem('liancheng-creator-design','1')}}catch(e){}</script>"
    html = html.replace('<meta charset="UTF-8" />', '<meta charset="UTF-8" />' + theme_boot)
    index.write_text(html)
    for name in ("qq.png", "avatar.png"):
        (args.output / "image" / name).unlink(missing_ok=True)
    (args.output / "favicon.ico").unlink(missing_ok=True)
    resources = Path(__file__).parent / "panel_branding"
    shutil.copy2(resources / "brand.svg", args.output / "brand.svg")
    shutil.copy2(resources / "studio.css", args.output / "studio.css")
    for name in ("studio-home.js", "studio-home.css", "studio-covers.svg", "studio-workspace.js", "studio-workspace.css", "studio-members.js", "studio-members.css", "studio-checkout.js"):
        shutil.copy2(resources / name, args.output / name)
    (args.output / "html").mkdir(exist_ok=True)
    for name in ("tutorial.html", "tutorial9.html"):
        shutil.copy2(resources / "tutorial.html", args.output / "html" / name)
    version = version_assets(args.output)
    print(json.dumps({"changed_bundles": changed, "count": len(changed), "version": version}, ensure_ascii=False))


if __name__ == "__main__":
    main()
