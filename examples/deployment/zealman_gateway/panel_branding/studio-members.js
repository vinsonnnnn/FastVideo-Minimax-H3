import {createCheckout} from '/studio-checkout.js';
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt = value => Number(value || 0).toLocaleString('zh-CN');
const money = cents => '¥' + (cents / 100).toFixed(2);
const stamp = value => new Date(value * 1000).toLocaleString('zh-CN');
const labels = {queued:'排队中',submitting:'正在提交',running:'生成中',done:'已完成',failed:'失败 · 已退款',cancelled:'已取消 · 已退款',review:'待管理员核对'};

export function createMembership({toast, modal, refresh, openView}) {
  const state = {user:null, csrf:'', config:null, wallet:null, jobs:[], workflows:[], admin:null, view:'wallet', image:null, draft:{prompt:'',seconds:5,mode:'single',workflow:''}, busy:false, lastOrder:null};
  const baseFetch = window.fetch.bind(window);
  window.fetch = (input, init = {}) => {
    const url = new URL(input instanceof Request ? input.url : input, location.href);
    const method = (init.method || (input instanceof Request ? input.method : 'GET')).toUpperCase();
    if (url.origin === location.origin && !['GET','HEAD','OPTIONS'].includes(method)) {
      const headers = new Headers(init.headers || (input instanceof Request ? input.headers : undefined));
      if(state.csrf) headers.set('X-LichTV-CSRF', state.csrf);
      init = {...init, headers};
    }
    return baseFetch(input, init);
  };
  const originalOpen = XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open = function(method,url,...args) {this.__lichtvSameOrigin=new URL(url,location.href).origin===location.origin;return originalOpen.call(this,method,url,...args);};
  const originalSend = XMLHttpRequest.prototype.send;
  XMLHttpRequest.prototype.send = function(...args) {
    if(state.csrf && this.__lichtvSameOrigin) this.setRequestHeader('X-LichTV-CSRF', state.csrf);
    return originalSend.apply(this,args);
  };
  async function api(path, body) {
    const response = await fetch('/studio-api/accounts' + path, body === undefined ? {} : {method:'POST', headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    const data = await response.json();
    if(!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : '请求内容不正确，请检查后重试');
    return data;
  }
  function renderAccount() {
    document.querySelectorAll('[data-action="account"]').forEach(el => {
      el.textContent = state.user ? `${fmt(state.user.credits)} 积分 · ${state.user.username}` : '登录 / 注册';
      el.classList.add('mb-account');el.setAttribute('aria-label','账号与积分');
    });
    document.body.classList.toggle('member-admin', state.user?.role === 'admin');
    document.querySelectorAll('[data-members-admin]').forEach(el => el.hidden=state.user?.role!=='admin');
  }
  async function bootstrap() {
    state.config = await api('/public');
    try {const data=await api('/me');state.user=data.user;state.csrf=data.csrf;} catch {state.user=null;state.csrf='';}
    renderAccount();return state.user;
  }
  function auth(register=false) {
    const dialog=modal(register?'创建 LichTV 账号':'欢迎回到 LichTV',`<p class="st-dialog-note">${register?`前100名注册用户，每人赠送100万积分。当前剩余 ${state.config?.bonus_places_remaining ?? '…'} 个名额，注册成功时以服务器记录为准。`:'登录后管理你的作品、任务与积分。'}</p><label class="st-field">账号<input name="username" autocomplete="username" minlength="3" maxlength="32" required placeholder="3–32位字母、数字或中文"></label><label class="st-field">密码<input name="password" type="password" autocomplete="${register?'new-password':'current-password'}" minlength="10" maxlength="128" required placeholder="至少10位"></label><p class="st-dialog-note">视频生成按提交时长计费：每秒2积分；执行失败自动退回。</p><footer><button type="button" class="st-button" data-switch>${register?'已有账号，去登录':'创建账号'}</button><button type="submit" class="st-button st-button-white">${register?'注册并领取奖励':'登录'}</button></footer>`, async form => {
      const data=await api(register?'/register':'/login',{username:form.elements.username.value,password:form.elements.password.value});
      state.user=data.user;state.csrf=data.csrf;location.reload();
    });
    dialog.querySelector('[data-switch]').onclick=()=>{dialog.close();auth(!register);};
  }
  function requireLogin() {if(state.user)return true;auth();return false;}
  async function enter(view) {
    state.view=view;
    if(!requireLogin())return;
    if(view==='wallet'){state.wallet=await api('/wallet');state.user=state.wallet.user;}
    else if(view==='members-admin'){if(state.user.role!=='admin')throw Error('需要管理员权限');state.admin=await api('/admin');}
    else {const [jobs,workflows]=await Promise.all([api('/jobs'),api('/workflows')]);state.jobs=jobs.items;state.queue=jobs.queue_size;state.workflows=workflows.items;}
    renderAccount();refresh();
  }
  const checkout=createCheckout({toast,modal,onUpdate:async order=>{state.lastOrder=order;await enter('wallet');}});
  function wallet() {
    const data=state.wallet;
    if(!data)return '<p class="mb-empty">正在读取积分账户…</p>';
    return `<div class="mb-heading"><div><span class="ws-eyebrow">YOUR ACCOUNT</span><h1>我的积分</h1><p>${esc(state.user.username)} · ${state.user.signup_seq?`第 ${state.user.signup_seq} 位注册用户`:'管理员账号'}</p></div><div><button class="ws-button" data-mb="password">修改密码</button> <button class="ws-button" data-mb="logout">退出登录</button></div></div><section class="mb-balance"><div><span>可用积分</span><strong>${fmt(state.user.credits)}</strong><p>每秒2积分 · 5秒视频消耗10积分 · 1分钟消耗120积分</p></div><span class="mb-balance-mark">L</span></section><h2>积分套餐</h2><div class="mb-packages">${data.packages.map(p=>`<button data-mb-package="${p.id}"><span>${fmt(p.credits)} <small>积分</small></span><strong>${money(p.price_cents)}</strong><em>创建充值订单 →</em></button>`).join('')}</div><p class="mb-note">支付宝、微信扫码订单在支付确认后自动到账。待配置渠道暂不可付款；人工订单仍由管理员核实收款。</p>${state.lastOrder?`<div class="mb-order-notice">${esc(state.lastOrder.message)}<br>订单号：<code>${esc(state.lastOrder.id)}</code> · ${money(state.lastOrder.price_cents)} / ${fmt(state.lastOrder.credits)}积分</div>`:''}<h2>充值订单</h2><div class="mb-table-wrap"><table><thead><tr><th>订单号 / 时间</th><th>积分</th><th>金额</th><th>方式 / 状态</th><th>操作</th></tr></thead><tbody>${data.orders.map(o=>`<tr><td><code>${esc(o.id)}</code><small>${stamp(o.created_at)}</small></td><td>${fmt(o.credits)}</td><td>${money(o.price_cents)}</td><td>${({alipay:'支付宝',wechatpay:'微信支付',manual:'人工核实'})[o.channel||'manual']} · ${o.status==='paid'?'已到账':o.status==='closed'?'已关闭':o.channel==='manual'?'待核实收款':'待付款'}</td><td><button class="ws-button" data-payment-order="${o.id}">${o.status==='paid'?'查看订单':'付款 / 查单'}</button></td></tr>`).join('')||'<tr><td colspan="5">暂无订单</td></tr>'}</tbody></table></div><h2>积分明细</h2><div class="mb-table-wrap"><table><thead><tr><th>时间</th><th>说明</th><th>变动</th><th>余额</th></tr></thead><tbody>${data.ledger.map(l=>`<tr><td>${stamp(l.created_at)}</td><td>${esc(l.reason)}</td><td class="${l.delta>0?'mb-positive':''}">${l.delta>0?'+':''}${fmt(l.delta)}</td><td>${fmt(l.balance)}</td></tr>`).join('')||'<tr><td colspan="4">暂无积分明细</td></tr>'}</tbody></table></div>`;
  }
  function resultLinks(result) {
    const links=new Set();
    function walk(value) {if(typeof value==='string'&&value.startsWith('/studio-api/accounts/media/'))links.add(value);else if(Array.isArray(value))value.forEach(walk);else if(value&&typeof value==='object')Object.values(value).forEach(walk);}
    walk(result);
    return [...links].map((url,i)=>`<a class="ws-button" href="${esc(url)}" target="_blank" rel="noopener">查看产出 ${i+1} ↗</a>`).join('');
  }
  function jobs() {
    const video=state.workflows.filter(w=>w.credits_per_second===2).sort((a,b)=>Number(a.reference_required)-Number(b.reference_required));
    return `<div class="mb-heading"><div><span class="ws-eyebrow">CREATE WITH CREDITS</span><h1>${state.view==='video-create'?'视频生成':'批量生成与任务'}</h1><p>每秒2积分 · 提交预扣 · 失败退回 · 单卡按顺序执行</p></div><button class="ws-button" data-mb="reload">刷新任务</button></div><div class="mb-create-grid"><form id="mb-generation"><label class="st-field">工作流<select name="workflow">${video.map(w=>`<option value="${esc(w.id)}" ${state.draft.workflow===w.id?'selected':''}>${esc(w.id.replace(/^API-/,''))}${w.reference_required?'（需参考图）':''}</option>`).join('')}</select></label><label class="st-field">镜头描述<textarea name="prompt" rows="5" required maxlength="20000" placeholder="描述人物、场景、动作与声音；批量时每行一个镜头。">${esc(state.draft.prompt)}</textarea></label><div class="mb-input-row"><label class="st-field">每段时长（秒）<input name="seconds" type="number" min="1" max="15" value="${state.draft.seconds}" required></label><label class="st-field">提交模式<select name="mode"><option value="single" ${state.draft.mode==='single'?'selected':''}>单镜头</option><option value="batch" ${state.draft.mode==='batch'?'selected':''}>批量：每行一个镜头</option></select></label></div><label class="st-field">参考图（按工作流需要）<input type="file" name="reference" accept="image/png,image/jpeg,image/webp"></label><small>${state.image?'参考图已上传；更换账号后需重新上传':'文生视频可不上传；图生视频需上传参考图。当前支持一张参考图。'}</small><div class="mb-estimate">预计 <strong id="mb-cost">10</strong> 积分 <span>余额 ${fmt(state.user?.credits)}</span></div><button class="ws-button ws-primary" type="submit" ${state.busy||!video.length?'disabled':''}>提交生成任务 →</button><p class="mb-note">每段1–15秒，当前采用480p级工作流预设。批量最多20段，逐条入队；余额不足时保留已经提交的任务。</p></form><aside class="mb-queue-info"><span>GPU QUEUE</span><strong>${fmt(state.queue)}</strong><p>全站待处理任务</p><hr><p>每个人拥有独立的任务和产出。排队期间可以取消，积分原路退回；已开始的任务将继续执行。</p><button class="ws-button" data-mb="wallet">查看我的积分</button></aside></div><h2>我的生成记录</h2><div class="mb-jobs">${state.jobs.map(j=>`<article><header><strong>${esc(j.workflow.replace(/^API-/,''))}</strong><span class="mb-status">${labels[j.status]||esc(j.status)}</span></header><p>${stamp(j.created_at)} · ${j.seconds?j.seconds+'秒 · ':''}${j.cost}积分</p>${j.error?`<p class="mb-error">${esc(j.error)}</p>`:''}<div>${resultLinks(j.result)}${j.status==='queued'?`<button class="ws-button" data-mb-cancel="${j.id}">取消并退回积分</button>`:''}</div></article>`).join('')||'<p class="mb-empty">你的第一段故事，从这里开始。</p>'}</div>`;
  }
  function admin() {
    const data=state.admin;if(!data)return '<p class="mb-empty">正在加载用户管理…</p>';
    return `<div class="mb-heading"><div><span class="ws-eyebrow">ADMINISTRATION</span><h1>用户管理</h1><p>账号、积分调整与人工收款核验，操作均保留积分流水。</p></div><div><button class="ws-button" data-payment-setup>支付配置状态</button> <button class="ws-button" data-mb="reload">刷新</button></div></div><h2>注册用户 <small>${data.users.filter(u=>u.signup_seq).length} / 奖励名额100</small></h2><div class="mb-table-wrap"><table><thead><tr><th>账号 / 注册序号</th><th>积分余额</th><th>状态</th><th>管理</th></tr></thead><tbody>${data.users.map(u=>`<tr><td>${esc(u.username)}<small>${u.signup_seq?'第'+u.signup_seq+'位':'管理员'}</small></td><td>${fmt(u.credits)}</td><td>${u.status==='active'?'正常':'已停用'}</td><td><button class="ws-button" data-mb-adjust="${u.id}">调整积分</button> ${u.role!=='admin'?`<button class="ws-button" data-mb-user="${u.id}" data-status="${u.status==='active'?'disabled':'active'}">${u.status==='active'?'停用':'启用'}</button>`:''}</td></tr>`).join('')}</tbody></table></div><h2>充值核验</h2><div class="mb-table-wrap"><table><thead><tr><th>账号 / 订单</th><th>套餐</th><th>金额</th><th>操作</th></tr></thead><tbody>${data.orders.map(o=>`<tr><td>${esc(o.username)}<small><code>${o.id}</code></small></td><td>${fmt(o.credits)}积分</td><td>${money(o.price_cents)}</td><td>${o.status==='paid'?'已入账':o.channel&&o.channel!=='manual'?`<span>${o.channel==='alipay'?'支付宝':'微信支付'}</span> <button class="ws-button" data-payment-admin-refresh="${o.id}">向平台查单</button>`:`<button class="ws-button ws-primary" data-mb-confirm="${o.id}">核实收款并入账</button>`}</td></tr>`).join('')||'<tr><td colspan="4">暂无充值订单</td></tr>'}</tbody></table></div>${data.review_jobs.length?`<h2>需核对的GPU任务</h2><p class="mb-note">提交响应中断的任务不会自动重试或退款。先核对GPU队列和历史，避免重复生成。</p>${data.review_jobs.map(j=>`<article class="mb-review"><code>${j.id}</code><p>${esc(j.error)}</p><button class="ws-button" data-mb-resolve="${j.id}">登记GPU任务号 / 核实退款</button></article>`).join('')}`:''}<h2>最近积分流水</h2><div class="mb-table-wrap"><table><thead><tr><th>账号</th><th>说明</th><th>变动</th><th>时间</th></tr></thead><tbody>${data.ledger.map(l=>`<tr><td>${esc(l.username)}</td><td>${esc(l.reason)}</td><td>${l.delta>0?'+':''}${fmt(l.delta)}</td><td>${stamp(l.created_at)}</td></tr>`).join('')}</tbody></table></div>`;
  }
  function render(view) {state.view=view;return `<div class="mb-workspace">${view==='wallet'?wallet():view==='members-admin'?admin():jobs()}</div>`;}
  function estimate(form) {
    const count=form.elements.mode.value==='batch'?form.elements.prompt.value.split('\n').filter(x=>x.trim()).length:1;
    const cost=(Number(form.elements.seconds.value)||0)*2*Math.max(1,count);
    document.querySelector('#mb-cost').textContent=fmt(cost);return cost;
  }
  document.addEventListener('input',e=>{const form=e.target.closest('#mb-generation');if(form){for(const key of ['prompt','seconds','mode','workflow'])state.draft[key]=form.elements[key].value;estimate(form);}});
  document.addEventListener('submit',async e=>{
    if(e.target.id!=='mb-generation')return;e.preventDefault();
    if(state.busy)return;
    const form=e.target, button=form.querySelector('[type="submit"]');
    try {
      const prompts=form.elements.mode.value==='batch'?form.elements.prompt.value.split('\n').map(x=>x.trim()).filter(Boolean):[form.elements.prompt.value.trim()];
      if(!prompts.length||prompts.length>20)throw Error('请填写1–20段镜头描述');
      if(estimate(form)>state.user.credits)throw Error('积分不足，请先充值');
      state.busy=true;button.disabled=true;button.textContent='正在提交…';
      const file=form.elements.reference.files[0];
      if(file){const body=new FormData();body.set('file',file);const response=await fetch('/studio-api/accounts/upload',{method:'POST',body});const data=await response.json();if(!response.ok)throw Error(data.detail||'上传失败');state.image=data.name;}
      const selected=state.workflows.find(w=>w.id===form.elements.workflow.value);if(selected?.reference_required&&!state.image)throw Error('此工作流需要参考图，请上传或选择U03文生视频');
      let submitted=0;state.retryKeys ||= new Map();
      for(const [index,prompt] of prompts.entries()){const payload={workflow_id:form.elements.workflow.value,prompt,seconds:Number(form.elements.seconds.value),image:state.image};const fingerprint=JSON.stringify([index,payload]);if(!state.retryKeys.has(fingerprint))state.retryKeys.set(fingerprint,crypto.randomUUID());await api('/jobs',{...payload,idempotency_key:state.retryKeys.get(fingerprint)});state.retryKeys.delete(fingerprint);submitted++;}
      toast(`已提交${submitted}个任务，按队列顺序生成`);await bootstrap();await enter(state.view);
    } catch(error){toast(error.message);}
    finally{state.busy=false;button.disabled=false;button.textContent='提交生成任务 →';}
  });
  document.addEventListener('click',async e=>{
    const target=e.target.closest('[data-mb],[data-mb-package],[data-mb-cancel],[data-mb-adjust],[data-mb-user],[data-mb-confirm],[data-mb-resolve]');
    if(!target)return;
    try {
      if(target.dataset.mb==='logout'){await api('/logout',{});localStorage.removeItem('lichtv-last-image');sessionStorage.removeItem('lichtv-last-image');location.reload();return;}
      if(target.dataset.mb==='password'){modal('修改密码','<label class="st-field">当前密码<input name="current" type="password" minlength="10" required autocomplete="current-password"></label><label class="st-field">新密码<input name="next" type="password" minlength="10" maxlength="128" required autocomplete="new-password"></label><footer><button type="submit" class="ws-button ws-primary">修改并重新登录</button></footer>',async form=>{await api('/password',{current_password:form.elements.current.value,new_password:form.elements.next.value});location.reload();});return;}
      if(target.dataset.mb==='wallet'){openView('wallet');return;}
      if(target.dataset.mb==='reload'){await enter(state.view);return;}
      if(target.dataset.mbPackage){const packageInfo=state.wallet.packages.find(p=>p.id===target.dataset.mbPackage);checkout.choose(packageInfo,state.wallet.payment_channels||state.config.payment_channels||[]);return;}
      if(target.dataset.mbCancel){await api('/jobs/'+target.dataset.mbCancel+'/cancel',{});await bootstrap();await enter(state.view);return;}
      if(target.dataset.mbUser){await api('/admin/users/'+target.dataset.mbUser+'/status',{status:target.dataset.status});await enter('members-admin');return;}
      if(target.dataset.mbAdjust){const id=target.dataset.mbAdjust,key=crypto.randomUUID();modal('调整用户积分','<label class="st-field">积分变动（正数增加，负数扣减）<input name="delta" type="number" required></label><label class="st-field">调整原因<input name="reason" minlength="4" maxlength="200" required></label><footer><button type="submit" class="ws-button ws-primary">记录调整</button></footer>',async form=>{await api('/admin/users/'+id+'/adjust',{delta:Number(form.elements.delta.value),reason:form.elements.reason.value,idempotency_key:key});await bootstrap();await enter('members-admin');});return;}
      if(target.dataset.mbConfirm){const id=target.dataset.mbConfirm;modal('核实收款并充值','<p class="st-dialog-note">仅在实际收款且金额与订单一致时确认。不可用同一笔收款为多个订单充值。</p><label class="st-field">实际收款流水号<input name="receipt" minlength="4" maxlength="120" required></label><label class="mb-checkbox"><input name="verified" type="checkbox" required> 已核实实际到账金额与订单一致</label><footer><button type="submit" class="ws-button ws-primary">确认入账</button></footer>',async form=>{await api('/admin/orders/'+id+'/confirm',{receipt:form.elements.receipt.value,verified_received:form.elements.verified.checked});await enter('members-admin');});return;}
      if(target.dataset.mbResolve){const id=target.dataset.mbResolve;modal('核对GPU任务','<label class="st-field">GPU prompt_id（已实际提交时填写）<input name="prompt"></label><label class="mb-checkbox"><input type="checkbox" name="notrunning"> 已核实GPU队列和历史，确认该任务没有执行，允许退款</label><footer><button type="submit" class="ws-button ws-primary">保存核对结果</button></footer>',async form=>{await api('/admin/jobs/'+id+'/resolve',{prompt_id:form.elements.prompt.value,confirmed_not_running:form.elements.notrunning.checked});await enter('members-admin');});}
    }catch(error){toast(error.message);}
  });
  setInterval(async()=>{if(!state.user||!['video-create','member-jobs'].includes(state.view)||state.busy||document.querySelector('dialog[open]')||document.activeElement?.closest('#mb-generation')||document.querySelector('#mb-generation input[type=file]')?.files.length)return;try{const data=await api('/jobs');const changed=JSON.stringify(state.jobs)!==JSON.stringify(data.items)||state.queue!==data.queue_size;state.jobs=data.items;state.queue=data.queue_size;if(changed&&document.querySelector('.mb-jobs')){await bootstrap();refresh();}}catch{}},6000);
  return {state,bootstrap,auth,requireLogin,enter,render,renderAccount};
}
