/* 关怀助手前端逻辑 */
"use strict";
const $ = (sel, el = document) => el.querySelector(sel);
const $$ = (sel, el = document) => [...el.querySelectorAll(sel)];

async function api(path, opts = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
  return data;
}

function toast(msg, isErr = false) {
  const t = $("#toast");
  t.textContent = msg;
  t.className = "toast" + (isErr ? " err" : "");
  t.hidden = false;
  clearTimeout(t._timer);
  t._timer = setTimeout(() => { t.hidden = true; }, 2600);
}

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, c => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

function fileToB64(file) {
  return new Promise((resolve, reject) => {
    const r = new FileReader();
    r.onload = () => resolve(r.result.split(",")[1]);
    r.onerror = reject;
    r.readAsDataURL(file);
  });
}

/* ---------- 页面切换 ---------- */
function show(page) {
  $$(".page").forEach(p => p.classList.toggle("active", p.id === "page-" + page));
  $$("nav a").forEach(a => a.classList.toggle("active", a.dataset.page === page));
  const loaders = {
    dashboard: loadDashboard, roster: loadRoster, templates: loadTemplates,
    config: loadConfig, logs: loadLogs,
  };
  if (loaders[page]) loaders[page]().catch(e => toast(e.message, true));
}
$$("nav a").forEach(a => a.addEventListener("click", e => { e.preventDefault(); show(a.dataset.page); }));

/* ---------- 公共渲染 ---------- */
function eventHtml(ev, idx) {
  const years = ev.years ? ` · ${ev.years}周年` : "";
  const poster = ev.poster
    ? `<img class="event-poster" src="${esc(ev.poster)}" data-full="${esc(ev.poster)}" alt="海报">`
    : "";
  return `<div class="event">
    ${poster}
    <div class="event-body">
      <div class="event-title"><b>${esc(ev.name)}</b>
        <span class="badge">${esc(ev.category)}${years ? " · " + ev.years + "周年" : ""}</span>
        <small>${esc(ev.company)}｜${esc(ev.project)}</small></div>
      <div class="event-copy">${esc(ev.copy)}</div>
    </div></div>`;
}

document.addEventListener("click", e => {
  if (e.target.matches(".event-poster")) {
    $("#lightbox img").src = e.target.dataset.full;
    $("#lightbox").hidden = false;
  }
});
$("#lightbox").addEventListener("click", () => { $("#lightbox").hidden = true; });

/* ---------- 仪表盘 ---------- */
async function loadDashboard() {
  const d = await api("/api/dashboard");
  $("#dash-date").textContent = `今天是 ${d.today}`;
  $("#stat-birthday").textContent = d.counts["生日"] || 0;
  $("#stat-founding").textContent = d.counts["成立周年"] || 0;
  $("#stat-entry").textContent = d.counts["入园周年"] || 0;
  const ch = d.channel;
  $("#stat-channel").textContent = ch.mode === "robot" ? (ch.webhook_set ? "群机器人 ✓" : "未配置")
    : ch.mode === "app" ? "企微应用" : "未配置";
  $("#dash-count").textContent = d.events.length ? `${d.events.length} 位` : "";
  $("#dash-events").innerHTML = d.events.length
    ? d.events.map(eventHtml).join("")
    : `<div class="empty">今天没有命中节点</div>`;
  $("#dash-recent").innerHTML = d.recent.length
    ? `<table class="table"><tbody>${d.recent.map(l => `
        <tr><td style="width:90px">${esc(l.date)}</td><td><b>${esc(l.name)}</b> · ${esc(l.category)}</td>
        <td>${esc(l.company)}</td>
        <td style="width:80px"><span class="badge ${l.status === "ok" ? "ok" : l.status === "fail" ? "fail" : "dim"}">${esc(l.status)}</span></td></tr>`).join("")}
      </tbody></table>`
    : `<div class="empty">还没有发送记录</div>`;
}

/* ---------- 台账 ---------- */
const ROSTER_FIELDS = [
  ["类别", "select", ["生日", "成立周年", "入园周年"], true],
  ["企业名称", "text", null, true], ["所属项目", "text"], ["姓名", "text", null, true],
  ["职务", "text"], ["性别", "select", ["男", "女", ""]], ["节点日期", "date", null, true],
];
const CATS = ["全部", "生日", "成立周年", "入园周年"];
const CAT_TAG = { "生日": "tag-birth", "成立周年": "tag-found", "入园周年": "tag-entry" };
const RS = { q: "", cat: "全部", sortKey: "next", sortDir: 1, page: 1, pageSize: 15, records: [] };

function nextOccur(dateStr) {
  const m = String(dateStr || "").match(/^(\d{4})-(\d{1,2})-(\d{1,2})/);
  if (!m) return { days: 9999, md: "" };
  const today = new Date(); today.setHours(0, 0, 0, 0);
  let dt = new Date(today.getFullYear(), +m[2] - 1, +m[3]);
  if (dt < today) dt = new Date(today.getFullYear() + 1, +m[2] - 1, +m[3]);
  return { days: Math.round((dt - today) / 86400000), md: `${m[2].padStart(2, "0")}-${m[3].padStart(2, "0")}` };
}

function rosterFiltered() {
  const q = RS.q.toLowerCase();
  let rows = RS.records.filter(r =>
    (RS.cat === "全部" || r["类别"] === RS.cat) &&
    (!q || Object.values(r).some(v => String(v).toLowerCase().includes(q))));
  const dir = RS.sortDir, key = RS.sortKey;
  rows = rows.slice().sort((a, b) => {
    if (key === "next") return (nextOccur(a["节点日期"]).days - nextOccur(b["节点日期"]).days) * dir;
    return String(a[key] ?? "").localeCompare(String(b[key] ?? ""), "zh") * dir;
  });
  return rows;
}

function renderRosterTabs() {
  const count = c => c === "全部" ? RS.records.length : RS.records.filter(r => r["类别"] === c).length;
  $("#roster-tabs").innerHTML = CATS.map(c =>
    `<button class="tab${c === RS.cat ? " active" : ""}" data-cat="${c}">${c}<i>${count(c)}</i></button>`).join("");
}

function renderRosterTable() {
  const rows = rosterFiltered();
  const totalPages = Math.max(1, Math.ceil(rows.length / RS.pageSize));
  RS.page = Math.min(RS.page, totalPages);
  const pageRows = rows.slice((RS.page - 1) * RS.pageSize, RS.page * RS.pageSize);

  $("#roster-table tbody").innerHTML = pageRows.length ? pageRows.map((r, i) => {
    const { days, md } = nextOccur(r["节点日期"]);
    const dayCls = days === 0 ? "day-today" : days <= 7 ? "day-soon" : "";
    const dayLabel = days === 0 ? "就是今天" : days === 1 ? "明天" : `${days} 天后`;
    return `<tr>
      <td class="dim-cell">${(RS.page - 1) * RS.pageSize + i + 1}</td>
      <td><span class="cat-tag ${CAT_TAG[r["类别"]] || ""}">${esc(r["类别"])}</span></td>
      <td>${esc(r["企业名称"])}</td><td>${esc(r["所属项目"])}</td>
      <td><b>${esc(r["姓名"])}</b></td><td>${esc(r["职务"])}</td><td>${esc(r["性别"])}</td>
      <td><div class="date-cell">${esc(md)}<span class="day-badge ${dayCls}">${dayLabel}</span></div></td>
      <td class="ops"><button data-edit="${RS.records.indexOf(r)}">编辑</button><button class="del" data-del="${RS.records.indexOf(r)}">删除</button></td></tr>`;
  }).join("")
    : `<tr><td colspan="9"><div class="empty">${RS.records.length ? "没有匹配的记录" : "暂无记录，点击右上角「新增」或「导入 Excel」"}</div></td></tr>`;

  renderRosterPager(rows.length, totalPages);
}

function renderRosterPager(total, totalPages) {
  let pages = "";
  for (let p = 1; p <= totalPages; p++) {
    if (totalPages > 7 && p > 2 && p < totalPages - 1 && Math.abs(p - RS.page) > 1) {
      if (!pages.endsWith("<i>…</i>")) pages += "<i>…</i>";
      continue;
    }
    pages += `<button class="pg${p === RS.page ? " active" : ""}" data-p="${p}">${p}</button>`;
  }
  $("#roster-pager").innerHTML = total
    ? `<span class="pg-total">共 ${total} 条</span>
       <button class="pg" data-p="${RS.page - 1}" ${RS.page <= 1 ? "disabled" : ""}>‹</button>
       ${pages}
       <button class="pg" data-p="${RS.page + 1}" ${RS.page >= totalPages ? "disabled" : ""}>›</button>`
    : "";
}

async function loadRoster(keepState = true) {
  $("#roster-table tbody").innerHTML = `<tr><td colspan="9"><div class="empty">加载中…</div></td></tr>`;
  const { records } = await api("/api/roster");
  RS.records = records;
  if (!keepState) Object.assign(RS, { q: "", cat: "全部", sortKey: "next", sortDir: 1, page: 1 });
  renderRosterTabs(); renderRosterTable();
}

function renderRoster() { renderRosterTabs(); renderRosterTable(); }

$("#roster-tabs").addEventListener("click", e => {
  const cat = e.target.dataset.cat;
  if (!cat) return;
  RS.cat = cat; RS.page = 1; renderRoster();
});

let rosterQTimer;
$("#roster-q").addEventListener("input", () => {
  clearTimeout(rosterQTimer);
  rosterQTimer = setTimeout(() => { RS.q = $("#roster-q").value.trim(); RS.page = 1; renderRosterTable(); }, 200);
});

$("#roster-table thead").addEventListener("click", e => {
  const th = e.target.closest("th.sortable");
  if (!th) return;
  const key = th.dataset.sort;
  if (RS.sortKey === key) RS.sortDir *= -1;
  else { RS.sortKey = key; RS.sortDir = 1; }
  $$("#roster-table thead th.sortable").forEach(t => {
    t.classList.toggle("active", t.dataset.sort === RS.sortKey);
    t.classList.toggle("desc", t.dataset.sort === RS.sortKey && RS.sortDir === -1);
  });
  renderRosterTable();
});

$("#roster-pager").addEventListener("click", e => {
  const p = e.target.dataset.p;
  if (!p) return;
  RS.page = +p;
  renderRosterTable();
});

$("#roster-table").addEventListener("click", async e => {
  const edit = e.target.dataset.edit, del = e.target.dataset.del;
  if (edit !== undefined) openRosterModal(RS.records[+edit], +edit);
  if (del !== undefined && confirm(`确认删除「${RS.records[+del]["姓名"]}」的记录？`)) {
    await api(`/api/roster?index=${del}`, { method: "DELETE" });
    toast("已删除"); loadRoster();
  }
});

function openRosterModal(rec, index) {
  $("#modal-title").textContent = index === undefined ? "新增记录" : `编辑记录 · ${rec["姓名"]}`;
  $("#modal-form").innerHTML = ROSTER_FIELDS.map(([name, type, options, required]) => {
    const val = rec ? (rec[name] ?? "") : "";
    const req = required ? `<i class="req">*</i>` : "";
    if (type === "select") {
      return `<label>${req}${name}<select class="input" data-f="${name}">${
        options.map(o => `<option ${o === val ? "selected" : ""}>${o || "未填写"}</option>`).join("")}</select></label>`;
    }
    return `<label>${req}${name}<input class="input" data-f="${name}" type="${type === "date" ? "date" : "text"}" value="${esc(val)}"></label>`;
  }).join("");
  $("#modal").hidden = false;
  $("#modal-ok").onclick = async () => {
    const body = {};
    $$("#modal-form [data-f]").forEach(inp => body[inp.dataset.f] = inp.value.trim());
    const missing = ROSTER_FIELDS.filter(([n, , , req]) => req && !body[n]);
    if (missing.length) {
      $$("#modal-form [data-f]").forEach(inp => inp.classList.toggle("input-err",
        missing.some(([n]) => n === inp.dataset.f)));
      return toast(`请填写：${missing.map(([n]) => n).join("、")}`, true);
    }
    try {
      if (index === undefined) await api("/api/roster", { method: "POST", body });
      else await api(`/api/roster?index=${index}`, { method: "PUT", body });
      $("#modal").hidden = true; toast("已保存"); loadRoster();
    } catch (err) { toast(err.message, true); }
  };
}
$("#roster-add").addEventListener("click", () => openRosterModal(undefined, undefined));
$("#modal-cancel").addEventListener("click", () => { $("#modal").hidden = true; });
$("#roster-import").addEventListener("click", () => {
  const input = document.createElement("input");
  input.type = "file"; input.accept = ".xlsx";
  input.onchange = async () => {
    const file = input.files[0];
    if (!file) return;
    if (!confirm(`导入将覆盖现有全部 ${RS.records.length} 条记录，且不可恢复，确定继续？`)) return;
    try {
      const data_b64 = await fileToB64(file);
      const r = await api("/api/roster/import", { method: "POST", body: { data_b64 } });
      toast(`导入成功，共 ${r.count} 条`); loadRoster();
    } catch (err) { toast(err.message, true); }
  };
  input.click();
});

/* ---------- 模板与海报 ---------- */
const TPL_KEYS = ["生日", "成立周年", "入园周年", "英文"];
async function loadTemplates() {
  const { templates } = await api("/api/templates");
  $("#tpl-grid").innerHTML = TPL_KEYS.map(k => `
    <div class="tpl-item"><label>${k}模板</label>
    <textarea class="input" data-tpl="${k}">${esc(templates[k])}</textarea></div>`).join("");
  $("#bg-grid").innerHTML = TPL_KEYS.slice(0, 3).map(k => `
    <div class="bg-slot"><img src="/api/bg/${encodeURIComponent(k)}?t=${Date.now()}" alt="${k}底图"
      onerror="this.style.opacity=.25">
      <div class="bg-name">${k}底图</div>
      <label class="upload">更换图片<input type="file" accept="image/*" data-bg="${k}"></label></div>`).join("");
  $$("#bg-grid input[data-bg]").forEach(inp => inp.addEventListener("change", async () => {
    const file = inp.files[0];
    if (!file) return;
    try {
      const data_b64 = await fileToB64(file);
      await api("/api/poster-bg", { method: "POST", body: { category: inp.dataset.bg, data_b64 } });
      toast("背景图已更新"); loadTemplates();
    } catch (err) { toast(err.message, true); }
  }));
}
$("#tpl-save").addEventListener("click", async () => {
  const body = {};
  $$("#tpl-grid [data-tpl]").forEach(t => body[t.dataset.tpl] = t.value);
  try { await api("/api/templates", { method: "PUT", body }); toast("模板已保存"); }
  catch (err) { toast(err.message, true); }
});

/* ---------- 推送配置 ---------- */
async function loadConfig() {
  const { config } = await api("/api/config");
  const w = config.wecom || {};
  $("#cfg-mode").value = w.mode || "dingtalk";
  $("#cfg-push-time").value = config.push_time || "10:00";
  $("#cfg-webhook").value = w.webhook || "";
  $("#cfg-corpid").value = w.corpid || "";
  $("#cfg-secret").value = w.secret || "";
  $("#cfg-agentid").value = w.agentid || "";
  $("#cfg-touser").value = w.touser || "";
  const sig = config.project_signature || {};
  renderSig(sig);
}
function renderSig(sig) {
  $("#cfg-sig").innerHTML = Object.entries(sig).map(([k, v]) => `
    <div class="sig-row"><input class="input" data-sig-k value="${esc(k)}">
    <input class="input" data-sig-v value="${esc(v)}">
    <button class="del" type="button" title="删除">×</button></div>`).join("")
    || `<div class="empty">暂无映射</div>`;
  $$("#cfg-sig .del").forEach(b => b.onclick = () => b.closest(".sig-row").remove());
}
$("#sig-add").addEventListener("click", () => {
  $("#cfg-sig").insertAdjacentHTML("beforeend",
    `<div class="sig-row"><input class="input" data-sig-k placeholder="所属项目">
     <input class="input" data-sig-v placeholder="落款名">
     <button class="del" type="button">×</button></div>`);
  const rows = $$("#cfg-sig .sig-row");
  rows[rows.length - 1].querySelector(".del").onclick = e => e.target.closest(".sig-row").remove();
});
$("#cfg-save").addEventListener("click", async () => {
  const sig = {};
  $$("#cfg-sig .sig-row").forEach(row => {
    const k = $("[data-sig-k]", row).value.trim(), v = $("[data-sig-v]", row).value.trim();
    if (k) sig[k] = v;
  });
  const body = {
    wecom: {
      mode: $("#cfg-mode").value, webhook: $("#cfg-webhook").value.trim(),
      corpid: $("#cfg-corpid").value.trim(), secret: $("#cfg-secret").value.trim(),
      agentid: $("#cfg-agentid").value.trim() || 0, touser: $("#cfg-touser").value.trim(),
    },
    project_signature: sig,
    push_time: $("#cfg-push-time").value || "10:00",
  };
  try {
    const r = await api("/api/config", { method: "PUT", body });
    toast(r.cron ? "配置已保存，" + r.cron : "配置已保存");
  }
  catch (err) { toast(err.message, true); }
});
$("#cfg-test").addEventListener("click", async () => {
  toast("正在发送测试消息…");
  try { await api("/api/config/test", { method: "POST" }); toast("测试消息已发出，请到钉钉/群里查看"); }
  catch (err) { toast("发送失败：" + err.message, true); }
});

/* ---------- 发送记录 ---------- */
async function loadLogs() {
  const { logs } = await api("/api/logs");
  const filter = $("#log-filter").value;
  const rows = logs.filter(l => !filter || l.status === filter);
  $("#log-table tbody").innerHTML = rows.length ? rows.map(l => `
    <tr><td>${esc(l.ts || "")}</td><td>${esc(l.date)}</td><td><b>${esc(l.name)}</b></td>
    <td><span class="badge">${esc(l.category)}</span></td><td>${esc(l.company)}</td>
    <td><span class="badge ${l.status === "ok" ? "ok" : l.status === "fail" ? "fail" : "dim"}">${esc(l.status)}</span>
      ${l.error ? `<div class="hint">${esc(l.error)}</div>` : ""}</td>
    <td>${l.poster ? `<a href="${esc(l.poster)}" target="_blank" class="badge dim">查看</a>` : "–"}</td></tr>`).join("")
    : `<tr><td colspan="7"><div class="empty">暂无记录</div></td></tr>`;
}
$("#log-filter").addEventListener("change", loadLogs);

/* ---------- 手动运行 ---------- */
let previewDate = null;
$("#run-date").value = new Date().toISOString().slice(0, 10);
$("#run-preview").addEventListener("click", async () => {
  const date = $("#run-date").value;
  if (!date) return toast("请选择日期", true);
  const { events } = await api("/api/preview?date=" + date);
  previewDate = date;
  $("#run-events").innerHTML = events.length
    ? `<div class="card"><h2>命中 ${events.length} 条</h2>${events.map(eventHtml).join("")}</div>`
    : `<div class="card"><div class="empty">该日期没有命中节点</div></div>`;
  $("#run-dry").disabled = false;
  $("#run-push").disabled = false;
});
async function doRun(dry) {
  if (!previewDate) return;
  if (!dry && !confirm(`确认向群机器人真实推送 ${previewDate} 的祝福？`)) return;
  $("#run-out").hidden = false;
  $("#run-out").textContent = "运行中…";
  try {
    const r = await api("/api/run", { method: "POST", body: { date: previewDate, dry_run: dry } });
    $("#run-out").textContent = r.output + (r.code ? `\n[退出码 ${r.code}]` : "");
    toast(r.code ? "完成（有失败项，见输出）" : "执行成功");
  } catch (err) { $("#run-out").textContent = "执行失败：" + err.message; }
}
$("#run-dry").addEventListener("click", () => doRun(true));
$("#run-push").addEventListener("click", () => doRun(false));

/* ---------- 启动 ---------- */
loadDashboard().catch(e => toast(e.message, true));
