/* 军师 — 前端逻辑（无框架，原生 JS） */

const $ = (id) => document.getElementById(id);

const state = {
  meta: null,
  view: "home",
  scenario: null,
  my_sliders: {},      // 性格滑轨值 {轴id: 0-100}，空=全部居中
  their_sliders: {},
  my_gender: null,
  their_gender: null,
  replies: [],
  image: null,         // { data, media_type, dataUrl }
  activeArchive: null, // { id, name } —— 当前正在续写的档案
  record: "",          // 累积的关系记录（持久、会长大）
  mode: "reply",
  vaultOpen: false,    // 隐藏档案「保险柜」是否打开（连点 logo 解锁）
};

/* ---------------- 工具 ---------------- */
function escapeHtml(s) {
  return String(s ?? "")
    .replaceAll("&", "&amp;").replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;").replaceAll('"', "&quot;");
}
function stripEmoji(s) {
  return String(s ?? "")
    .replace(/\p{Extended_Pictographic}(?:️|‍\p{Extended_Pictographic})*/gu, "")
    .replace(/[︎️]/gu, "").replace(/\s{2,}/g, " ").trim();
}
const cleanText = (s) => escapeHtml(stripEmoji(s));

function splitMessages(text) {
  const s = String(text ?? "").trim();
  if (!/第\s*[一二三四五六1-6]\s*条\s*[：:]/.test(s)) return s ? [s] : [];
  const parts = s.split(/第\s*[一二三四五六1-6]\s*条\s*[：:]/).map((p) => p.trim()).filter(Boolean);
  return parts.length ? parts : [s];
}

let toastTimer = null;
function toast(msg) {
  const el = $("toast");
  el.textContent = msg;
  el.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (el.hidden = true), 2000);
}

async function copyText(text) {
  try { await navigator.clipboard.writeText(text); }
  catch {
    const ta = document.createElement("textarea");
    ta.value = text; document.body.appendChild(ta); ta.select();
    document.execCommand("copy"); ta.remove();
  }
  toast("已复制");
}

function zoneClass(v) { return v < 35 ? "zone-safe" : v < 65 ? "zone-warn" : "zone-danger"; }

/* ---------------- 配色主题 ---------------- */
const THEMES = ["sand", "mist", "dusk"];
function setTheme(theme) {
  if (!THEMES.includes(theme)) theme = "sand";
  document.body.dataset.theme = theme;
  try { localStorage.setItem("junshi-theme", theme); } catch {}
  document.querySelectorAll(".theme-dot").forEach((d) => {
    const on = d.dataset.theme === theme;
    d.classList.toggle("active", on);
    d.setAttribute("aria-pressed", on ? "true" : "false");
  });
}
function initTheme() {
  let saved = "sand";
  try { saved = localStorage.getItem("junshi-theme") || "sand"; } catch {}
  setTheme(saved);
  applyTheme();
}
// 场景专属强调色：把当前场景写到 body[data-scene]，CSS 负责换 --accent
function applyTheme() {
  document.body.dataset.scene = state.scenario || "";
}

/* ---------------- 起名弹窗 ---------------- */
function promptArchiveName(def = "", title = "给这段对话起个名") {
  return new Promise((resolve) => {
    const mask = $("nameModalMask"), input = $("nameModalInput");
    const ok = $("nameModalOk"), cancel = $("nameModalCancel");
    $("nameModalTitle").textContent = title;
    input.value = def;
    mask.hidden = false;
    setTimeout(() => { input.focus(); input.select(); }, 30);
    const close = (val) => {
      mask.hidden = true;
      ok.onclick = cancel.onclick = mask.onclick = input.onkeydown = null;
      resolve(val);
    };
    ok.onclick = () => close(input.value.trim() || def);
    cancel.onclick = () => close(null);
    mask.onclick = (e) => { if (e.target === mask) close(null); };
    input.onkeydown = (e) => {
      if (e.key === "Enter") { e.preventDefault(); close(input.value.trim() || def); }
      if (e.key === "Escape") close(null);
    };
  });
}

/* ---------------- 关系记录（累积） ---------------- */
const MY_TAGS = ["我", "me", "本人", "自己"];
const THEM_TAGS = ["对方", "ta", "他", "她", "对方说"];

// 识别一行是谁说的：返回 {speaker, content}；无法识别返回 null
function speakerOf(line) {
  const m = line.match(/^\s*([^\s:：，。!！?？]{1,8})\s*[:：]\s*([\s\S]*)$/);
  if (m) {
    const tag = m[1].trim().toLowerCase();
    if (MY_TAGS.includes(tag)) return { speaker: "me", content: m[2].trim() };
    if (THEM_TAGS.includes(tag)) return { speaker: "them", content: m[2].trim() };
  }
  const bare = line.trim().toLowerCase();          // 整行就是一个说话人标记（无冒号）
  if (MY_TAGS.includes(bare)) return { speaker: "me", content: "" };
  if (THEM_TAGS.includes(bare)) return { speaker: "them", content: "" };
  return null;
}

// 解析成消息序列：标记行设定上下文、未标记行跟随上文、空消息跳过
function parseRecord(text) {
  const out = [];
  let ctx = "them";
  for (const raw of (text || "").split("\n")) {
    const line = raw.trim();
    if (!line) continue;
    if (line.startsWith("【关系近况】") || line.startsWith("———")) { out.push({ note: line }); continue; }
    const s = speakerOf(line);
    let speaker, content;
    if (s) { speaker = s.speaker; content = s.content; ctx = speaker; if (!content) continue; }
    else { speaker = ctx; content = line; }
    if (!content) continue;
    out.push({ speaker, content });
  }
  return out;
}

function parseToBubbles(text) {
  return parseRecord(text).map((m) =>
    m.note
      ? `<div class="rec-note">${cleanText(m.note)}</div>`
      : `<div class="rec-msg ${m.speaker}"><span class="rec-who">${m.speaker === "me" ? "我" : "对方"}</span><div class="bubble ${m.speaker}">${cleanText(m.content)}</div></div>`
  ).join("");
}

function recordLineCount() {
  return parseRecord(state.record).filter((m) => !m.note).length;
}

function renderRecord() {
  const n = recordLineCount();
  $("recordCount").textContent = n ? `${n} 条` : "";
  const tl = $("recordTimeline");
  if (!state.record.trim()) {
    tl.innerHTML = '<div class="record-empty">还没攒下记录。<br>在下面贴第一段对话，问一次就会记到这儿。</div>';
  } else {
    tl.innerHTML = parseToBubbles(state.record);
    tl.scrollTop = tl.scrollHeight;
  }
  updateOnboard();
}

// 三步引导条：只在彻底空白（无记录、新消息框也空）时露出
function updateOnboard() {
  const tip = $("onboardTip");
  if (!tip) return;
  const empty = recordLineCount() === 0 && !$("chatHistory").value.trim();
  tip.hidden = !empty;
}

// 军师看到的上下文 = 累积记录 + 这次的新消息
function buildChatContext() {
  const nm = $("chatHistory").value.trim();
  if (state.record && nm) return state.record + "\n" + nm;
  return state.record || nm;
}

async function persistRecord() {
  if (!state.activeArchive) return;
  try {
    await fetch(`/api/archives/${state.activeArchive.id}`, {
      method: "PUT", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ chat_history: state.record }),
    });
  } catch {}
}

// 问完，把这次的新消息沉淀进累积记录，输入框腾空
async function absorbNewMessage() {
  const nm = $("chatHistory").value.trim();
  if (!nm) return;
  state.record = state.record ? state.record + "\n" + nm : nm;
  $("chatHistory").value = "";
  renderRecord();
  await persistRecord();
}

/* ---------------- 引擎徽章 ---------------- */
function renderEngineBadge() {
  const eng = state.meta.engine;
  let text, llm = false, hint = "";
  if (eng.startsWith("qwen")) { text = "通义千问已接入"; llm = true; }
  else if (eng.startsWith("llm")) { text = "Claude 已接入"; llm = true; }
  else { text = "离线演示模式"; hint = "配置 DASHSCOPE_API_KEY 或 ANTHROPIC_API_KEY 后自动接入"; }
  for (const id of ["engineBadge", "homeEngineBadge"]) {
    const b = $(id); if (!b) continue;
    b.textContent = text; b.title = hint || eng;
    b.classList.toggle("llm", llm);
  }
}

/* ---------------- 视图路由 ---------------- */
function showView(view) {
  state.view = view;
  $("homeView").hidden = view !== "home";
  $("workspaceView").hidden = view !== "workspace";
  window.scrollTo(0, 0);
  if (view === "home") loadHomeArchives();
}

/* ---------------- 首页 ---------------- */
async function loadHomeArchives() {
  const list = $("homeArchiveList");
  const vault = state.vaultOpen;
  let items = [];
  try { items = await (await fetch(`/api/archives${vault ? "?hidden=1" : ""}`)).json(); } catch { items = []; }
  $("archiveTitle").textContent = vault ? "隐藏的档案" : "我的档案";
  $("archivesHome").classList.toggle("vault", vault);
  $("vaultExitBtn").hidden = !vault;
  $("archiveCount").textContent = items.length ? `${items.length} 段聊天` : "";
  if (!items.length) {
    list.innerHTML = vault
      ? '<div class="archive-empty">还没有隐藏档案。在档案卡片上点「隐藏」，就会将其收进这里。</div>'
      : '<div class="archive-empty">还没有档案。点上面「先问一句」，聊完存档，下次继续。</div>';
    return;
  }
  list.innerHTML = items.map((it) => {
    const sc = state.meta.scenarios.find((s) => s.id === it.scenario);
    const last = (it.chat_history || "").split("\n").filter((l) => l.trim()).slice(-1)[0] || "还没有聊天记录";
    const rel = it.relation_text ? ` · ${it.relation_text.slice(0, 16)}` : "";
    const hideBtn = vault
      ? `<button class="ac-hide" data-unhide="${it.id}" title="移出隐藏">取消隐藏</button>`
      : `<button class="ac-hide" data-hide="${it.id}" title="藏起来">隐藏</button>`;
    return `
      <div class="archive-card" data-id="${it.id}">
        <div class="ac-actions">
          ${hideBtn}
          <button class="ac-del" data-del="${it.id}" title="删除">删除</button>
        </div>
        <div class="ac-name">${escapeHtml(it.name)}</div>
        <div class="ac-meta">${sc ? sc.name : it.scenario}${escapeHtml(rel)}</div>
        <div class="ac-last">${cleanText(last.slice(0, 70))}</div>
      </div>`;
  }).join("");
  list.querySelectorAll(".archive-card").forEach((el) => {
    el.addEventListener("click", () => openArchive(items.find((x) => x.id === +el.dataset.id)));
  });
  list.querySelectorAll(".ac-del").forEach((el) => {
    el.addEventListener("click", async (ev) => {
      ev.stopPropagation();
      await fetch(`/api/archives/${el.dataset.del}`, { method: "DELETE" });
      loadHomeArchives();
    });
  });
  list.querySelectorAll("[data-hide]").forEach((el) => {
    el.addEventListener("click", (ev) => { ev.stopPropagation(); setArchiveHidden(el.dataset.hide, 1); });
  });
  list.querySelectorAll("[data-unhide]").forEach((el) => {
    el.addEventListener("click", (ev) => { ev.stopPropagation(); setArchiveHidden(el.dataset.unhide, 0); });
  });
}

async function setArchiveHidden(id, hidden) {
  await fetch(`/api/archives/${id}`, {
    method: "PUT", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ hidden }),
  });
  toast(hidden ? "已收进隐藏档案" : "已移回我的档案");
  loadHomeArchives();
}

function toggleVault(open) {
  state.vaultOpen = open === undefined ? !state.vaultOpen : open;
  if (state.vaultOpen) {
    let learned = false;
    try { learned = localStorage.getItem("junshi-vault-learned") === "1"; } catch {}
    // 第一次解锁时说清楚怎么进出，把「不可学习」变成「用一次就会」
    toast(learned ? "进入隐藏档案" : "进入隐藏档案 · 连点左上角「师」5 下可再进出");
    try { localStorage.setItem("junshi-vault-learned", "1"); } catch {}
  }
  loadHomeArchives();
}

/* ---------------- 选择区渲染 ---------------- */
function renderScenarios() {
  $("scenarioGrid").innerHTML = state.meta.scenarios.map((s) => `
    <button class="scenario-card ${s.id === state.scenario ? "active" : ""}" data-id="${s.id}" aria-pressed="${s.id === state.scenario}">
      <div class="sc-name">${s.name}</div>
      <div class="sc-desc">${s.desc}</div>
    </button>`).join("");
}
// 性格滑轨：按当前场景的轴渲染，值取自 state[side+"_sliders"]，缺省 50（居中）
function sliderState(side) {
  return side === "me" ? state.my_sliders : state.their_sliders;
}
function renderSliders(side) {
  const sc = currentScenario();
  const container = $(side === "me" ? "mySliders" : "theirSliders");
  if (!sc || !sc.sliders) { container.innerHTML = ""; return; }
  const vals = sliderState(side);
  container.innerHTML = sc.sliders.map((ax) => {
    const v = vals[ax.id] ?? 50;
    return `
      <div class="slider-row" data-axis="${ax.id}">
        <span class="slider-end left">${ax.left}</span>
        <input type="range" min="0" max="100" value="${v}" class="slider-input" data-side="${side}" data-axis="${ax.id}"
          aria-label="${side === "me" ? "我" : "ta"}：${ax.left}到${ax.right}">
        <span class="slider-end right">${ax.right}</span>
      </div>`;
  }).join("");
}
// 把当前场景的滑轨翻成中文描述（与后端逻辑一致），给「军师帮我写」用
function describeSlidersJS(side) {
  const sc = currentScenario();
  if (!sc || !sc.sliders) return "";
  const vals = sliderState(side);
  const parts = [];
  for (const ax of sc.sliders) {
    const v = vals[ax.id] ?? 50;
    if (v <= 18) parts.push("非常" + ax.left);
    else if (v <= 38) parts.push("偏" + ax.left);
    else if (v >= 82) parts.push("非常" + ax.right);
    else if (v >= 62) parts.push("偏" + ax.right);
  }
  return parts.join("、");
}
function renderGenders(containerId, activeId) {
  $(containerId).innerHTML = (state.meta.genders || []).map((g) =>
    `<button class="chip ${g.id === activeId ? "active" : ""}" data-id="${g.id}" aria-pressed="${g.id === activeId}">${g.label}</button>`
  ).join("");
}
function renderRelationStages() {
  const sc = currentScenario();
  const labels = (sc && sc.stages) ? sc.stages : (state.meta.relation_stages || []).map((s) => s.label);
  $("relationStages").innerHTML = labels.map((label) =>
    `<button class="chip" data-label="${label}">${label}</button>`
  ).join("");
}
function renderExamples() {
  const sc = state.meta.scenarios.find((s) => s.id === state.scenario);
  $("exampleChips").innerHTML = (sc?.examples || []).map((e) => `<button class="example-chip">${escapeHtml(e)}</button>`).join("");
}
function currentScenario() {
  return state.meta.scenarios.find((s) => s.id === state.scenario);
}
// 预设问题 + 提问框/想说啥占位，都按当前场景走（问导师就不会冒出「ta 喜不喜欢我」）
function applyScenarioHints() {
  const sc = currentScenario();
  if (!sc) return;
  $("consultPresets").innerHTML = (sc.consult || []).map((q) =>
    `<button class="preset-chip">${escapeHtml(q)}</button>`).join("");
  if (sc.ask_hint) $("consultQuestion").placeholder = sc.ask_hint;
  if (sc.intent_hint) $("intent").placeholder = sc.intent_hint;
  if (sc.relation_label) $("relationTitle").textContent = sc.relation_label;   // 正式场景不说「你俩」
  if (sc.record_label) $("recordTitle").textContent = sc.record_label;
  if (sc.relation_hint) $("relationText").placeholder = sc.relation_hint;
  renderRelationStages();   // 关系阶段标签也按场景走（导师/HR/长辈不再显示「暧昧中」）
  renderSliders("me");      // 性格滑轨也按场景走
  renderSliders("their");
}
function renderSelectors() {
  renderScenarios();
  renderGenders("myGenders", state.my_gender);
  renderGenders("theirGenders", state.their_gender);
  renderExamples();
  applyScenarioHints();   // 内部已渲染关系阶段标签 + 滑轨
}

/* ---------------- 截图 ---------------- */
async function processImageFile(file) {
  if (!file || !file.type.startsWith("image/")) { toast("只支持图片"); return; }
  let bitmap;
  try { bitmap = await createImageBitmap(file); } catch { toast("图片读取失败"); return; }
  const MAX = 1400, scale = Math.min(1, MAX / Math.max(bitmap.width, bitmap.height));
  const canvas = document.createElement("canvas");
  canvas.width = Math.max(1, Math.round(bitmap.width * scale));
  canvas.height = Math.max(1, Math.round(bitmap.height * scale));
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = "#fff"; ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
  const dataUrl = canvas.toDataURL("image/jpeg", 0.85);
  state.image = { data: dataUrl.split(",")[1], media_type: "image/jpeg", dataUrl };
  $("imagePreview").src = dataUrl;
  $("imagePreviewWrap").hidden = false;
  toast("截图已就绪");
}
function clearImage() {
  state.image = null;
  $("imagePreview").src = "";
  $("imagePreviewWrap").hidden = true;
}

/* ---------------- 公共请求体 ---------------- */
function contextPayload() {
  return {
    scenario: state.scenario,
    my_sliders: state.my_sliders,
    their_sliders: state.their_sliders,
    my_detail: $("myDetail").value.trim(),
    their_detail: $("theirDetail").value.trim(),
    relation_text: $("relationText").value.trim(),
    my_gender: state.my_gender || "",
    their_gender: state.their_gender || "",
  };
}

/* ---------------- 模式一：帮我回 ---------------- */
function loadingHtml(text) {
  return `<div class="loading"><span class="dots"><span></span><span></span><span></span></span>${text}</div>`;
}

// 把异常翻成人话 + 下一步建议
function friendlyError(err) {
  const raw = (err && err.message) || String(err || "");
  if (/Failed to fetch|NetworkError|load failed/i.test(raw))
    return "连不上军师——检查下后端（uvicorn）是不是在跑，再点重试。";
  if (/40\d|Authentication|api[_ ]?key|unauthor/i.test(raw))
    return "军师没接上，可能是接口 Key 失效了。可以重试，或在 .env 里换一个可用的 Key。";
  if (/请提供|请粘贴|请告诉|填进来|需要聊天|无效/.test(raw))
    return raw;   // 业务校验提示本身就清楚，原样显示
  return "出了点状况：" + raw + "。可以直接重试。";
}
// 结构化错误卡片：清楚说明 + 重试按钮
function showError(containerId, err, retryFn) {
  const el = $(containerId);
  el.innerHTML = `
    <div class="error-card" role="alert">
      <div class="error-msg">${escapeHtml(friendlyError(err))}</div>
      <div class="error-actions"><button class="btn-ghost sm" data-err-retry>重试</button></div>
    </div>`;
  const btn = el.querySelector("[data-err-retry]");
  if (btn && retryFn) btn.addEventListener("click", retryFn);
}

async function generate() {
  const ctx = buildChatContext();
  if (!ctx && !state.image) { toast("先在下面贴一段新消息，或拖一张截图"); $("chatHistory").focus(); return; }
  const btn = $("generateBtn"); btn.disabled = true;
  $("replyResults").innerHTML = loadingHtml("军师正在读这段对话…");
  try {
    const res = await fetch("/api/generate", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ...contextPayload(),
        chat_history: ctx,
        intent: $("intent").value.trim(),
        image_data: state.image ? state.image.data : "",
        image_media_type: state.image ? state.image.media_type : "",
      }),
    });
    if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || `请求失败（${res.status}）`);
    const data = await res.json();
    renderReplies(data, ctx);
    await absorbNewMessage();
    if (data.engine.startsWith("offline-fallback")) toast("AI 暂不可用，已用离线引擎兜底");
  } catch (e) {
    showError("replyResults", e, generate);
  } finally { btn.disabled = false; }
}

function renderReplies(data, chatHistory) {
  state.replies = data.replies;
  state.lastChatHistory = chatHistory;
  const a = data.analysis;
  const analysisHtml = `
    <div class="card">
      <div class="risk-head">
        <span class="risk-name">翻车率</span>
        <span class="risk-val ${zoneClass(a.risk)}"><span class="n">${a.risk}</span> · ${escapeHtml(a.risk_label)}</span>
      </div>
      <div class="risk-bar"><div class="risk-fill ${zoneClass(a.risk)}" style="width:0%"></div></div>
      <ul class="signals">${a.signals.map((s) => `<li>${cleanText(s.meaning)}</li>`).join("")}</ul>
    </div>`;
  const cardsHtml = data.replies.map((r, i) => `
    <div class="card reply-card tone-${r.tone}">
      <div class="reply-head">
        <span class="tone-tag">${cleanText(r.tone_label)}</span>
        <div class="reply-actions">
          <button class="micro-btn" data-act="preview" data-idx="${i}">试发预览</button>
          <button class="micro-btn" data-act="copy" data-idx="${i}">复制</button>
        </div>
      </div>
      <div class="reply-text">${splitMessages(r.text).map((m) => `<div class="msg-line">${cleanText(m)}</div>`).join("")}</div>
      <div class="reply-meta"><span class="meta-key">军师说</span><span>${cleanText(r.rationale)}</span></div>
      <div class="preview-slot"></div>
    </div>`).join("");
  $("replyResults").innerHTML = analysisHtml + cardsHtml;
  requestAnimationFrame(() => requestAnimationFrame(() => {
    const fill = $("replyResults").querySelector(".risk-fill");
    if (fill) fill.style.width = a.risk + "%";
  }));
}

// 末尾几条对话 + 你的回复，渲染成气泡
function previewBubbles(chatHistory, replyText) {
  let html = "";
  for (const m of parseRecord(chatHistory).filter((x) => !x.note).slice(-3)) {
    html += `<div class="bubble ${m.speaker}">${cleanText(m.content)}</div>`;
  }
  for (const m of splitMessages(replyText)) html += `<div class="bubble me">${cleanText(m)}</div>`;
  return `<div class="preview-strip"><span class="preview-label">聊天界面预览</span>${html}</div>`;
}

/* ---------------- 模式二：分析聊天 ---------------- */
async function generateSummary() {
  const ctx = buildChatContext();
  if (!ctx) { toast("还没有记录可分析，先在下面贴段对话"); $("chatHistory").focus(); return; }
  const btn = $("summaryBtn"); btn.disabled = true;
  $("summaryResults").innerHTML = loadingHtml("军师正在把整段聊天捋一遍…");
  try {
    const res = await fetch("/api/summary", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...contextPayload(), chat_history: ctx }),
    });
    if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || `请求失败（${res.status}）`);
    renderSummary(await res.json());
    await absorbNewMessage();
  } catch (e) {
    showError("summaryResults", e, generateSummary);
  } finally { btn.disabled = false; }
}

function renderSummary(d) {
  const score = Math.max(0, Math.min(100, d.vibe_score));
  const zc = score >= 65 ? "zone-safe" : score >= 35 ? "zone-warn" : "zone-danger";
  const zt = score >= 65 ? "氛围不错" : score >= 35 ? "平平淡淡" : "有点危险";
  const green = d.green_flags?.length ? `<div><div class="flags-title flag-green">好的信号</div><ul class="flags-list">${d.green_flags.map((f) => `<li>${escapeHtml(f)}</li>`).join("")}</ul></div>` : "";
  const warn = d.warning_flags?.length ? `<div><div class="flags-title flag-warn">注意点</div><ul class="flags-list">${d.warning_flags.map((f) => `<li>${escapeHtml(f)}</li>`).join("")}</ul></div>` : "";
  $("summaryResults").innerHTML = `
    <div class="card">
      <div class="vibe">
        <div class="vibe-track"><div class="vibe-fill ${zc}" style="width:0%"></div></div>
        <div class="vibe-info"><span class="vibe-num ${zc}">${score}</span><span class="vibe-text">${zt}</span></div>
      </div>
      <div class="sum-sec"><div class="sum-sec-title">关系阶段</div><div class="sum-text">${escapeHtml(d.stage_assessment)}</div></div>
      ${green || warn ? `<div class="sum-sec"><div class="sum-flags">${green}${warn}</div></div>` : ""}
      <div class="sum-sec"><div class="sum-sec-title">对方在释放什么信号</div><ul class="sum-list">${d.their_signals.map((s) => `<li>${escapeHtml(s)}</li>`).join("")}</ul></div>
      <div class="sum-sec"><div class="sum-sec-title">你可能在帮倒忙的地方</div><ul class="sum-list">${d.your_patterns.map((p) => `<li>${escapeHtml(p)}</li>`).join("")}</ul></div>
      <div class="sum-sec"><div class="sum-sec-title">军师的方向建议</div><div class="sum-advice"><div class="sum-text">${escapeHtml(d.strategic_advice)}</div></div></div>
      <div class="sum-sec"><div class="sum-sec-title">下一步具体怎么做</div><div class="sum-next">${escapeHtml(d.next_move)}</div></div>
    </div>`;
  requestAnimationFrame(() => requestAnimationFrame(() => {
    const fill = $("summaryResults").querySelector(".vibe-fill");
    if (fill) fill.style.width = score + "%";
  }));
}

/* ---------------- 模式：帮我评 ---------------- */
async function critique() {
  const draft = $("draftReply").value.trim();
  if (!draft) { toast("先把你想发的那句话贴进来"); $("draftReply").focus(); return; }
  const btn = $("critiqueBtn"); btn.disabled = true;
  $("critiqueResults").innerHTML = loadingHtml("军师正在审你这句…");
  try {
    const res = await fetch("/api/critique", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...contextPayload(), chat_history: buildChatContext(), draft }),
    });
    if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || `请求失败（${res.status}）`);
    renderCritique(await res.json());
    await absorbNewMessage();
  } catch (e) {
    showError("critiqueResults", e, critique);
  } finally { btn.disabled = false; }
}

function renderCritique(d) {
  const score = Math.max(0, Math.min(100, d.score));
  const sz = score >= 65 ? "zone-safe" : score >= 35 ? "zone-warn" : "zone-danger";
  const risk = Math.max(0, Math.min(100, d.risk));
  const rz = zoneClass(risk);
  const strengths = d.strengths?.length ? `<div class="sum-sec"><div class="sum-sec-title">这句做对了</div><ul class="sum-list">${d.strengths.map((s) => `<li>${escapeHtml(s)}</li>`).join("")}</ul></div>` : "";
  const problems = d.problems?.length ? `<div class="sum-sec"><div class="sum-sec-title">要改的地方</div><ul class="sum-list">${d.problems.map((s) => `<li>${escapeHtml(s)}</li>`).join("")}</ul></div>` : "";
  $("critiqueResults").innerHTML = `
    <div class="card">
      <div class="crit-head">
        <div class="crit-score ${sz}"><span class="cs-num">${score}</span><span class="cs-unit">分</span></div>
        <div class="crit-verdict">${escapeHtml(d.one_liner)}</div>
      </div>
      <div class="risk-head"><span class="risk-name">翻车率</span><span class="risk-val ${rz}"><span class="n">${risk}</span></span></div>
      <div class="risk-bar"><div class="risk-fill ${rz}" style="width:0%"></div></div>
      ${strengths}${problems}
      <div class="sum-sec">
        <div class="sum-sec-title">军师改写版</div>
        <div class="reply-text">${splitMessages(d.rewrite).map((m) => `<div class="msg-line">${cleanText(m)}</div>`).join("")}</div>
        <button class="micro-btn" id="copyRewrite" style="margin-top:10px">复制改写版</button>
      </div>
    </div>`;
  requestAnimationFrame(() => requestAnimationFrame(() => {
    const f = $("critiqueResults").querySelector(".risk-fill"); if (f) f.style.width = risk + "%";
  }));
  const cr = $("copyRewrite");
  if (cr) cr.addEventListener("click", () => copyText(splitMessages(d.rewrite).join("\n")));
}

/* ---------------- 模式三：问军师 ---------------- */
async function consult(question) {
  const q = (question || $("consultQuestion").value).trim();
  if (!q) { toast("先告诉军师你想问啥"); $("consultQuestion").focus(); return; }
  $("consultQuestion").value = q;
  const btn = $("consultBtn"); btn.disabled = true;
  $("consultResults").innerHTML = loadingHtml("军师正在琢磨…");
  try {
    const res = await fetch("/api/consult", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...contextPayload(), chat_history: buildChatContext(), question: q }),
    });
    if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || `请求失败（${res.status}）`);
    renderConsult(await res.json());
    await absorbNewMessage();
  } catch (e) {
    showError("consultResults", e, () => consult());
  } finally { btn.disabled = false; }
}

function renderConsult(d) {
  const conf = Math.max(0, Math.min(100, d.confidence || 0));
  const ev = d.evidence?.length ? `<div class="sum-sec"><div class="sum-sec-title">凭什么这么说</div><ul class="sum-list">${d.evidence.map((e) => `<li>${escapeHtml(e)}</li>`).join("")}</ul></div>` : "";
  $("consultResults").innerHTML = `
    <div class="card consult-card">
      <div class="consult-q">你问：${escapeHtml(d.question || "")}</div>
      <div class="verdict">${escapeHtml(d.verdict)}</div>
      <div class="conf-row">
        <span class="conf-label">把握</span>
        <span class="conf-track"><span class="conf-fill" style="width:0%"></span></span>
        <span class="conf-num">${conf}%</span>
      </div>
      <div class="sum-sec"><div class="sum-sec-title">细说</div><div class="sum-text">${escapeHtml(d.read)}</div></div>
      ${ev}
      <div class="sum-sec"><div class="sum-sec-title">那你该怎么办</div><div class="sum-next">${escapeHtml(d.advice)}</div></div>
    </div>`;
  requestAnimationFrame(() => requestAnimationFrame(() => {
    const fill = $("consultResults").querySelector(".conf-fill");
    if (fill) fill.style.width = conf + "%";
  }));
}

/* ---------------- 军师帮我写画像 ---------------- */
async function genProfile(side) {
  const gender = side === "me" ? state.my_gender : state.their_gender;
  const genderObj = (state.meta.genders || []).find((g) => g.id === gender);
  const ta = $(side === "me" ? "myDetail" : "theirDetail");
  const btn = document.querySelector(`[data-genprofile="${side}"]`);
  btn.disabled = true; const old = btn.textContent; btn.textContent = "在写了在写了…";
  try {
    const res = await fetch("/api/profile", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        side, scenario: state.scenario,
        tags: describeSlidersJS(side),
        gender: genderObj?.label || "",
        free_text: ta.value.trim(),
        chat_history: $("chatHistory").value.trim(),
      }),
    });
    const data = await res.json();
    ta.value = data.profile;
    toast(data.engine.startsWith("offline") ? "离线只能粗拼，配置 Key 后更准" : "军师写好了，可以再改");
  } catch { toast("生成失败"); }
  finally { btn.disabled = false; btn.textContent = old; }
}

/* ---------------- 档案：存 / 读 ---------------- */
function setWsTitle(name) {
  $("wsTitle").textContent = name || "还没起名";
  $("wsTitle").classList.toggle("renamable", !!state.activeArchive);
  updateRelationScope();
}
function updateRelationScope() {
  const hint = $("relationScope");
  const n = recordLineCount() + ($("chatHistory").value.trim() ? 1 : 0);
  if (state.activeArchive) hint.textContent = `分析「${state.activeArchive.name}」整份记录${n ? `（约 ${n} 条）` : ""}。`;
  else hint.textContent = n ? `分析已攒下的整份记录（约 ${n} 条）；存档后会一直记着。` : "在下面贴段对话再看。";
}

function archivePayload() {
  return { ...contextPayload(), relation_stage: "", chat_history: state.record };
}

async function saveArchive() {
  await absorbNewMessage();   // 把还没问的新消息也一并收进记录
  if (state.activeArchive) {
    const res = await fetch(`/api/archives/${state.activeArchive.id}`, {
      method: "PUT", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(archivePayload()),
    });
    toast(res.ok ? `已更新档案「${state.activeArchive.name}」` : "更新失败");
  } else {
    const name = await promptArchiveName(suggestArchiveName());
    if (name === null) return;   // 取消
    const res = await fetch("/api/archives", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, ...archivePayload() }),
    });
    if (res.ok) {
      const data = await res.json();
      state.activeArchive = { id: data.id, name: data.name };
      setWsTitle(data.name);
      toast(`已存为档案「${data.name}」`);
    } else toast("存档失败");
  }
}

// 智能默认名：拿 ta 画像第一句或场景名兜底
function suggestArchiveName() {
  const detail = $("theirDetail").value.trim();
  if (detail) {
    const first = detail.split(/[，。\n、,.]/)[0].trim();
    if (first) return first.slice(0, 12);
  }
  const sc = currentScenario();
  return sc ? sc.name : "新的一段";
}

function openArchive(item) {
  if (!item) return;
  state.activeArchive = { id: item.id, name: item.name };
  state.scenario = item.scenario || state.meta.scenarios[0].id;
  state.my_sliders = item.my_sliders || {};
  state.their_sliders = item.their_sliders || {};
  state.my_gender = item.my_gender || null;
  state.their_gender = item.their_gender || null;
  $("myDetail").value = item.my_detail || "";
  $("theirDetail").value = item.their_detail || "";
  $("relationText").value = item.relation_text || "";
  state.record = item.chat_history || "";
  $("chatHistory").value = "";
  $("intent").value = "";
  clearImage();
  applyTheme();
  renderSelectors();
  renderRecord();
  // 档案里已经填过画像，就把折叠区展开，方便用户看到/续改
  $("profileFold").open = !!(item.my_detail || item.their_detail || item.relation_text
    || Object.keys(item.my_sliders || {}).length || Object.keys(item.their_sliders || {}).length);
  setWsTitle(item.name);
  clearResults();
  setMode("reply");
  showView("workspace");
}

function newSession() {
  state.activeArchive = null;
  state.scenario = state.meta.scenarios[0].id;
  state.my_sliders = {}; state.their_sliders = {};
  state.my_gender = null; state.their_gender = null;
  state.record = "";
  ["myDetail", "theirDetail", "relationText", "chatHistory", "intent", "consultQuestion", "draftReply"].forEach((id) => { if ($(id)) $(id).value = ""; });
  clearImage();
  applyTheme();
  renderSelectors();
  renderRecord();
  $("profileFold").open = false;   // 新会话：选填区收起，先走最小路径
  setWsTitle("还没起名");
  clearResults();
  setMode("reply");
  showView("workspace");
}

function clearResults() {
  $("replyResults").innerHTML = '<div class="placeholder">把聊天记录贴上来，军师给你三档能直接发的回复，还会标注一个翻车率。</div>';
  $("critiqueResults").innerHTML = '<div class="placeholder">写好一句拿不准的回复，军师给你分析，再写一段仅供参考。</div>';
  $("summaryResults").innerHTML = '<div class="placeholder">军师会把整段聊天读一遍，判断你俩的关系阶段、对方的信号、你的问题，再给方向。</div>';
  $("consultResults").innerHTML = '<div class="placeholder">敲下心里的疑问，军师结合你们的聊天记录，帮你分析。</div>';
}

/* ---------------- 模式切换 ---------------- */
function setMode(mode) {
  state.mode = mode;
  document.querySelectorAll(".tab-btn").forEach((b) => {
    const on = b.dataset.mode === mode;
    b.classList.toggle("active", on);
    b.setAttribute("aria-selected", on ? "true" : "false");
  });
  $("replyPane").hidden = mode !== "reply";
  $("critiquePane").hidden = mode !== "critique";
  $("relationPane").hidden = mode !== "relation";
  $("consultPane").hidden = mode !== "consult";
  if (mode === "relation") updateRelationScope();
}

/* ---------------- 历史抽屉 ---------------- */
function openDrawer() { $("drawerMask").hidden = false; $("historyDrawer").hidden = false; loadHistoryList(); }
function closeDrawer() { $("drawerMask").hidden = true; $("historyDrawer").hidden = true; }
async function loadHistoryList() {
  const list = $("historyList");
  list.innerHTML = '<div class="history-empty">加载中…</div>';
  const items = await (await fetch("/api/history")).json();
  if (!items.length) { list.innerHTML = '<div class="history-empty">还没有历史记录</div>'; return; }
  list.innerHTML = items.map((it) => {
    const sc = state.meta.scenarios.find((s) => s.id === it.scenario);
    return `
      <div class="history-item" data-id="${it.id}">
        <div class="h-top"><span>${sc ? sc.name : it.scenario}</span><span>${it.created_at}</span></div>
        <div class="h-received">${it.has_image ? "图片记录 · " : ""}${cleanText((it.received || "").slice(0, 60))}</div>
        <button class="h-del" data-del="${it.id}" title="删除">删除</button>
      </div>`;
  }).join("");
  list.querySelectorAll(".history-item").forEach((el) => {
    el.addEventListener("click", () => {
      const it = items.find((x) => x.id === +el.dataset.id);
      if (!it) return;
      $("chatHistory").value = it.received || "";
      $("intent").value = it.intent || "";
      if (it.result) renderReplies(it.result, it.received || "");
      setMode("reply"); closeDrawer(); toast("已载入这条记录");
    });
  });
  list.querySelectorAll(".h-del").forEach((el) => {
    el.addEventListener("click", async (ev) => {
      ev.stopPropagation();
      await fetch(`/api/history/${el.dataset.del}`, { method: "DELETE" });
      loadHistoryList();
    });
  });
}

/* ---------------- 事件绑定 ---------------- */
function bindEvents() {
  // 首页
  $("startBtn").addEventListener("click", newSession);
  $("backHomeBtn").addEventListener("click", () => showView("home"));

  // 选择
  $("scenarioGrid").addEventListener("click", (e) => {
    const c = e.target.closest(".scenario-card"); if (!c) return;
    state.scenario = c.dataset.id;
    state.my_sliders = {}; state.their_sliders = {};   // 换场景换了一套轴，重置回居中
    applyTheme();                                      // 场景专属色
    renderScenarios(); renderExamples(); applyScenarioHints();
  });
  // 滑轨拖动：实时写入 state（事件委托，两个容器共用）
  for (const cid of ["mySliders", "theirSliders"]) {
    $(cid).addEventListener("input", (e) => {
      const inp = e.target.closest(".slider-input"); if (!inp) return;
      sliderState(inp.dataset.side)[inp.dataset.axis] = +inp.value;
    });
  }
  $("myGenders").addEventListener("click", (e) => {
    const c = e.target.closest(".chip"); if (!c) return;
    state.my_gender = state.my_gender === c.dataset.id ? null : c.dataset.id;
    renderGenders("myGenders", state.my_gender);
  });
  $("theirGenders").addEventListener("click", (e) => {
    const c = e.target.closest(".chip"); if (!c) return;
    state.their_gender = state.their_gender === c.dataset.id ? null : c.dataset.id;
    renderGenders("theirGenders", state.their_gender);
  });
  // 关系快捷词：点一下追加到正文
  $("relationStages").addEventListener("click", (e) => {
    const c = e.target.closest(".chip"); if (!c) return;
    const ta = $("relationText"), label = c.dataset.label;
    ta.value = ta.value.trim() ? `${ta.value.trim()}，${label}` : label;
    ta.focus();
  });
  document.querySelectorAll("[data-genprofile]").forEach((b) =>
    b.addEventListener("click", () => genProfile(b.dataset.genprofile)));

  // 例子
  $("exampleChips").addEventListener("click", (e) => {
    const c = e.target.closest(".example-chip"); if (!c) return;
    const ta = $("chatHistory");
    ta.value = ta.value.trim() ? ta.value.trim() + "\n对方：" + c.textContent : "对方：" + c.textContent;
    ta.focus();
  });

  // 三种动作 tab
  document.querySelector(".tabs").addEventListener("click", (e) => {
    const b = e.target.closest(".tab-btn"); if (!b) return; setMode(b.dataset.mode);
  });

  // 回复卡片：预览 / 复制
  $("replyResults").addEventListener("click", (e) => {
    const b = e.target.closest("[data-act]"); if (!b) return;
    const r = state.replies[+b.dataset.idx]; if (!r) return;
    if (b.dataset.act === "copy") copyText(splitMessages(r.text).join("\n"));
    if (b.dataset.act === "preview") {
      const slot = b.closest(".reply-card").querySelector(".preview-slot");
      if (slot.innerHTML) { slot.innerHTML = ""; }
      else { slot.innerHTML = previewBubbles(state.lastChatHistory, r.text); }
    }
  });

  $("generateBtn").addEventListener("click", generate);
  $("critiqueBtn").addEventListener("click", critique);
  $("draftReply").addEventListener("keydown", (e) => { if ((e.metaKey || e.ctrlKey) && e.key === "Enter") critique(); });
  $("summaryBtn").addEventListener("click", generateSummary);
  $("consultBtn").addEventListener("click", () => consult());
  $("consultQuestion").addEventListener("keydown", (e) => { if (e.key === "Enter") consult(); });
  $("consultPresets").addEventListener("click", (e) => {
    const c = e.target.closest(".preset-chip"); if (!c) return; consult(c.textContent);
  });
  $("archiveSaveBtn").addEventListener("click", saveArchive);
  $("chatHistory").addEventListener("keydown", (e) => { if ((e.metaKey || e.ctrlKey) && e.key === "Enter") generate(); });
  $("chatHistory").addEventListener("input", updateOnboard);

  // 累积记录：编辑 / 完成
  $("recordEditBtn").addEventListener("click", () => {
    const tl = $("recordTimeline"), ed = $("recordEditor"), btn = $("recordEditBtn");
    if (ed.hidden) {
      ed.value = state.record; tl.hidden = true; ed.hidden = false; btn.textContent = "完成"; ed.focus();
    } else {
      state.record = ed.value.trim(); ed.hidden = true; tl.hidden = false; btn.textContent = "编辑";
      renderRecord(); persistRecord();
    }
  });

  // 截图：点击 / 粘贴 / 全窗口拖拽
  $("imageDrop").addEventListener("click", () => $("imageInput").click());
  $("imageInput").addEventListener("change", (e) => { if (e.target.files[0]) processImageFile(e.target.files[0]); e.target.value = ""; });
  $("imageRemove").addEventListener("click", (e) => { e.stopPropagation(); e.preventDefault(); clearImage(); });
  $("saveRecordBtn").addEventListener("click", async () => {
    const nm = $("chatHistory").value.trim();
    if (!nm) { toast("先把新消息贴进来"); $("chatHistory").focus(); return; }
    await absorbNewMessage();
    toast("已存入记录");
  });
  window.addEventListener("paste", (e) => {
    const item = [...(e.clipboardData?.items || [])].find((i) => i.type.startsWith("image/"));
    if (item) { e.preventDefault(); processImageFile(item.getAsFile()); }
  });
  let dragDepth = 0;
  window.addEventListener("dragenter", (e) => {
    if (![...(e.dataTransfer?.types || [])].includes("Files")) return;
    dragDepth++; if (state.view === "workspace") $("dropOverlay").hidden = false;
  });
  window.addEventListener("dragover", (e) => { if ([...(e.dataTransfer?.types || [])].includes("Files")) e.preventDefault(); });
  window.addEventListener("dragleave", () => { dragDepth = Math.max(0, dragDepth - 1); if (!dragDepth) $("dropOverlay").hidden = true; });
  window.addEventListener("drop", (e) => {
    if (!e.dataTransfer?.files?.length) return;
    e.preventDefault(); dragDepth = 0; $("dropOverlay").hidden = true;
    if (state.view !== "workspace") return;
    const f = [...e.dataTransfer.files].find((x) => x.type.startsWith("image/"));
    if (f) processImageFile(f);
  });

  // 隐藏入口：连点 logo「军」5 下，开/关隐藏档案
  let brandTaps = 0, brandTimer = null;
  $("brandMark").addEventListener("click", () => {
    brandTaps++;
    clearTimeout(brandTimer);
    brandTimer = setTimeout(() => { brandTaps = 0; }, 1500);
    if (brandTaps >= 5) { brandTaps = 0; toggleVault(true); }
  });
  $("vaultExitBtn").addEventListener("click", () => toggleVault(false));

  // 配色切换：两个切换器共用，事件委托
  document.addEventListener("click", (e) => {
    const dot = e.target.closest(".theme-dot"); if (!dot) return;
    setTheme(dot.dataset.theme);
  });

  // 点标题改名（仅在已存档时）
  $("wsTitle").addEventListener("click", async () => {
    if (!state.activeArchive) return;
    const name = await promptArchiveName(state.activeArchive.name, "给这段对话改个名");
    if (name === null || name === state.activeArchive.name) return;
    const res = await fetch(`/api/archives/${state.activeArchive.id}`, {
      method: "PUT", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    });
    if (res.ok) { state.activeArchive.name = name; setWsTitle(name); toast("改名成功"); }
    else toast("改名失败");
  });

  // 历史
  $("historyBtn").addEventListener("click", openDrawer);
  $("closeDrawerBtn").addEventListener("click", closeDrawer);
  $("drawerMask").addEventListener("click", closeDrawer);
  $("clearHistoryBtn").addEventListener("click", async () => {
    await fetch("/api/history", { method: "DELETE" }); loadHistoryList(); toast("历史已清空");
  });
}

/* ---------------- 启动 ---------------- */
async function init() {
  try { state.meta = await (await fetch("/api/meta")).json(); }
  catch { toast("连不上后端，确认 uvicorn 在跑"); return; }
  state.scenario = state.meta.scenarios[0].id;
  state.my_sliders = {}; state.their_sliders = {};
  initTheme();
  renderEngineBadge();
  renderSelectors();
  bindEvents();
  if (location.hash === "#new") newSession();
  else showView("home");
}
init();
