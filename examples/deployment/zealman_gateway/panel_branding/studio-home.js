import {createStudioWorkspace} from '/studio-workspace.js';
import {createMembership} from '/studio-members.js';

const $ = (selector, root = document) => root.querySelector(selector);
const escapeHTML = (value) => String(value ?? "").replace(/[&<>"']/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const icons = {
  upload: '<path d="M12 16V3m-5 5 5-5 5 5M4 14v5a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-5"/>',
  download: '<path d="M12 3v13m-5-5 5 5 5-5M4 16v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3"/>',
  book: '<path d="M12 5c-3-2-6-2-10-1v15c4-1 7-1 10 1 3-2 6-2 10-1V4c-4-1-7-1-10 1Zm0 0v15"/>',
  script: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Zm0 0v6h6M8 12h8m-8 4h6"/>',
  cloud: '<path d="M7 18a5 5 0 1 1 1-10 6 6 0 0 1 11 2 4 4 0 0 1-1 8ZM9 13l3-3 3 3m-3-3v10"/>',
  save: '<path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h12l4 4v12a2 2 0 0 1-2 2ZM7 3v6h10V3M7 21v-8h10v8"/>',
  trash: '<path d="M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7m4-7v7"/>',
  refresh: '<path d="M20 7v5h-5M4 17v-5h5M5 8a8 8 0 0 1 13-3l2 2M4 17l2 2a8 8 0 0 0 13-3"/>',
  check: '<path d="m4 12 5 5L20 6"/>',
  home: '<path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1Z"/><path d="M9 21v-8h6v8"/>',
  folder: '<path d="M3 7a2 2 0 0 1 2-2h5l2 2h7a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z"/>',
  image: '<rect x="3" y="3" width="18" height="18" rx="3"/><circle cx="8" cy="8" r="1.5"/><path d="m21 15-5-5L5 21"/>',
  canvas: '<rect x="3" y="3" width="7" height="7" rx="2"/><rect x="14" y="14" width="7" height="7" rx="2"/><path d="M14 6h4v8M6 10v8h8"/>',
  video: '<rect x="3" y="4" width="18" height="16" rx="3"/><path d="m10 8 6 4-6 4Z"/>',
  film: '<rect x="3" y="3" width="18" height="18" rx="3"/><path d="M7 3v18M17 3v18M3 8h4m-4 8h4m10-8h4m-4 8h4"/>',
  person: '<circle cx="12" cy="8" r="4"/><path d="M4 21v-2a8 8 0 0 1 16 0v2"/>',
  audio: '<path d="M3 10v4m4-8v12m5-16v20m5-16v12m4-8v4"/>',
  grid: '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
  sparkle: '<path d="m12 3 2.6 6.4L21 12l-6.4 2.6L12 21l-2.6-6.4L3 12l6.4-2.6Z"/>',
  layers: '<path d="m12 3 10 6-10 6L2 9Z"/><path d="m2 14 10 6 10-6"/>',
  search: '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>',
  arrow: '<path d="M5 12h14m-6-6 6 6-6 6"/>',
  plus: '<path d="M12 4v16M4 12h16"/>',
  chevron: '<path d="m9 5 7 7-7 7"/>',
  settings: '<path d="M4 7h16M4 17h16"/><circle cx="9" cy="7" r="3"/><circle cx="16" cy="17" r="3"/>',
  help: '<circle cx="12" cy="12" r="9"/><path d="M9.5 9a2.5 2.5 0 1 1 4.1 1.9c-1.1.6-1.6 1-1.6 2.6M12 17h.01"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  menu: '<path d="M4 6h16M4 12h16M4 18h16"/>',
  close: '<path d="m6 6 12 12M6 18 18 6"/>',
};
const icon = (name, cls = "") => `<svg class="st-icon ${cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${icons[name] || icons.sparkle}</svg>`;
const tool = (id, label, symbol, page, subPage, hint) => ({id, label, symbol, page, subPage, hint});
const tools = [
  tool("h3", "H3 多参考", "layers", "quick-generate", "u00n-minimax-h3-naonao", "图片与声音，一起进入镜头"),
  tool("ltx", "LTX 音画", "audio", "quick-generate", "j11-ltx23-commercial-avatar", "图像与语音驱动视频"),
  tool("wan", "Wan 动态", "film", "quick-generate", "wan22-smoothmix-v2", "让静态画面动起来"),
  tool("character", "角色设定", "person", "quick-generate", "t4-krea2-character-sheet", "构建角色的统一形象"),
  tool("video", "视频生成", "video", "quick-generate", "u6-minimax-h3-composer", "使用参考素材创作镜头"),
  tool("image", "图像编辑", "image", "quick-generate", "p18-klein9b-drama-multi-edit", "编辑人物、服装和场景"),
  tool("voice", "声音克隆", "audio", "quick-generate", "j-single-voice-clone", "用参考人声生成对白"),
  tool("storyboard", "分镜创作", "grid", "quick-generate", "d14-flux-klein-storyboard", "探索场景与镜头角度"),
  tool("upscale", "画质增强", "sparkle", "quick-generate", "m02-seedvr2-upscale", "为图像补充更多细节"),
];
const state = {view:"home", projects:[], connected:null, count:0, requested:null, lastPage:null};
const workspaceViews = new Set(['novels','scripts','images','export']);
const workspace = createStudioWorkspace({icon,toast,modal,navigate,
  refresh:()=>{if(state.view!=='native')renderSurface();},go:view=>setView(view)});
const memberViews = new Set(['wallet','video-create','member-jobs','members-admin']);
const membership = createMembership({toast,modal,refresh:()=>{if(state.view!=='native')renderSurface();},openView:view=>setView(view)});
let toastTimer;
function toast(message) {
  let el = $("#studio-toast");
  if (!el) { el = document.createElement("div"); el.id="studio-toast"; el.setAttribute("role","status"); document.body.append(el); }
  el.textContent=message;el.classList.add("show");clearTimeout(toastTimer);toastTimer=setTimeout(()=>el.classList.remove("show"),4500);
}
async function getJSON(path) {
  const r=await fetch(path,{cache:"no-store"});
  if (!r.ok) throw new Error(`服务暂不可用（${r.status}）`);
  return r.json();
}
async function waitFor(predicate, timeout=20000) {
  const start=Date.now();
  while (!predicate()) { if (Date.now()-start>timeout) throw new Error("工作台连接超时，请稍后重试"); await new Promise(r=>setTimeout(r,100)); }
}
function setView(view, nativePage) {
  if(view!=='home' && !membership.requireLogin())return;
  if(view==='projects')view='member-jobs';
  state.view=view;
  document.body.classList.toggle("studio-native",view==="native");
  document.body.classList.toggle("studio-home-active",view!=="native");
  document.body.classList.remove("studio-menu-open");
  $("#studio-surface").hidden=view==="native";
  $("#studio-mobile-menu").setAttribute("aria-expanded","false");
  document.querySelectorAll(".st-nav-button").forEach(el=>el.classList.toggle("is-active",el.dataset.view===view || (view==="native"&&el.dataset.page===nativePage)));
  if (view!=="native") { renderSurface(); $("#studio-surface").scrollTop=0; }
  if (workspaceViews.has(view)) workspace.enter(view);
  if(memberViews.has(view))membership.enter(view).catch(error=>toast(error.message));
  else membership.state.view='';
}
async function navigate(page, subPage) {
  if(!membership.requireLogin())return;
  if(page!=='basic-tutorial'){setView(page==='quick-generate'?'video-create':'member-jobs');return;}
  state.requested=page;
  setView("native",page);
  await waitFor(()=>window.__LIANCHENG_NAV_READY__);
  window.dispatchEvent(new CustomEvent("liancheng:navigate",{detail:{page,subPage}}));
}
async function canvas(action="open", detail={}) {
  await navigate("zealman-h3canvas");
  await waitFor(()=>window.__LIANCHENG_CANVAS_READY__);
  return new Promise((resolve,reject)=>{
    const requestId=globalThis.crypto?.randomUUID?.() || String(Date.now());
    const timer=setTimeout(()=>{window.removeEventListener("liancheng:canvas-result",done);reject(new Error("画布未响应，请重新打开"));},15000);
    function done(e) {
      if (e.detail.requestId!==requestId) return;
      clearTimeout(timer);window.removeEventListener("liancheng:canvas-result",done);
      e.detail.error?reject(new Error(e.detail.error)):resolve(e.detail);
    }
    window.addEventListener("liancheng:canvas-result",done);
    window.dispatchEvent(new CustomEvent("liancheng:canvas-project",{detail:{action,...detail,requestId}}));
  });
}
function modal(title, content, onSubmit) {
  const dialog=document.createElement("dialog");dialog.className="st-dialog";
  dialog.setAttribute("aria-label",title);
  dialog.innerHTML=`<form method="dialog"><header><h2>${escapeHTML(title)}</h2><button type="button" data-dismiss aria-label="关闭">${icon("close")}</button></header>${content}</form>`;
  dialog.querySelector("[data-dismiss]").onclick=()=>dialog.close();
  dialog.addEventListener("click",e=>{if(e.target===dialog)dialog.close();});
  dialog.addEventListener("close",()=>dialog.remove());
  const form=dialog.querySelector("form");
  form.addEventListener("submit",async e=>{
    if (!onSubmit) return;
    e.preventDefault();const submit=form.querySelector('[type="submit"]');submit.disabled=true;
    try {await onSubmit(form);dialog.close();} catch(error){toast(error.message);submit.disabled=false;}
  });
  document.body.append(dialog);dialog.showModal();
  return dialog;
}
function createProject() { setView("member-jobs"); }
function dateLabel(timestamp) {
  const d=new Date(Number(timestamp)||timestamp);return Number.isNaN(d.valueOf())?"尚未更新":d.toLocaleDateString("zh-CN",{year:"numeric",month:"2-digit",day:"2-digit"}).replaceAll("/","-");
}
function projectCard(p) {
  const count=Array.isArray(p.nodes)?p.nodes.length:0;
  return `<button class="st-project-card" data-open-project="${escapeHTML(p.id)}"><span class="st-project-thumb">${icon("canvas")}</span><span class="st-project-meta"><strong>${escapeHTML(p.title || "未命名项目")}</strong><span>${dateLabel(p.updatedAt)} <i>·</i> ${count} 个节点</span></span><span class="st-card-arrow">${icon("arrow")}</span></button>`;
}
const features=[
  {tool:"h3",cover:"scene",title:"一个角色，无限种故事",desc:"多图参考 · H3 镜头创作",badge:"视频创作"},
  {tool:"storyboard",cover:"story",title:"让每一格，都有叙事",desc:"角色设定 · 多角度分镜",badge:"角色与分镜"},
  {tool:"voice",cover:"voice",title:"给角色，一个声音",desc:"人声参考 · 对白合成",badge:"声音创作"},
  {tool:"upscale",cover:"detail",title:"细节，值得再多一点",desc:"图像放大 · 画面精修",badge:"画面后期"},
];
function header() {
  return `<header class="st-topbar"><span class="st-top-badge">${icon("sparkle")} 让创作回到想象本身</span><div class="st-top-actions"><button class="st-search-trigger" data-action="search" aria-label="搜索项目和工具">${icon("search")}<span>搜索</span><kbd>⌘ K</kbd></button><button class="st-connection" data-action="refresh-status"><i class="${state.connected===true?"online":state.connected===false?"offline":""}"></i><span>${state.connected===true?"推理服务已连接":state.connected===false?"服务未连接":"正在连接服务"}</span></button><button class="st-avatar" data-action="account" aria-label="工作台信息">Lich</button></div></header>`;
}
function renderSurface() {
  if(memberViews.has(state.view)) {$("#studio-surface").innerHTML=`<div class="st-container">${header()}${membership.render(state.view)}</div>`;membership.renderAccount();return;}
  if (workspaceViews.has(state.view)) {
    $("#studio-surface").innerHTML=`<div class="st-container">${header()}${workspace.render(state.view)}</div>`;
    membership.renderAccount();return;
  }
  const projects=state.view==="projects";
  const cards=(projects?state.projects:state.projects.slice(0,3)).map(projectCard).join("");
  $("#studio-surface").innerHTML=`<div class="st-container">${header()}
    ${projects?'<div class="st-page-heading"><div><span class="st-eyebrow">YOUR STORIES</span><h1>我的项目</h1><p>每一个想法，都可以在这里继续。</p></div><button class="st-button st-button-white" data-action="new-project">'+icon("plus")+' 新建批量项目</button></div>':`<section class="ws-home-hero"><div class="ws-hero-copy"><span class="ws-eyebrow">LICHTV · STORY TO SCREEN</span><h1>让好故事，<br><em>成为好镜头。</em></h1><p>从一页原著，到一场好戏。把人物、分镜与声音，<br class="ws-desktop-break">连接成属于你的短剧。</p><div class="ws-hero-actions"><button class="ws-button ws-primary" data-view="novels">${icon("upload")}上传小说</button><button class="ws-button" data-view="scripts">${icon("script")}剧本创作</button><button class="ws-hero-link" data-action="new-project">新建批量项目 ${icon("arrow")}</button></div><span class="ws-hero-footnote">原著与剧本分别管理 · 连接现有5090工作流</span></div><div class="ws-story-art" aria-hidden="true"><div class="ws-art-orbit"></div><div class="ws-art-page ws-art-page-back"><span>SCENE 01</span><i></i><i></i><i></i><i></i><b>一切，从一个故事开始。</b></div><div class="ws-art-frame"><div class="ws-art-moon"></div><div class="ws-art-hill one"></div><div class="ws-art-hill two"></div><span>LIGHTS. CAMERA. IMAGINATION.</span><b>${icon("film")}第一场 · 雨夜来信</b></div><div class="ws-art-label">${icon("sparkle")}你的下一个故事，正在成形</div></div></section>
    <section class="ws-flow" aria-label="短剧创作流程">${[['01','上传小说','原著导入与阅读','book','data-view="novels"'],['02','剧本创作','场次、对白与镜头','script','data-view="scripts"'],['03','图像创作','角色与场景设定','image','data-view="images"'],['04','批量生成','画布编排多个镜头','canvas','data-action="canvas"'],['05','导出剪映','进入剪辑时间线','film','data-view="export"']].map(([n,title,sub,symbol,attrs])=>`<button ${attrs}><span class="ws-flow-number">${n}</span><span class="ws-flow-icon">${icon(symbol)}</span><span><strong>${title}</strong><small>${sub}</small></span>${icon('chevron')}</button>`).join('')}</section>
    <section class="st-tools" aria-label="创作工具">${tools.map(t=>`<button class="st-tool" data-tool="${t.id}" title="${escapeHTML(t.hint)}"><span class="st-tool-icon">${icon(t.symbol)}</span><strong>${t.label}</strong></button>`).join("")}</section>`}
    <section class="st-project-section"><div class="st-section-heading"><h2>${projects?"全部项目":"最近项目"}<span class="st-count">${state.projects.length}</span></h2>${projects?'':`<button class="st-text-button" data-view="projects">查看全部 ${icon("chevron")}</button>`}</div><div class="st-project-grid">${cards}<button class="st-project-card st-new-project" data-action="new-project"><span class="st-project-thumb">${icon("plus")}</span><span class="st-project-meta"><strong>${state.projects.length?"开启新的故事":"创建你的第一个项目"}</strong><span>在画布里组织角色、场景和镜头</span></span></button></div></section>
    ${projects?"":`<section class="st-feature-section"><div class="st-section-heading"><h2>为你的下一部作品</h2><span class="st-section-note">创作能力，触手可及</span></div><div class="st-feature-grid">${features.map(f=>`<button class="st-feature-card" data-tool="${f.tool}"><span class="st-cover st-cover-${f.cover}"><svg viewBox="0 0 400 225" aria-hidden="true"><use href="/studio-covers.svg#${f.cover}"></use></svg><span class="st-cover-label">LichTV</span><span class="st-cover-arrow">${icon("arrow")}</span></span><span class="st-feature-title">${f.title}<span>${f.badge}</span></span><span class="st-feature-desc">${f.desc}</span></button>`).join("")}</div></section>
    <section class="st-process"><div><span class="st-eyebrow">CREATE YOUR WAY</span><h2>把想法，留在作品里。</h2></div><button data-tool="character"><span>01</span><strong>建立角色</strong><small>角色与场景参考</small>${icon("arrow")}</button><button data-action="canvas"><span>02</span><strong>编排镜头</strong><small>画布与分镜创作</small>${icon("arrow")}</button><button data-page="task-list-management"><span>03</span><strong>查看成片</strong><small>任务进度与产出</small>${icon("arrow")}</button></section>`}
    <footer class="st-home-footer"><span>LichTV · 创作工作台</span><button class="st-text-button" data-page="basic-tutorial">使用指南 ${icon("arrow")}</button></footer></div>`;
  membership.renderAccount();
}
async function loadProjects() {
  if(!membership.state.user)return;
  try {
    const d=await getJSON("/api/h3-canvas");
    const list=d.files?.canvas?.projects;
    state.projects=Array.isArray(list)?[...list].sort((a,b)=>(b.updatedAt||0)-(a.updatedAt||0)):[];
    if(state.view!=="native")renderSurface();
  } catch(error) {toast("项目列表暂时未能加载，点击服务状态可重试");}
}
async function loadStatus() {
  try { const d=await getJSON("/api/comfy/status");state.connected=Boolean(d.running); }
  catch {state.connected=false;}
  document.querySelectorAll(".st-connection").forEach(el=>{el.innerHTML=`<i class="${state.connected?"online":"offline"}"></i><span>${state.connected?"推理服务已连接":"服务未连接"}</span>`;});
  $("#st-sidebar-status").innerHTML=`<i class="${state.connected?"online":"offline"}"></i>${state.connected?"计算服务已连接":"计算服务未连接"}`;
}
function search() {
  const dialog=modal("搜索工作台",'<label class="st-search-field">'+icon("search")+'<input autofocus aria-label="搜索项目或工具" placeholder="搜索项目或创作工具…"></label><div class="st-search-results"></div>');
  const input=dialog.querySelector("input"),results=dialog.querySelector(".st-search-results");
  function render() {
    const query=input.value.trim().toLowerCase();
    const found=[...tools.filter(t=>(t.label+t.hint).toLowerCase().includes(query)).map(t=>({kind:"tool",id:t.id,title:t.label,desc:t.hint})),...state.projects.filter(p=>(p.title||"").toLowerCase().includes(query)).map(p=>({kind:"project",id:p.id,title:p.title||"未命名项目",desc:"画布项目"}))].slice(0,10);
    results.innerHTML=found.length?found.map(x=>`<button type="button" data-result-kind="${x.kind}" data-result-id="${escapeHTML(x.id)}">${icon(x.kind==="project"?"folder":"sparkle")}<span><strong>${escapeHTML(x.title)}</strong><small>${escapeHTML(x.desc)}</small></span>${icon("arrow")}</button>`).join(""):'<p class="st-empty">没有找到匹配的项目或工具</p>';
  }
  input.oninput=render;render();input.focus();
  results.onclick=async e=>{
    const result=e.target.closest("[data-result-kind]");if(!result)return;dialog.close();
    try {if(result.dataset.resultKind==="project")await canvas("open",{id:result.dataset.resultId});else await launchTool(result.dataset.resultId);}catch(error){toast(error.message);}
  };
}
async function launchTool(id) {
  if(!membership.requireLogin())return;
  if(['h3','ltx','wan','video'].includes(id)){setView('video-create');return;}
  if(['image','character','storyboard','upscale'].includes(id)){setView('images');return;}
  toast('声音等高级工作流正在适配账号隔离与积分入口');
}
async function settings() {
  await navigate("system-management");
  await waitFor(()=>[...document.querySelectorAll("#root .app-sidebar button")].some(b=>b.textContent.trim()==="系统设置"));
  [...document.querySelectorAll("#root .app-sidebar button")].find(b=>b.textContent.trim()==="系统设置").click();
}
async function handle(e) {
  const button=e.target.closest("[data-action],[data-tool],[data-page],[data-view],[data-open-project]");
  if(!button || (!button.closest("#studio-sidebar,#studio-surface,#studio-mobile-menu,#studio-scrim,#st-announcement")))return;
  try {
    if(button.dataset.openProject)return await canvas("open",{id:button.dataset.openProject});
    if(button.dataset.tool)return await launchTool(button.dataset.tool);
    if(button.dataset.page)return await navigate(button.dataset.page);
    if(button.dataset.view){setView(button.dataset.view);await loadProjects();return;}
    switch(button.dataset.action){
      case "new-project":createProject();break;
      case "announcement-start":setView('novels');break;
      case "announcement-close":document.body.classList.remove('studio-banner-on');$("#st-announcement").hidden=true;sessionStorage.setItem('lichtv-banner-hidden','1');break;
      case "canvas":await navigate("zealman-h3canvas");break;
      case "search":search();break;
      case "refresh-status":await loadStatus();await loadProjects();break;
      case "menu":document.body.classList.toggle("studio-menu-open");$("#studio-mobile-menu").setAttribute("aria-expanded",String(document.body.classList.contains("studio-menu-open")));break;
      case "close-menu":document.body.classList.remove("studio-menu-open");$("#studio-mobile-menu").setAttribute("aria-expanded","false");break;
      case "tools":$("#st-advanced").hidden=!$("#st-advanced").hidden;button.setAttribute("aria-expanded",String(!$("#st-advanced").hidden));break;
      case "settings":await settings();break;
      case "account":if(membership.state.user)setView('wallet');else membership.auth();break;
    }
  } catch(error){toast(error.message);}
}
async function start() {
  document.documentElement.classList.add("liancheng-creator");
  const sidebar=document.createElement("aside");sidebar.id="studio-sidebar";sidebar.setAttribute("aria-label","工作台导航");
  const nav=(label,symbol,attrs)=>`<button class="st-nav-button" ${attrs}>${icon(symbol)}<span>${label}</span></button>`;
  sidebar.innerHTML=`<button class="st-brand" data-view="home" aria-label="LichTV 首页"><span class="st-brand-mark">Lich</span><strong>LichTV<span>AI STUDIO</span></strong></button><nav>${nav("我的积分","sparkle",'data-view="wallet"')}${nav("用户管理","person",'data-view="members-admin" data-members-admin')}${nav("首页","home",'data-view="home"')}${nav("项目","folder",'data-view="projects"')}${nav("资产","image",'data-page="output-management"')}<p class="st-nav-label">短剧创作</p>${nav("上传小说","book",'data-view="novels"')}${nav("剧本创作","script",'data-view="scripts"')}${nav("图像创作","image",'data-view="images"')}${nav("批量生成","canvas",'data-action="canvas" data-page-nav="zealman-h3canvas"')}${nav("视频生成","video",'data-tool="video"')}${nav("声音创作","audio",'data-tool="voice"')}${nav("导出剪映","film",'data-view="export"')}${nav("任务列表","clock",'data-page="task-list-management"')}<p class="st-nav-label">工作台</p><button class="st-nav-button st-nav-disclosure" data-action="tools" aria-expanded="false">${icon("settings")}<span>高级工具</span>${icon("chevron")}</button><div id="st-advanced" hidden>${nav("API 工作流","layers",'data-page="workflow-to-api"')}${nav("接口文档","film",'data-page="api-docs"')}${nav("常用工具","grid",'data-page="common-tools"')}${nav("媒体对比","image",'data-page="media-compare"')}</div>${nav("使用指南","help",'data-page="basic-tutorial"')}${nav("服务状态","sparkle",'data-page="system-management"')}${nav("系统设置","settings",'data-action="settings"')}</nav><footer><span class="st-sidebar-note">每个想法，都值得成为作品。</span><button id="st-sidebar-status" class="st-sidebar-status" data-action="refresh-status"><i></i>正在连接计算服务</button><span class="st-sidebar-version">LichTV <span>创作工作室</span></span></footer>`;
  const surface=document.createElement("div");surface.id="studio-surface";
  const mobile=document.createElement("button");mobile.id="studio-mobile-menu";mobile.dataset.action="menu";mobile.setAttribute("aria-label","打开导航");mobile.setAttribute("aria-expanded","false");mobile.innerHTML=icon("menu");
  const scrim=document.createElement("button");scrim.id="studio-scrim";scrim.dataset.action="close-menu";scrim.setAttribute("aria-label","关闭导航");
  document.body.append(sidebar,surface,mobile,scrim);
  if(sessionStorage.getItem('lichtv-banner-hidden')!=='1'){
    const banner=document.createElement('div');banner.id='st-announcement';
    banner.innerHTML=`<span class="ws-announcement-brand">LICHTV STUDIO</span><span>好故事，不止于文字。<b>从原著到镜头，在一个工作室继续创作。</b></span><button data-action="announcement-start">开启创作 ${icon('arrow')}</button><button class="ws-announcement-close" data-action="announcement-close" aria-label="关闭宣传栏">${icon('close')}</button>`;
    document.body.append(banner);document.body.classList.add('studio-banner-on');
  }
  document.addEventListener("click",handle);
  document.addEventListener("keydown",e=>{if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==="k"){e.preventDefault();search();}if(e.key==="Escape"){document.body.classList.remove("studio-menu-open");$("#studio-mobile-menu").setAttribute("aria-expanded","false");}});
  window.addEventListener("liancheng:page",e=>{
    const page=e.detail.page,previous=state.lastPage;state.lastPage=page;
    if(state.view==="native"&&previous==="zealman-h3canvas"&&page!=="zealman-h3canvas"&&state.requested!==page){setView("home");loadProjects();return;}
    if(state.requested===page)state.requested=null;
    if(state.view==="native")document.querySelectorAll(".st-nav-button").forEach(el=>el.classList.toggle("is-active",el.dataset.page===page||el.dataset.pageNav===page||tools.some(t=>t.id===el.dataset.tool&&t.page===page&&t.subPage===e.detail.subPage)));
  });
  setView("home");
  try{await membership.bootstrap();if(membership.state.user){await loadProjects();workspace.load().catch(error=>toast(error.message));}}catch(error){toast(error.message);}
  loadStatus();
  setInterval(loadStatus,30000);
  window.addEventListener("focus",()=>{if(state.view==='home'||state.view==='projects')loadProjects();});
}
start();
