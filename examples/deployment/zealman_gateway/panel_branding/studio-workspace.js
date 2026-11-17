/* Document-first creation workspace; existing GPU APIs remain authoritative. */
export function createStudioWorkspace({icon, toast, modal, navigate, refresh, go}) {
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const state = {novels:[],scripts:[],providers:[],defaults:{},workflows:[],novel:null,script:null,
    imageMode:'local',workflow:null,workflowConfig:null,imagePrompt:'',imageRef:null,imageURL:sessionStorage.getItem('lichtv-last-image')||'',
    selectedVideos:[],videos:[],manualVideos:[],videoURL:'',busy:'',imageStatus:'',draft:null,providerId:null,model:null,imageRatio:'16:9',imageQuality:'0.4',draftTitle:'LichTV短剧',draftRoot:localStorage.getItem('lichtv-draft-root')||'C:\\Users\\Administrator\\AppData\\Local\\JianyingPro\\User Data\\Projects\\com.lveditor.draft',draftRatio:'portrait',view:'home'};
  const service = '/studio-api';
  async function request(path, options={}) {
    const response = await fetch(service + path, {cache:'no-store',...options});
    let data;
    try {data=await response.json();} catch {throw new Error('工作室服务未就绪，请稍后重试');}
    if (!response.ok) throw new Error(typeof data.detail==='string'?data.detail:`请求失败（${response.status}）`);
    return data;
  }
  const json = (method, body) => ({method,headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  async function load() {
    const data=await request('/library');
    Object.assign(state,data);
    const response=await fetch('/api/workflow/list',{cache:'no-store'});
    const list=await response.json();
    state.workflows=(list.workflows||[]).filter(w=>/^API-(A|B|C|D|T)/.test(w.id));
    if(!state.workflow){const selected=state.defaults.image;state.workflow=state.workflows.find(w=>selected?.provider_id==='comfyui'&&w.id===selected.model)||state.workflows.find(w=>w.id.startsWith('API-B18'))||state.workflows[0]||null;if(selected&&selected.provider_id!=='comfyui'){state.imageMode='api';state.providerId=selected.provider_id;state.model=selected.model;}}
    refresh();
  }
  function count(value){return Number(value||0).toLocaleString('zh-CN');}
  function heading(label,title,description,actions=''){
    return `<header class="ws-heading"><div><span class="ws-eyebrow">${label}</span><h1>${title}</h1><p>${description}</p></div><div class="ws-heading-actions">${actions}</div></header>`;
  }
  function button(label,action,symbol='plus',primary=false,extra=''){
    return `<button class="ws-button ${primary?'ws-primary':''}" data-ws-action="${action}" ${extra}>${icon(symbol)}${label}</button>`;
  }
  function empty(symbol,title,description,action=''){
    return `<div class="ws-empty"><span class="ws-empty-icon">${icon(symbol)}</span><h3>${title}</h3><p>${description}</p>${action}</div>`;
  }
  function novelView(){
    const novel=state.novel;
    return heading('STORY LIBRARY','先让一个好故事，住进来。','导入和管理原著，在准备好之后，单独进入剧本创作。',
      button('上传小说','upload-novel','upload',true))+
      `<input type="file" id="ws-novel-file" accept=".txt,.md,.docx,.pdf" hidden>
      <section class="ws-split ws-library-layout"><aside class="ws-panel ws-library"><div class="ws-panel-title"><h2>我的原著 <span>${state.novels.length}</span></h2><span class="ws-soft">共享资料库</span></div>
      <div class="ws-dropzone" data-ws-drop="novel">${icon('upload')}<strong>${state.busy==='upload'?'正在解析文档…':'拖入文件，或点击上传'}</strong><span>TXT / MD / DOCX / PDF · 最大20MiB</span></div>
      <div class="ws-document-list">${state.novels.map(n=>`<button class="ws-document ${novel?.id===n.id?'selected':''}" data-ws-action="open-novel" data-id="${n.id}"><span class="ws-document-icon">${icon('book')}</span><span><strong>${esc(n.title)}</strong><small>${count(n.characters)} 字 · ${n.chapters} 章 · ${esc(n.filename.split('.').pop().toUpperCase())}</small></span>${icon('chevron')}</button>`).join('')||'<p class="ws-list-empty">还没有上传原著</p>'}</div></aside>
      <article class="ws-panel ws-reader">${novel?`<header class="ws-reader-header"><div><span class="ws-tag">原著正文</span><h2>${esc(novel.title)}</h2><p>${count(novel.characters)} 字 · ${novel.chapters} 章</p></div>${button('进入剧本创作','novel-to-script','arrow',true)}</header><pre class="ws-novel-text">${esc(novel.text)}</pre><footer class="ws-reader-footer"><span>原文和改编剧本分别保存</span>${button('移除这份原著','delete-novel','trash')}</footer>`:
        empty('book','每一个镜头，都从故事开始','上传小说后可在这里阅读原文。扫描版PDF请先识别文字。',button('选择原著文件','upload-novel','upload',true))}</article></section>`;
  }
  function sceneRows(text){
    return String(text||'').split(/\n\s*\n/).map(s=>s.trim()).filter(Boolean).map((s,i)=>({index:i+1,text:s}));
  }
  function scriptView(){
    const script=state.script;
    return heading('SCRIPT ROOM','把文字，写成看得见的场景。','原著导入与剧本创作分开；可独立写作，也可选择原著建立改编草稿。',
      button('新建剧本','new-script','plus',true))+
      `<section class="ws-split ws-script-layout"><aside class="ws-panel ws-script-rail"><div class="ws-panel-title"><h2>剧本库 <span>${state.scripts.length}</span></h2></div>
      <label class="ws-label">从原著开始<select id="ws-source-novel"><option value="">选择一份已上传的小说</option>${state.novels.map(n=>`<option value="${n.id}" ${state.novel?.id===n.id?'selected':''}>${esc(n.title)}</option>`).join('')}</select></label>
      <div class="ws-rail-actions">${button('建立改编草稿','seed-script','book')}${button('AI改编','adapt-script','sparkle',false,state.busy==='adapt'?'disabled':'')}</div>
      <p class="ws-helper">建立草稿不调用模型；AI改编需要先配置文本API。</p>
      <div class="ws-document-list">${state.scripts.map(s=>`<button class="ws-document ${script?.id===s.id?'selected':''}" data-ws-action="open-script" data-id="${s.id}"><span class="ws-document-icon">${icon('script')}</span><span><strong>${esc(s.title)}</strong><small>${count(s.text.length)} 字 · ${new Date(s.updated_at).toLocaleDateString('zh-CN')}</small></span></button>`).join('')||'<p class="ws-list-empty">还没有保存的剧本</p>'}</div>
      ${button('配置文本模型','text-models','settings')}</aside>
      <article class="ws-panel ws-editor">${script?`<header class="ws-editor-header"><div class="ws-editor-title"><span class="ws-tag">剧本正文</span><input id="ws-script-title" aria-label="剧本名称" maxlength="120" value="${esc(script.title)}"></div><div>${button(state.busy==='save'?'保存中…':'保存剧本','save-script','save',true,state.busy==='save'?'disabled':'')}</div></header>
      <div class="ws-writing-bar"><span>场次 · 内外景 · 动作 · 对白 · 镜头建议</span><span id="ws-script-count">${count(script.text.length)} 字</span></div>
      <textarea id="ws-script-text" class="ws-script-text" spellcheck="false" placeholder="在这里写下第一场戏…">${esc(script.text)}</textarea>
      <footer class="ws-editor-footer"><div>${button('导出TXT','download-script','download')}${button('导出分镜CSV','download-scenes','grid')}${button('删除','delete-script','trash')}</div>${button('打开批量生成','open-batch','arrow',true)}</footer><p class="ws-helper ws-editor-tip">分镜CSV按段落整理供你编辑；复制镜头描述后，可在批量生成画布中继续编排。</p>`:
      empty('script','给你的故事，写下第一场戏','新建空白剧本，或从左侧选取原著建立草稿。',button('新建剧本','new-script','plus',true))}</article></section>`;
  }
  function imageView(){
    const current=state.workflow;
    const providers=state.providers.filter(p=>p.kind==='image');
    const selected=state.defaults.image;
    const provider=providers.find(p=>p.id===(state.providerId||selected?.provider_id));
    return heading('VISUAL STUDIO','让角色与场景，先有一个模样。','本机ComfyUI工作流与外部API分开选择，模型来源与配置状态清晰可见。',
      button('模型与API分组','image-models','settings'))+
      `<section class="ws-panel ws-image-studio"><div class="ws-image-toolbar"><div class="ws-segment"><button data-ws-action="image-local" class="${state.imageMode==='local'?'selected':''}">${icon('layers')}ComfyUI 工作流</button><button data-ws-action="image-api" class="${state.imageMode==='api'?'selected':''}">${icon('cloud')}API 生图</button></div><span class="ws-tag ${state.imageMode==='local'?'ws-green':''}">${state.imageMode==='local'?'本机工作流':provider?'已配置API分组':'尚未配置API'}</span></div>
      <div class="ws-image-grid"><aside class="ws-image-controls">${state.imageMode==='local'?`<label class="ws-label">选择生图工作流<select id="ws-image-workflow">${state.workflows.map(w=>`<option value="${esc(w.id)}" ${current?.id===w.id?'selected':''}>${esc(w.name||w.id)}</option>`).join('')}</select></label><p class="ws-helper">直接调用当前5090上的已注册工作流。模型、采样与后处理沿用所选模板。</p>`:
      `<label class="ws-label">API分组<select id="ws-image-provider"><option value="">请选择已配置分组</option>${providers.map(p=>`<option value="${p.id}" ${provider?.id===p.id?'selected':''}>${esc(p.name)}</option>`).join('')}</select></label><label class="ws-label">图像模型<select id="ws-image-model">${(provider?.models||[]).map(m=>`<option ${m===(state.model||selected?.model)?'selected':''}>${esc(m)}</option>`).join('')}</select></label>${providers.length?'':button('添加API分组','image-models','plus')}`}
      <label class="ws-label">画面描述<textarea id="ws-image-prompt" rows="7" placeholder="描述人物、场景、构图与光线…">${esc(state.imagePrompt)}</textarea></label>
      <div class="ws-inline-fields"><label class="ws-label">画幅<select id="ws-image-ratio"><option value="16:9" ${state.imageRatio==='16:9'?'selected':''}>16:9 横屏</option><option value="9:16" ${state.imageRatio==='9:16'?'selected':''}>9:16 竖屏</option><option value="1:1" ${state.imageRatio==='1:1'?'selected':''}>1:1 方形</option></select></label><label class="ws-label">基础尺寸<select id="ws-image-quality"><option value="0.4" ${state.imageQuality==='0.4'?'selected':''}>0.4 MP</option><option value="1" ${state.imageQuality==='1'?'selected':''}>1 MP</option><option value="2" ${state.imageQuality==='2'?'selected':''}>2 MP</option></select></label></div>
      ${state.imageMode==='local'?`<label class="ws-reference">${icon('image')}<span>${esc(state.imageRef?.name||'添加参考图（按工作流需要）')}</span><input type="file" id="ws-image-reference" accept="image/*" hidden></label>`:''}
      <button class="ws-button ws-primary ws-generate" data-ws-action="generate-image" ${state.busy==='image'?'disabled':''}>${icon('sparkle')}${state.busy==='image'?'正在生成…':'生成图像'}</button><p class="ws-helper">${state.imageMode==='local'?'生成会占用当前5090；二采或放大可能改变最终尺寸。':'外部API费用按供应商规则结算。'}</p></aside>
      <article class="ws-image-preview">${state.imageURL?`<img src="${esc(state.imageURL)}" alt="生成结果"><a class="ws-button" href="${esc(state.imageURL)}" target="_blank" rel="noopener">${icon('download')}打开原图</a>`:empty('image','把想象，变成第一张参考图','角色设定、分镜静帧、服装与场景，都可以从这里开始。')}<div class="ws-generation-state" role="status">${esc(state.imageStatus||'等待生成')}</div></article></div></section>`;
  }
  function exportView(){
    return heading('EDITING HANDOFF','让生成的镜头，走进剪辑时间线。','按选取顺序生成可编辑的剪映草稿包，保留视频素材和原音轨。',button('刷新成片','refresh-videos','refresh'))+
      `<section class="ws-split ws-export-layout"><article class="ws-panel ws-video-library"><div class="ws-panel-title"><h2>已有成片 <span>${state.videos.length}</span></h2><span class="ws-soft">已选 ${state.selectedVideos.length} / 12</span></div>
      ${state.videos.length?`<div class="ws-video-grid">${state.videos.map(v=>{const index=state.selectedVideos.indexOf(v.url);return `<button class="ws-video-card ${index>=0?'selected':''}" data-ws-action="select-video" data-url="${esc(v.url)}"><span class="ws-video-thumb">${icon('film')}<b>${index>=0?index+1:icon('plus')}</b></span><strong>${esc(v.filename)}</strong><small>${esc(v.title||'生成视频')}</small></button>`;}).join('')}</div>`:empty('film','这里会出现你已完成的镜头','先生成一个视频，再刷新成片列表。也可以粘贴本平台的视频产出路径。')}
      <div class="ws-manual-media"><input id="ws-video-url" value="${esc(state.videoURL)}" placeholder="本平台路径，例如 /output/…/镜头.mp4" aria-label="视频产出路径">${button('添加镜头','add-video','plus')}</div></article>
      <aside class="ws-panel ws-export-settings"><span class="ws-eyebrow">JIAN YING DRAFT</span><h2>导出到剪映</h2><label class="ws-label">草稿名称<input id="ws-draft-title" maxlength="80" value="${esc(state.draftTitle)}"></label>
      <label class="ws-label">本机剪映草稿目录<input id="ws-draft-root" value="${esc(state.draftRoot)}" placeholder="C:\\…\\剪映草稿目录"></label><p class="ws-helper">在剪映「设置 → 草稿位置」核对实际目录。素材路径会按此目录写入草稿。</p>
      <label class="ws-label">时间线画幅<select id="ws-draft-ratio"><option value="portrait" ${state.draftRatio==='portrait'?'selected':''}>9:16 · 1080×1920</option><option value="landscape" ${state.draftRatio==='landscape'?'selected':''}>16:9 · 1920×1080</option></select></label>
      <ol class="ws-export-steps"><li>选择镜头，按编号顺序排列</li><li>生成并下载草稿ZIP</li><li>解压，将项目文件夹复制到草稿目录</li><li>在剪映中刷新草稿列表并打开</li></ol>
      <button class="ws-button ws-primary ws-generate" data-ws-action="export-draft" ${state.busy==='export'||!state.selectedVideos.length?'disabled':''}>${icon('download')}${state.busy==='export'?'正在准备素材与草稿…':'生成剪映草稿包'}</button>
      ${state.draft?`<a class="ws-button ws-ready-download" href="${state.draft.download_url}" download>${icon('check')}下载草稿包 · ${state.draft.clips}个镜头</a><p class="ws-helper">项目文件夹：${esc(state.draft.project_folder)}</p>`:''}
      <p class="ws-export-note">云端网页无法直接写入你的电脑。此处导出可编辑草稿包；导入后的兼容性需以你的剪映专业版为准。</p></aside></section>`;
  }
  function render(view){
    state.view=view;
    return `<div class="ws-workspace">${view==='novels'?novelView():view==='scripts'?scriptView():view==='images'?imageView():exportView()}</div>`;
  }
  async function uploadNovel(file){
    if(!file)return;
    state.busy='upload';refresh();
    try {const form=new FormData();form.append('file',file);state.novel=await request('/novels/import',{method:'POST',body:form});await load();toast('原著已保存，可单独进入剧本创作');}
    finally {state.busy='';refresh();}
  }
  async function saveScript(){
    if(!state.script)return;
    state.busy='save';refresh();
    try {state.script=await request('/scripts/'+state.script.id,json('PUT',{title:state.script.title,text:state.script.text,novel_id:state.script.novel_id}));await load();toast('剧本已保存');}
    finally {state.busy='';refresh();}
  }
  async function createScript(novel=null){
    const text=novel?`《${novel.title}》\n\n【改编目标】\n请在这里填写人物关系、集数与戏剧冲突。\n\n【第一场】\n内/外景：\n时间：\n人物：\n动作：\n对白：\n镜头建议：\n\n【原文摘录 · 前6000字，待人工改编】\n${novel.text.slice(0,6000)}`:'';
    state.script=await request('/scripts',json('POST',{title:novel?novel.title+' · 改编草稿':'未命名剧本',text,novel_id:novel?.id||null}));
    await load();go('scripts');
  }
  function downloadText(filename,text,type='text/plain;charset=utf-8'){
    const url=URL.createObjectURL(new Blob([text],{type}));const a=document.createElement('a');a.href=url;a.download=filename;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  }
  function modelDialog(kind){
    let group=state.defaults[kind]?.provider_id||(kind==='image'?'comfyui':state.providers.find(p=>p.kind===kind)?.id);
    let choice=state.defaults[kind]?.model||'';
    const dialog=modal(kind==='image'?'选择默认图片模型':'选择文本模型',`<div class="ws-model-dialog"></div>`);
    dialog.classList.add('ws-model-modal');dialog.querySelector('form').addEventListener('submit',event=>event.preventDefault());
    const container=dialog.querySelector('.ws-model-dialog');
    function paint(){
      const providers=state.providers.filter(p=>p.kind===kind);
      const provider=providers.find(p=>p.id===group);
      const models=group==='comfyui'?state.workflows.map(w=>({id:w.id,label:w.name||w.id})):provider?.models.map(m=>({id:m,label:m}))||[];
      container.innerHTML=`<p class="ws-helper">选择本机工作流，或配置外部API分组。模型列表由对应服务提供。</p><div class="ws-model-layout"><nav class="ws-model-groups">${kind==='image'?`<button type="button" data-group="comfyui" class="${group==='comfyui'?'selected':''}">${icon('layers')}本机ComfyUI <small>${state.workflows.length}个工作流</small></button>`:''}${providers.map(p=>`<button type="button" data-group="${p.id}" class="${group===p.id?'selected':''}">${icon('cloud')}${esc(p.name)}<small>${p.models.length}个模型 · ${p.configured?'已存密钥':'未存密钥'}</small></button>`).join('')}<button type="button" data-add-provider>${icon('plus')}添加API分组</button></nav><div class="ws-model-options"><div class="ws-model-search"><input placeholder="搜索模型名称…" aria-label="搜索模型">${provider?'<button type="button" data-refresh-models>拉取模型</button>':''}</div><div class="ws-model-list">${models.map(m=>`<button type="button" data-model="${esc(m.id)}" class="${m.id===choice?'selected':''}"><span>${icon(group==='comfyui'?'layers':'cloud')}</span><strong>${esc(m.label)}</strong><small>${group==='comfyui'?'本机工作流 · 占用5090':'外部API · 以供应商计费为准'}</small>${m.id===choice?icon('check'):''}</button>`).join('')||'<div class="ws-list-empty">这个分组没有模型。请添加模型ID或点击拉取模型。</div>'}</div>${provider?'<button type="button" class="ws-remove-provider" data-remove-provider>删除这个API分组</button>':''}</div></div><button type="button" class="ws-button ws-primary ws-model-confirm" data-confirm-model ${!choice?'disabled':''}>设为默认分组和模型</button>`;
      container.querySelectorAll('[data-group]').forEach(button=>button.onclick=()=>{group=button.dataset.group;choice='';paint();});
      container.querySelectorAll('[data-model]').forEach(button=>button.onclick=()=>{choice=button.dataset.model;paint();});
      container.querySelector('.ws-model-search input').oninput=event=>container.querySelectorAll('[data-model]').forEach(button=>button.hidden=!button.textContent.toLowerCase().includes(event.target.value.toLowerCase()));
      container.querySelector('[data-add-provider]').onclick=()=>{dialog.close();providerDialog(kind);};
      const fetchModels=container.querySelector('[data-refresh-models]');
      if(fetchModels)fetchModels.onclick=async()=>{fetchModels.disabled=true;try{await request('/providers/'+group+'/models',{method:'POST'});await load();choice='';paint();}catch(error){toast(error.message);fetchModels.disabled=false;}};
      const remove=container.querySelector('[data-remove-provider]');
      if(remove)remove.onclick=async()=>{if(!confirm('删除此API分组和保存的密钥？'))return;await request('/providers/'+group,{method:'DELETE'});await load();group=kind==='image'?'comfyui':null;choice='';paint();};
      container.querySelector('[data-confirm-model]').onclick=async()=>{try{await request('/defaults',json('PUT',{kind,provider_id:group,model:choice}));if(kind==='image'){state.providerId=group;state.model=choice;state.imageMode=group==='comfyui'?'local':'api';if(group==='comfyui')state.workflow=state.workflows.find(w=>w.id===choice);}await load();dialog.close();toast('默认模型已保存');}catch(error){toast(error.message);}};
    }
    paint();
  }
  function providerDialog(kind){
    const dialog=modal('添加'+(kind==='image'?'图像':'文本')+'API分组',`<p class="ws-dialog-intro">接口需兼容 ${kind==='image'?'images/generations':'chat/completions'}。填写供应商实际提供的地址和模型ID。</p><label class="ws-label">分组名称<input name="name" required maxlength="60" placeholder="例如：我的图像API"></label><label class="ws-label">API基础地址<input name="base_url" type="url" required placeholder="https://供应商域名/v1"></label><label class="ws-label">API Key<input name="api_key" type="password" autocomplete="new-password" placeholder="仅保存在服务端，不在列表中返回"></label><label class="ws-label">模型ID（每行一个）<textarea name="models" rows="3" placeholder="填写你有权限使用的模型ID，或保存后拉取列表"></textarea></label><footer><button type="submit" class="ws-button ws-primary">保存API分组</button></footer>`,async form=>{
      await request('/providers',json('POST',{name:form.elements.name.value,kind,base_url:form.elements.base_url.value.trim(),api_key:form.elements.api_key.value.trim(),models:form.elements.models.value.split(/[\n,]/).map(x=>x.trim()).filter(Boolean)}));await load();setTimeout(()=>modelDialog(kind),50);
    });
    dialog.classList.add('ws-provider-dialog');
  }
  async function localGenerate(){
    if(!state.workflow)throw new Error('请先选择本机图像工作流');
    const response=await fetch('/api/workflow/config/'+encodeURIComponent(state.workflow.id));const config=await response.json();
    const cfg=config.api_config||config.apiConfig;
    if(!cfg)throw new Error('工作流参数未公开，请在高级工具中查看');
    const values={};let promptSet=false;
    for(const [key,on] of Object.entries(cfg.enabledParams||{})){
      if(!on)continue;
      const alias=cfg.apiNames?.[key]||key;
      if(/^ref_image_/.test(alias)){values[alias]=alias==='ref_image_0'?state.imageRef?.name||null:null;continue;}
      if(/seed/i.test(alias)){values[alias]=Math.floor(Math.random()*1000000000);continue;}
      if(!promptSet && /prompt|text|提示词/i.test(alias) && !/negative|负/i.test(alias)){values[alias]=state.imagePrompt;promptSet=true;}
      else if(alias==='megapixels')values[alias]=Number(state.imageQuality);
      else if(alias==='aspect_ratio')values[alias]=({'16:9':'16:9 (Widescreen)','9:16':'9:16 (Portrait Widescreen)','1:1':'1:1 (Square)'})[state.imageRatio];
    }
    if(!promptSet)throw new Error('该工作流没有公开文本输入，请选择其他工作流或使用原生参数页');
    const submitted=await fetch('/api/workflow/generate',json('POST',{workflow_id:state.workflow.id,input_values:values,source:'api',client_id:'lichtv-studio-'+Date.now()}));
    const task=await submitted.json();if(!submitted.ok||!task.prompt_id)throw new Error(task.detail||task.error||'任务提交失败');
    state.imageStatus='任务已提交 · '+task.prompt_id;refresh();
    const began=Date.now();
    while(Date.now()-began<30*60*1000){
      await new Promise(resolve=>setTimeout(resolve,2500));
      const result=await(await fetch('/api/workflow/result?prompt_id='+encodeURIComponent(task.prompt_id),{cache:'no-store'})).json();
      if(result.pending!==false)continue;
      if(result.error)throw new Error(typeof result.error==='string'?result.error:'工作流执行失败，请查看任务列表');
      const urls=[];
      function walk(value){if(!value||typeof value!=='object')return;if(value.url && (value.type==='image'||/\.(png|jpe?g|webp)/i.test(value.url)||/\.(png|jpe?g|webp)$/i.test(value.filename||'')))urls.push(value.url);Object.values(value).forEach(walk);}
      walk(result.results||result);
      if(!urls.length)throw new Error('任务已结束，但没有返回可预览的图片，请到我的资产查看');
      return urls[0];
    }
    throw new Error('已等待30分钟，任务可能仍在后台，请到任务列表查看');
  }
  async function generateImage(){
    if(!state.imagePrompt.trim())throw new Error('请先填写画面描述');
    state.busy='image';state.imageStatus='正在准备生成任务…';refresh();
    try{
      if(state.imageMode==='local')state.imageURL=await localGenerate();
      else{
        const providerId=document.querySelector('#ws-image-provider')?.value||state.defaults.image?.provider_id;
        const model=document.querySelector('#ws-image-model')?.value||state.defaults.image?.model;
        if(!providerId||!model)throw new Error('请先配置API分组并选择图像模型');
        const ratio=state.imageRatio;
        const size=ratio==='16:9'?'1536x1024':ratio==='9:16'?'1024x1536':'1024x1024';
        state.imageURL=(await request('/image',json('POST',{provider_id:providerId,model,prompt:state.imagePrompt,size}))).url;
      }
      sessionStorage.setItem('lichtv-last-image',state.imageURL);state.imageStatus='图像已生成';
    }catch(error){state.imageStatus=error.message;throw error;}
    finally{state.busy='';refresh();}
  }
  async function refreshVideos(){const found=(await request('/videos')).items;const seen=new Set();state.videos=[...state.manualVideos,...found].filter(item=>{if(seen.has(item.url))return false;seen.add(item.url);return true;});refresh();}
  async function action(name,element){
    switch(name){
      case 'upload-novel':document.querySelector('#ws-novel-file').click();break;
      case 'open-novel':state.novel=await request('/novels/'+element.dataset.id);refresh();break;
      case 'delete-novel':if(confirm('移除此原著？已保存的剧本会保留。')){await request('/novels/'+state.novel.id,{method:'DELETE'});state.novel=null;await load();}break;
      case 'novel-to-script':go('scripts');break;
      case 'new-script':await createScript();break;
      case 'seed-script':{const id=document.querySelector('#ws-source-novel').value;if(!id)throw new Error('请先选择一份原著');state.novel=await request('/novels/'+id);await createScript(state.novel);break;}
      case 'open-script':state.script={...state.scripts.find(s=>s.id===element.dataset.id)};refresh();break;
      case 'save-script':await saveScript();break;
      case 'delete-script':if(confirm('删除当前剧本？')){await request('/scripts/'+state.script.id,{method:'DELETE'});state.script=null;await load();}break;
      case 'download-script':downloadText(state.script.title+'.txt',state.script.text);break;
      case 'download-scenes':{const rows=sceneRows(state.script.text);const cell=s=>'"'+String(s).replaceAll('"','""')+'"';downloadText(state.script.title+'-分镜.csv','\uFEFF序号,镜头描述,建议秒数\n'+rows.map(row=>[row.index,cell(row.text),5].join(',')).join('\n'),'text/csv;charset=utf-8');break;}
      case 'open-batch':await navigate('zealman-h3canvas');break;
      case 'text-models':modelDialog('text');break;
      case 'image-models':modelDialog('image');break;
      case 'image-local':state.imageMode='local';refresh();break;
      case 'image-api':state.imageMode='api';refresh();break;
      case 'generate-image':await generateImage();break;
      case 'adapt-script':{const novelId=document.querySelector('#ws-source-novel').value;const selected=state.defaults.text;if(!novelId)throw new Error('请先选择原著');if(!selected){modelDialog('text');return;}state.busy='adapt';refresh();try{state.script=await request('/adapt',json('POST',{novel_id:novelId,provider_id:selected.provider_id,model:selected.model,instructions:'改编为节奏清晰的短剧剧本，保留核心人物与主要矛盾。'}));await load();}finally{state.busy='';refresh();}break;}
      case 'refresh-videos':await refreshVideos();break;
      case 'select-video':{const url=element.dataset.url;const index=state.selectedVideos.indexOf(url);if(index>=0)state.selectedVideos.splice(index,1);else if(state.selectedVideos.length<12)state.selectedVideos.push(url);else throw new Error('单次最多导出12个镜头');state.draft=null;refresh();break;}
      case 'add-video':{const url=state.videoURL.trim();if(!url.startsWith('/output/')&&!url.startsWith('/api/comfy/view?'))throw new Error('请粘贴当前面板的 /output/ 路径或产出预览地址');if(!state.videos.some(v=>v.url===url)){const clip={url,filename:decodeURIComponent(url.split('?')[0].split('/').pop()),title:'手动加入的成片'};state.manualVideos.unshift(clip);state.videos.unshift(clip);}state.videoURL='';if(state.selectedVideos.length<12&&!state.selectedVideos.includes(url))state.selectedVideos.push(url);refresh();break;}
      case 'export-draft':{const draftRoot=state.draftRoot.trim();const title=state.draftTitle.trim();const landscape=state.draftRatio==='landscape';localStorage.setItem('lichtv-draft-root',draftRoot);state.busy='export';refresh();try{state.draft=await request('/drafts',json('POST',{title,urls:state.selectedVideos,draft_root:draftRoot,width:landscape?1920:1080,height:landscape?1080:1920}));toast('草稿包已准备好，点击下载后按说明复制到剪映目录');}finally{state.busy='';refresh();}break;}
    }
  }
  document.addEventListener('click',event=>{
    const target=event.target.closest('[data-ws-action]');
    if(target){event.preventDefault();action(target.dataset.wsAction,target).catch(error=>toast(error.message));}
    if(event.target.closest('[data-ws-drop="novel"]'))document.querySelector('#ws-novel-file')?.click();
  });
  document.addEventListener('input',event=>{
    if(event.target.id==='ws-script-title'&&state.script)state.script.title=event.target.value;
    if(event.target.id==='ws-script-text'&&state.script){state.script.text=event.target.value;const counter=document.querySelector('#ws-script-count');if(counter)counter.textContent=count(event.target.value.length)+' 字';}
    if(event.target.id==='ws-image-prompt')state.imagePrompt=event.target.value;
    if(event.target.id==='ws-draft-root')state.draftRoot=event.target.value;
    if(event.target.id==='ws-draft-title')state.draftTitle=event.target.value;
    if(event.target.id==='ws-video-url')state.videoURL=event.target.value;
  });
  document.addEventListener('change',async event=>{
    try{
      if(event.target.id==='ws-novel-file')await uploadNovel(event.target.files[0]);
      if(event.target.id==='ws-image-workflow')state.workflow=state.workflows.find(w=>w.id===event.target.value);
      if(event.target.id==='ws-image-provider'){state.providerId=event.target.value;state.model=null;refresh();}
      if(event.target.id==='ws-image-model')state.model=event.target.value;
      if(event.target.id==='ws-image-ratio')state.imageRatio=event.target.value;
      if(event.target.id==='ws-image-quality')state.imageQuality=event.target.value;
      if(event.target.id==='ws-draft-ratio')state.draftRatio=event.target.value;
      if(event.target.id==='ws-image-reference'){
        const file=event.target.files[0];if(!file)return;
        const form=new FormData();form.append('file',file);form.append('overwrite','false');
        const response=await fetch('/studio-api/accounts/upload',{method:'POST',body:form});const data=await response.json();
        if(!response.ok)throw new Error('参考图上传失败');state.imageRef=data;refresh();
      }
    }catch(error){toast(error.message);}
  });
  document.addEventListener('dragover',event=>{if(event.target.closest('[data-ws-drop]'))event.preventDefault();});
  document.addEventListener('drop',event=>{if(event.target.closest('[data-ws-drop="novel"]')){event.preventDefault();uploadNovel(event.dataTransfer.files[0]).catch(error=>toast(error.message));}});
  document.addEventListener('keydown',event=>{if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==='s'&&state.view==='scripts'){event.preventDefault();saveScript().catch(error=>toast(error.message));}});
  return {render,load,enter(view){state.view=view;if(view==='export')refreshVideos().catch(error=>toast(error.message));},modelDialog};
}
