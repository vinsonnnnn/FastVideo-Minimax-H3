"use strict";
(() => {
  const $ = (id) => document.getElementById(id);
  let jobId = new URL(location.href).searchParams.get("job");
  let busy = false;
  let ready = false;
  let previewUrl;
  const fail = (message = "") => {
    $("error").textContent = message;
    $("error").hidden = !message;
  };
  const api = async (path, options = {}) => {
    const response = await fetch(path, { ...options, signal: AbortSignal.timeout(150000) });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error?.message || data.detail || `HTTP ${response.status}`);
    return data;
  };
  const setBusy = (value) => {
    busy = value;
    $("submit").disabled = busy || !ready;
    $("submit").textContent = value ? "等待镜头完成…" : "生成镜头";
  };
  const readImage = (file) => new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(new Error("读取参考图失败。"));
    reader.readAsDataURL(file);
  });
  const follow = async () => {
    if (!jobId || busy) return;
    setBusy(true);
    fail();
    $("resume").hidden = true;
    $("job").textContent = `任务：${jobId}`;
    try {
      const deadline = Date.now() + 60 * 60 * 1000;
      while (true) {
        const job = await api(`/api/generations/${encodeURIComponent(jobId)}`);
        const labels = { queued: "已排队", in_progress: "正在生成画面和声音…", completed: "镜头生成完成", failed: "生成失败" };
        $("status").textContent = labels[job.status] || job.status;
        if (job.status === "completed") {
          const content = `/api/generations/${encodeURIComponent(jobId)}/content`;
          $("video").src = content;
          $("video").hidden = false;
          $("download").href = content;
          $("download").download = `${jobId}.mp4`;
          $("download").hidden = false;
          break;
        }
        if (job.status === "failed") throw new Error(job.error?.message || "请检查服务器日志。" );
        if (Date.now() > deadline) throw new Error("查询已超过一小时，可稍后重新查询。" );
        await new Promise((resolve) => setTimeout(resolve, 2000));
      }
    } catch (error) {
      fail(error.message);
      $("resume").hidden = false;
    } finally { setBusy(false); }
  };
  $("reference").addEventListener("change", () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    const file = $("reference").files[0];
    $("reference-preview").hidden = !file;
    if (file) { previewUrl = URL.createObjectURL(file); $("reference-preview").src = previewUrl; }
  });
  $("resume").addEventListener("click", follow);
  $("form").addEventListener("submit", async (event) => {
    event.preventDefault();
    if (busy || !ready) return;
    fail();
    const file = $("reference").files[0];
    if (!file || file.size > 15 * 1024 * 1024) { fail("请选择不超过 15 MiB 的参考图。" ); return; }
    if (!$("prompt").value.trim()) { fail("请填写镜头描述。" ); return; }
    setBusy(true);
    $("video").hidden = true;
    $("download").hidden = true;
    $("resume").hidden = true;
    $("status").textContent = "正在提交镜头…";
    try {
      const job = await api("/api/generations", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: $("prompt").value, reference: await readImage(file), seed: Number($("seed").value) }) });
      jobId = job.id;
      const url = new URL(location.href); url.searchParams.set("job", jobId); history.replaceState({}, "", url);
      setBusy(false);
      await follow();
    } catch (error) {
      // Never retry POST automatically: an ambiguous network failure may have created a job.
      $("status").textContent = "提交结果未确认。";
      fail(`${error.message} 请求不会自动重试；请检查服务器任务记录后再提交。`);
    } finally { setBusy(false); }
  });
  api("/api/status").then((info) => {
    ready = info.ready;
    $("connection").textContent = `后端已连接 · ${info.model}`;
    $("mode").textContent = info.mock ? "模拟演示：输出为测试图案和提示音，未运行 H3 模型。" : "真实 H3 推理 · 分辨率和时长使用服务器配置。";
    setBusy(false);
    if (jobId) follow();
  }).catch((error) => { $("connection").textContent = "后端未就绪，请检查隧道或启动日志后刷新。"; fail(error.message); });
})();
