const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const money=value=>'¥'+(value/100).toFixed(2);
const channelName=value=>({alipay:'支付宝',wechatpay:'微信支付',manual:'人工核实收款'}[value]||value);

export function createCheckout({toast,modal,onUpdate}) {
  async function request(path,body) {
    const response=await fetch('/studio-api'+path,body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    const data=await response.json();
    if(!response.ok)throw Error(typeof data.detail==='string'?data.detail:'支付请求失败，请稍后重试');
    return data;
  }
  function choose(packageInfo,channels) {
    const enabled=channels.find(channel=>channel.enabled)?.id||'manual';
    const requestKey=crypto.randomUUID();
    const dialog=modal('选择支付方式',`<div class="co-package"><span>${Number(packageInfo.credits).toLocaleString('zh-CN')}积分</span><strong>${money(packageInfo.price_cents)}</strong></div><p class="st-dialog-note">请选择付款方式。扫码订单在支付平台确认后自动增加积分。</p><div class="co-channels">${channels.map(channel=>`<label class="co-channel ${channel.enabled?'':'co-disabled'}"><input type="radio" name="channel" value="${esc(channel.id)}" ${channel.enabled?'':'disabled'} ${enabled===channel.id?'checked':''}><span><strong>${esc(channel.name)}</strong><small>${channel.enabled?'扫码付款 · 确认后自动到账':esc(channel.message)}</small></span><em>${channel.enabled?'扫码支付':'待配置'}</em></label>`).join('')}<label class="co-channel"><input type="radio" name="channel" value="manual" ${enabled==='manual'?'checked':''}><span><strong>人工核实收款</strong><small>联系管理员安排付款 · 核实到账后入账</small></span></label></div>${channels.some(channel=>!channel.enabled)?'<p class="co-note">待配置渠道暂不可付款，需要平台管理员完成商户接入。</p>':''}<footer><button type="submit" class="ws-button ws-primary">创建订单</button></footer>`,async form=>{
      const order=await request('/accounts/orders',{package_id:packageInfo.id,channel:form.elements.channel.value,idempotency_key:requestKey});
      await onUpdate(order);
      setTimeout(()=>show(order),0);
    });
    dialog.classList.add('co-dialog');
  }
  function content(order) {
    const paid=order.status==='paid';
    const status=paid?'支付成功 · 积分已到账':order.status==='closed'?'订单已关闭':order.expired?'二维码已过期，请查询是否已付款':order.channel==='manual'?'等待管理员核实收款':order.qr_url?'请使用'+channelName(order.channel)+'扫码':'正在等待支付平台确认';
    return `<div class="co-package"><span>${Number(order.credits).toLocaleString('zh-CN')}积分 · ${esc(channelName(order.channel))}</span><strong>${money(order.price_cents)}</strong></div><div class="co-payment ${paid?'co-paid':''}">${paid?'<span class="co-success">✓</span>':order.qr_url?`<img src="${esc(order.qr_url)}" width="232" height="232" alt="${esc(channelName(order.channel))}付款二维码">`:'<span class="co-placeholder">'+(order.channel==='manual'?'人工核实':'等待确认')+'</span>'}<strong>${status}</strong><p>${order.channel==='manual'?'请联系管理员安排付款。创建订单不代表已经付款。':'请核对金额后付款。积分仅在平台验签确认交易成功后发放。'}</p>${order.payment_error?`<p class="co-error">${esc(order.payment_error)}</p>`:''}</div><div class="co-order-number">订单号 <code>${esc(order.id)}</code></div>${!paid&&order.channel!=='manual'?`<footer><button type="button" class="ws-button" data-co-refresh>我已付款，查询状态</button>${!order.qr_url&&!order.expired?'<button type="button" class="ws-button ws-primary" data-co-retry>重试获取二维码</button>':''}</footer>`:''}`;
  }
  function show(order) {
    const dialog=modal('充值订单',`<div class="co-body">${content(order)}</div>`);dialog.classList.add('co-dialog');
    let current=order,checking=false,notified=order.status==='paid';
    async function update(force=false,retry=false) {
      if(checking||!dialog.open)return;
      checking=true;
      try {
        const next=await request('/payments/orders/'+current.id+(retry?'/retry':force?'/refresh':''),force||retry?{}:undefined);
        if(JSON.stringify(next)!==JSON.stringify(current)) {
          current=next;dialog.querySelector('.co-body').innerHTML=content(current);
          if(current.status==='paid'&&!notified){notified=true;await onUpdate(current);toast('充值成功，积分已到账');}
        }
      }catch(error){if(force||retry)toast(error.message);}
      finally{checking=false;}
    }
    dialog.addEventListener('click',event=>{if(event.target.closest('[data-co-refresh]'))update(true);if(event.target.closest('[data-co-retry]'))update(true,true);});
    const timer=setInterval(()=>{if(current.status==='pending'&&current.channel!=='manual')update();},3000);
    dialog.addEventListener('close',()=>clearInterval(timer));
  }
  async function resume(orderId){show(await request('/payments/orders/'+orderId));}
  document.addEventListener('click',async event=>{
    const button=event.target.closest('[data-payment-order],[data-payment-admin-refresh],[data-payment-setup]');
    if(!button)return;
    try {
      if(button.dataset.paymentOrder){await resume(button.dataset.paymentOrder);return;}
      if(button.dataset.paymentAdminRefresh){const order=await request('/payments/admin/orders/'+button.dataset.paymentAdminRefresh+'/refresh',{});toast(order.status==='paid'?'支付已确认，积分已到账':'尚未确认付款，请稍后刷新');return;}
      const data=await request('/payments/admin/configuration');
      modal('支付配置状态',`<p class="st-dialog-note">${esc(data.instructions)}</p><div class="co-channels">${data.channels.map(channel=>`<div class="co-channel"><span><strong>${esc(channel.name)}</strong><small>${esc(channel.message)}</small></span><em>${channel.enabled?'已配置':'待配置'}</em></div>`).join('')}</div><p class="st-dialog-note">服务器配置文件：<code>${esc(data.config_file)}</code></p><p class="st-dialog-note">私钥不能通过聊天、公开仓库或网页静态目录提供。真实收款还需签约产品及公开HTTPS回调。</p>`);
    }catch(error){toast(error.message);}
  });
  return {choose,resume};
}
