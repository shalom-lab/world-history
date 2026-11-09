"""Render the interactive viewer: canvas renderer, zoom to cursor, search, EN/中文, export.

Layout is a flex column (header / toolbar / search+chips / chart / foot) so the
chart area does not depend on a hard-coded `calc(100vh - Npx)`.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

import json
import os

import i18n

DATA = str(ROOT / "data")
OUT = str(ROOT / "viewer" / "index.html")


def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return json.load(f)


HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>{title} — timeline viewer</title>
<style>
 *{{box-sizing:border-box}}
 html,body{{height:100%}}
 body{{margin:0;height:100vh;display:flex;flex-direction:column;overflow:hidden;
   font-family:-apple-system,Segoe UI,Roboto,"Microsoft YaHei",Helvetica,Arial,sans-serif;
   color:#1c2436;background:#fff;-webkit-font-smoothing:antialiased}}
 header{{padding:10px 16px 4px;flex:0 0 auto}}
 h1{{font-size:15px;margin:0 0 2px;letter-spacing:.2px}}
 .sub{{font-size:11.5px;color:#66708a}}

 /* ---------- toolbar ---------- */
 .bar{{display:flex;align-items:center;gap:8px;padding:7px 16px;flex:0 0 auto;
   border-top:1px solid #eef1f6;border-bottom:1px solid #eef1f6;background:#fcfdff}}
 .group{{display:inline-flex;border:1px solid #ccd5e4;border-radius:8px;overflow:hidden;background:#fff;
   box-shadow:0 1px 1px #0f18300a}}
 .group button{{border:0;border-radius:0;width:34px;height:29px;display:grid;place-items:center;
   background:#fff;color:#2b3a55;cursor:pointer;padding:0}}
 .group button + button{{border-left:1px solid #e4e9f2}}
 .group button:hover{{background:#eef3fb}}
 .group button:active{{background:#e2eaf7}}
 .group button svg{{width:15px;height:15px;display:block}}
 .ghost{{display:inline-flex;align-items:center;gap:6px;height:29px;padding:0 11px;font:inherit;font-size:12px;
   border:1px solid #ccd5e4;border-radius:8px;background:#fff;color:#2b3a55;cursor:pointer;
   box-shadow:0 1px 1px #0f18300a;transition:background .12s,border-color .12s,transform .06s}}
 .ghost:hover{{background:#eef3fb;border-color:#b9c6dc}}
 .ghost:active{{transform:translateY(1px)}}
 .ghost svg{{width:14px;height:14px;opacity:.8}}
 .ghost.accent{{border-color:#c7d4ea;background:#f4f8ff;color:#1d3f77}}
 .sep{{width:1px;height:20px;background:#e4e9f2;margin:0 2px}}
 .readout{{font-size:12px;color:#3a465e;font-variant-numeric:tabular-nums;margin-left:6px}}
 .pill{{margin-left:auto;height:29px;padding:0 14px;font:inherit;font-size:12px;font-weight:600;
   border:1px solid #1f3864;border-radius:999px;background:#1f3864;color:#fff;cursor:pointer;
   transition:background .12s,box-shadow .12s}}
 .pill:hover{{background:#274a80;box-shadow:0 2px 8px #1f386433}}
 button:focus-visible{{outline:2px solid #4a7fd4;outline-offset:1px}}

 /* ---------- search + chips ---------- */
 .searchrow{{display:flex;align-items:center;gap:10px;padding:6px 16px;flex:0 0 auto;border-bottom:1px solid #eef1f6}}
 .searchbox{{position:relative;flex:0 0 300px}}
 .searchbox svg{{position:absolute;left:9px;top:7px;width:14px;height:14px;opacity:.45}}
 .searchbox input{{width:100%;font:inherit;font-size:12px;padding:5px 9px 5px 29px;border:1px solid #ccd5e4;
   border-radius:8px;background:#fff;outline:none}}
 .searchbox input:focus{{border-color:#4a7fd4;box-shadow:0 0 0 3px #4a7fd41f}}
 #qcount{{font-size:11px;color:#66708a;white-space:nowrap}}
 .chips{{display:flex;gap:4px;overflow:auto;flex:1 1 auto;max-height:26px;scrollbar-width:thin}}
 .chip{{font-size:11px;color:#39435c;display:inline-flex;align-items:center;gap:4px;cursor:pointer;
   border-radius:999px;padding:2px 8px;border:1px solid transparent;white-space:nowrap;user-select:none}}
 .chip:hover{{background:#f0f4fa}}
 .chip.off{{opacity:.32;text-decoration:line-through}}
 .chip i{{width:9px;height:9px;display:inline-block;border-radius:2px;border:1px solid #00000022}}

 /* ---------- chart ---------- */
 #app{{position:relative;display:flex;flex:1 1 auto;min-height:0}}
 #labelsPane{{position:relative;flex:0 0 344px;width:344px;overflow-y:scroll;overflow-x:hidden;
   border-right:1px solid #dfe5ef;background:#fbfbfc;scrollbar-width:thin}}
 #labels{{position:absolute;top:0;left:0;display:block;pointer-events:none;will-change:transform}}
 #labSpacer{{width:1px}}
 #scroll{{position:relative;flex:1;overflow:auto}}
 #spacer{{width:1px;height:1px}}
 #chart{{position:absolute;top:0;left:344px;pointer-events:none}}
 #tip{{position:fixed;pointer-events:none;background:#12161f;color:#fff;font-size:11.5px;line-height:1.45;
   padding:6px 9px;border-radius:6px;max-width:420px;opacity:0;transition:opacity .08s;z-index:9;
   box-shadow:0 4px 14px #0003}}
 .foot{{font-size:11px;color:#7b869c;padding:4px 16px;border-top:1px solid #eef1f6;flex:0 0 auto}}
</style></head>
<body>
<header>
  <h1 id="hTitle">{title}</h1>
  <div class="sub" id="hSub"></div>
</header>
<div class="bar">
  <div class="group">
    <button id="zout" title="zoom out" aria-label="zoom out">
      <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round">
        <circle cx="7" cy="7" r="4.6"/><path d="M10.5 10.5L14 14M5 7h4"/></svg>
    </button>
    <button id="zin" title="zoom in" aria-label="zoom in">
      <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round">
        <circle cx="7" cy="7" r="4.6"/><path d="M10.5 10.5L14 14M5 7h4M7 5v4"/></svg>
    </button>
  </div>
  <button class="ghost" id="reset"></button>
  <button class="ghost" id="fit"></button>
  <span class="sep"></span>
  <button class="ghost" id="expng"></button>
  <button class="ghost" id="excsv"></button>
  <span class="readout" id="readout"></span>
  <button class="pill" id="lang">中文</button>
</div>
<div class="searchrow">
  <div class="searchbox">
    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round">
      <circle cx="7" cy="7" r="4.6"/><path d="M10.5 10.5L14 14"/></svg>
    <input id="q" type="search" autocomplete="off">
  </div>
  <span id="qcount"></span>
  <div class="chips" id="chips"></div>
</div>
<div id="app">
  <div id="labelsPane"><canvas id="labels"></canvas><div id="labSpacer"></div></div>
  <div id="scroll"><div id="spacer"></div></div>
  <canvas id="chart"></canvas>
</div>
<div class="foot" id="foot"></div>
<div id="tip"></div>
<script type="application/json" id="data">{payload}</script>
<script>
const D = JSON.parse(document.getElementById('data').textContent);
const Y0 = D.meta.time_range.start_year, Y1 = D.meta.time_range.end_year;
const SPAN = Y1 - Y0;
const PAD_TOP = 22, PAD_BOT = 8, GUTTER = 344, RIGHT_PAD = 24;
const UI = D.ui;
let lang = 'en';

function t(k) {{ return (UI[lang] && UI[lang][k]) || (UI.en && UI.en[k]) || k; }}
function famName(f) {{ return (lang === 'zh' && D.families_zh[f]) ? D.families_zh[f] : f; }}
function nm(e) {{ return (lang === 'zh' && e.name_zh) ? e.name_zh : e.name; }}
function lb(s) {{ return (lang === 'zh' && s.label_zh) ? s.label_zh : s.label; }}
function fmt(y) {{
  const n = Math.abs(y);
  return y < 0 ? (lang === 'zh' ? '公元前 ' + n : n + ' BCE')
               : (lang === 'zh' ? '公元 ' + y : y + ' CE');
}}
function esc(s) {{ return String(s).replace(/[&<>"]/g, c => ({{'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}}[c])); }}

const scroll = document.getElementById('scroll');
const spacer = document.getElementById('spacer');
const cv = document.getElementById('chart');
const ctx = cv.getContext('2d');
const labelsPane = document.getElementById('labelsPane');
const labSpacer = document.getElementById('labSpacer');
const lcv = document.getElementById('labels');
const lctx = lcv.getContext('2d');
const tip = document.getElementById('tip');
const readout = document.getElementById('readout');
const qEl = document.getElementById('q');
const qCount = document.getElementById('qcount');

const state = {{ zoomX: 1400 / SPAN, rowH: 15, minZoom: 0.02, maxZoom: 60 }};

const byEnt = new Map();
for (const s of D.spans) {{
  if (!byEnt.has(s.entity_id)) byEnt.set(s.entity_id, []);
  byEnt.get(s.entity_id).push(s);
}}
for (const arr of byEnt.values()) arr.sort((a, b) => a.start_year - b.start_year);

const famOn = new Set(D.familiesOn);
let query = '', matches = [], matchIdx = -1, searchIndex = [];
let dirty = false, rafId = 0, syncing = false;
let view = {{ w: 0, h: 0, dpr: 1 }};
let lastW = -1, lastH = -1;

function buildSearchIndex() {{
  searchIndex = D.entities.map(e => {{
    const parts = [e.name, e.name_zh || '', e.language_family || '',
                   D.families_zh[e.language_family] || ''];
    for (const s of (byEnt.get(e.id) || [])) {{
      if (s.label) parts.push(s.label);
      if (s.label_zh) parts.push(s.label_zh);
    }}
    return parts.join(' ').toLowerCase();
  }});
}}

function schedule() {{
  if (dirty) return;
  dirty = true;
  rafId = requestAnimationFrame(() => {{ dirty = false; paint(); }});
}}

const contentW = () => Math.round(SPAN * state.zoomX);
const contentH = () => PAD_TOP + D.entities.length * state.rowH + PAD_BOT;

function applySizes() {{
  const w = contentW() + 4, h = contentH();
  if (w !== lastW) {{ spacer.style.width = w + 'px'; lastW = w; }}
  if (h !== lastH) {{ spacer.style.height = h + 'px'; labSpacer.style.height = h + 'px'; lastH = h; }}
}}

function resize() {{
  view.dpr = window.devicePixelRatio || 1;
  const app = document.getElementById('app');
  view.w = Math.max(1, app.clientWidth - GUTTER);
  view.h = Math.max(1, scroll.clientHeight);
  cv.width = Math.round(view.w * view.dpr); cv.height = Math.round(view.h * view.dpr);
  cv.style.width = view.w + 'px'; cv.style.height = view.h + 'px';
  ctx.setTransform(view.dpr, 0, 0, view.dpr, 0, 0);
  lcv.width = Math.round(GUTTER * view.dpr); lcv.height = Math.round(view.h * view.dpr);
  lcv.style.width = GUTTER + 'px'; lcv.style.height = view.h + 'px';
  lctx.setTransform(view.dpr, 0, 0, view.dpr, 0, 0);
  schedule();
}}

function tickStep() {{
  const target = 90 / state.zoomX;
  for (const s of [10, 20, 50, 100, 200, 250, 500, 1000, 2000]) if (s >= target) return s;
  return 5000;
}}

function cut(txt, maxW) {{
  if (lctx.measureText(txt).width <= maxW) return txt;
  let lo = 0, hi = txt.length;
  while (lo < hi) {{
    const mid = (lo + hi + 1) >> 1;
    if (lctx.measureText(txt.slice(0, mid) + '…').width <= maxW) lo = mid; else hi = mid - 1;
  }}
  return txt.slice(0, lo) + '…';
}}

function paint() {{
  const W = view.w, H = view.h, rh = state.rowH, zx = state.zoomX;
  const sx = scroll.scrollLeft, sy = scroll.scrollTop, lsy = labelsPane.scrollTop;
  const hit = new Set(matches);
  lcv.style.transform = 'translateY(' + lsy + 'px)';

  ctx.clearRect(0, 0, W, H);
  lctx.clearRect(0, 0, GUTTER, H);

  const i0 = Math.max(0, Math.floor((sy - PAD_TOP) / rh));
  const i1 = Math.min(D.entities.length - 1, Math.ceil((sy + H - PAD_TOP) / rh));

  for (let i = i0; i <= i1; i++) {{
    const y = PAD_TOP + i * rh - sy;
    const ly = PAD_TOP + i * rh - lsy;
    const isHit = hit.has(i);
    const bg = isHit ? '#fff3c4' : ((i % 2 === 0) ? '#f3f5f9' : '#ffffff');
    ctx.fillStyle = bg; ctx.fillRect(0, y, W, rh);
    lctx.fillStyle = bg; lctx.fillRect(0, ly, GUTTER, rh);
    if (isHit) {{ lctx.fillStyle = '#e0a800'; lctx.fillRect(0, ly, 3, rh); }}
  }}

  const step = tickStep();
  const yFrom = Y0 + sx / zx, yTo = Y0 + (sx + W) / zx;
  ctx.font = '11px -apple-system,Segoe UI,sans-serif';
  for (let yr = Math.ceil(yFrom / step) * step; yr <= yTo; yr += step) {{
    const x = (yr - Y0) * zx - sx;
    ctx.strokeStyle = (yr % (step * 5) === 0) ? '#c6d0e0' : '#e8edf5';
    ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(x + .5, 0); ctx.lineTo(x + .5, H); ctx.stroke();
    ctx.fillStyle = '#44506b';
    ctx.fillText(fmt(yr), x + 3, 14);
  }}

  for (let i = i0; i <= i1; i++) {{
    const e = D.entities[i];
    const y = PAD_TOP + i * rh - sy;
    const ly = PAD_TOP + i * rh - lsy;
    const arr = byEnt.get(e.id) || [];
    const fs = Math.min(10, rh * 0.62);
    for (const s of arr) {{
      if (!famOn.has(s.language_family || '—')) continue;
      const x0 = (s.start_year - Y0) * zx - sx;
      const x1 = (s.end_year - Y0) * zx - sx;
      if (x1 < -2 || x0 > W + 2) continue;
      const w = Math.max(1, x1 - x0);
      ctx.fillStyle = s.color_hex;
      ctx.fillRect(x0, y + 1, w, Math.max(2, rh - 2));
      const txt = lb(s);
      if (txt && w > 46 && rh >= 11) {{
        ctx.save();
        ctx.beginPath(); ctx.rect(x0, y, w - 3, rh); ctx.clip();
        ctx.fillStyle = '#1a1a1a';
        ctx.font = fs.toFixed(1) + 'px -apple-system,Segoe UI,"Microsoft YaHei",sans-serif';
        ctx.fillText(txt, x0 + 3, y + rh * 0.74);
        ctx.restore();
      }}
    }}
    const lfs = Math.min(11, Math.max(7, rh * 0.64));
    lctx.font = lfs.toFixed(1) + 'px -apple-system,Segoe UI,"Microsoft YaHei",sans-serif';
    const name = nm(e);
    const fam = famName(e.language_family || '');
    let famW = 0;
    if (rh >= 13 && fam) {{
      lctx.font = '8.5px -apple-system,Segoe UI,"Microsoft YaHei",sans-serif';
      famW = lctx.measureText(fam).width;
      lctx.fillStyle = '#7b869c';
      lctx.fillText(fam, GUTTER - RIGHT_PAD - famW, ly + rh * 0.74);
    }}
    lctx.fillStyle = '#1c2436';
    lctx.font = lfs.toFixed(1) + 'px -apple-system,Segoe UI,"Microsoft YaHei",sans-serif';
    const nameMax = GUTTER - RIGHT_PAD - (rh >= 13 ? famW + 10 : 0) - 7;
    lctx.fillText(cut(name, Math.max(40, nameMax)), 7, ly + rh * 0.74);
  }}
  lctx.strokeStyle = '#dfe5ef';
  lctx.beginPath(); lctx.moveTo(GUTTER - .5, 0); lctx.lineTo(GUTTER - .5, H); lctx.stroke();

  updateReadout();
}}

function updateReadout() {{
  const zx = state.zoomX, sx = scroll.scrollLeft;
  const a = Math.round(Y0 + sx / zx), b = Math.round(Y0 + (sx + view.w) / zx);
  readout.textContent = `${{fmt(a)}} – ${{fmt(b)}}　·　` +
    t('readout_1px').replace('{{v}}', (1 / zx).toFixed(2));
}}

function zoomAt(factorX, mx, my, factorY) {{
  const zx = state.zoomX;
  const anchorYear = Y0 + (scroll.scrollLeft + mx) / zx;
  const rowUnits = (scroll.scrollTop + my - PAD_TOP) / state.rowH;
  state.zoomX = Math.min(state.maxZoom, Math.max(state.minZoom, zx * factorX));
  if (factorY && factorY !== 1) state.rowH = Math.min(70, Math.max(6, state.rowH * factorY));
  applySizes();
  scroll.scrollLeft = Math.round((anchorYear - Y0) * state.zoomX - mx);
  scroll.scrollTop = Math.round(PAD_TOP + rowUnits * state.rowH - my);
  schedule();
}}

scroll.addEventListener('scroll', () => {{
  tip.style.opacity = 0;
  if (!syncing) {{ syncing = true; labelsPane.scrollTop = scroll.scrollTop; syncing = false; }}
  schedule();
}});
labelsPane.addEventListener('scroll', () => {{
  if (!syncing) {{ syncing = true; scroll.scrollTop = labelsPane.scrollTop; syncing = false; }}
  schedule();
}});

scroll.addEventListener('wheel', ev => {{
  ev.preventDefault();
  const r = scroll.getBoundingClientRect();
  const mx = ev.clientX - r.left, my = ev.clientY - r.top;
  const f = Math.exp(-ev.deltaY * 0.0016);
  if (ev.shiftKey) zoomAt(1, mx, my, f);
  else zoomAt(f, mx, my, 1);
}}, {{passive: false}});

let drag = null;
scroll.addEventListener('mousedown', ev => {{
  drag = {{x: ev.clientX, y: ev.clientY, l: scroll.scrollLeft, t: scroll.scrollTop}};
  scroll.style.cursor = 'grabbing';
  tip.style.opacity = 0;
}});
window.addEventListener('mousemove', ev => {{
  if (drag) {{
    scroll.scrollLeft = drag.l - (ev.clientX - drag.x);
    scroll.scrollTop = drag.t - (ev.clientY - drag.y);
  }}
}});
window.addEventListener('mouseup', () => {{ drag = null; scroll.style.cursor = 'default'; }});
scroll.addEventListener('dblclick', ev => {{
  const r = scroll.getBoundingClientRect();
  zoomAt(2, ev.clientX - r.left, ev.clientY - r.top, 1);
}});

scroll.addEventListener('mousemove', ev => {{
  if (drag) return;
  const r = scroll.getBoundingClientRect();
  const mx = ev.clientX - r.left, my = ev.clientY - r.top;
  const i = Math.floor((scroll.scrollTop + my - PAD_TOP) / state.rowH);
  if (i < 0 || i >= D.entities.length) {{ tip.style.opacity = 0; return; }}
  const e = D.entities[i];
  const year = Y0 + (scroll.scrollLeft + mx) / state.zoomX;
  let hit = null;
  for (const s of (byEnt.get(e.id) || [])) {{
    if (s.start_year <= year && year <= s.end_year && famOn.has(s.language_family || '—')) {{ hit = s; break; }}
  }}
  if (!hit) {{ tip.style.opacity = 0; return; }}
  const zh = lang === 'zh';
  tip.innerHTML =
    `<b>${{esc(zh ? (e.name_zh || e.name) : e.name)}}</b><br>` +
    `${{esc(zh ? (hit.label_zh || hit.label || t('no_label')) : (hit.label || t('no_label')))}}<br>` +
    `${{fmt(hit.start_year)}} → ${{fmt(hit.end_year)}}` +
    (hit.language_family ? ` · ${{esc(famName(hit.language_family))}}` : '');
  tip.style.left = Math.min(ev.clientX + 14, window.innerWidth - 320) + 'px';
  tip.style.top = (ev.clientY + 16) + 'px';
  tip.style.opacity = 1;
}});
scroll.addEventListener('mouseleave', () => {{ tip.style.opacity = 0; }});

// ---- search
function runSearch() {{
  query = qEl.value.trim().toLowerCase();
  if (!query) {{ matches = []; matchIdx = -1; qCount.textContent = ''; schedule(); return; }}
  matches = [];
  for (let i = 0; i < searchIndex.length; i++) if (searchIndex[i].includes(query)) matches.push(i);
  matchIdx = matches.length ? 0 : -1;
  qCount.textContent = matches.length
    ? t('search_hits').replace('{{n}}', matches.length).replace('{{i}}', 1)
    : t('search_none');
  if (matchIdx >= 0) jumpTo(matches[0]);
  schedule();
}}
function jumpTo(i) {{
  scroll.scrollTop = Math.max(0, PAD_TOP + i * state.rowH - view.h / 2);
  schedule();
}}
function stepMatch(dir) {{
  if (!matches.length) return;
  matchIdx = (matchIdx + dir + matches.length) % matches.length;
  qCount.textContent = t('search_hits').replace('{{n}}', matches.length).replace('{{i}}', matchIdx + 1);
  jumpTo(matches[matchIdx]);
}}
qEl.addEventListener('input', runSearch);
qEl.addEventListener('keydown', ev => {{
  if (ev.key === 'Enter') {{ ev.preventDefault(); stepMatch(ev.shiftKey ? -1 : 1); }}
  if (ev.key === 'Escape') {{ qEl.value = ''; runSearch(); }}
}});

// ---- export
function download(blob, name) {{
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = name;
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 4000);
}}

function exportPNG() {{
  // repaint at the current dpr onto an offscreen canvas covering the visible view
  const off = document.createElement('canvas');
  off.width = cv.width; off.height = cv.height;
  off.getContext('2d').drawImage(cv, 0, 0);
  off.toBlob(b => download(b, 'world-history-' + Math.round(Y0 + scroll.scrollLeft / state.zoomX) + '.png'), 'image/png');
}}

function exportCSV() {{
  const zh = lang === 'zh';
  const head = ['entity_id', zh ? '横带' : 'entity', zh ? '大区' : 'section',
                zh ? '时间段' : 'label', 'start_year', 'end_year',
                zh ? '颜色' : 'color', zh ? '语系' : 'family'];
  const lines = [head.join(',')];
  const quote = v => '"' + String(v == null ? '' : v).replace(/"/g, '""') + '"';
  const eById = new Map(D.entities.map(e => [e.id, e]));
  for (const s of D.spans) {{
    const e = eById.get(s.entity_id) || {{}};
    lines.push([
      s.entity_id,
      quote(zh ? (e.name_zh || e.name) : e.name),
      quote(e.section || ''),
      quote(zh ? (s.label_zh || s.label) : s.label),
      s.start_year, s.end_year, s.color_hex,
      quote(famName(s.language_family || '')),
    ].join(','));
  }}
  download(new Blob(['\\ufeff' + lines.join('\\r\\n')], {{ type: 'text/csv;charset=utf-8' }}),
           'world-history-timeline.csv');
}}

// ---- controls
const zoomCentre = f => zoomAt(f, scroll.clientWidth / 2, scroll.clientHeight / 2, 1);
document.getElementById('zin').onclick = () => zoomCentre(1.6);
document.getElementById('zout').onclick = () => zoomCentre(1 / 1.6);
document.getElementById('reset').onclick = () => {{
  state.zoomX = 1400 / SPAN; state.rowH = 15; applySizes();
  scroll.scrollTop = 0; scroll.scrollLeft = 0; schedule();
}};
document.getElementById('fit').onclick = () => {{
  state.zoomX = Math.max(state.minZoom, (scroll.clientWidth - 6) / SPAN);
  state.rowH = 15; applySizes(); scroll.scrollLeft = 0; scroll.scrollTop = 0; schedule();
}};
document.getElementById('expng').onclick = exportPNG;
document.getElementById('excsv').onclick = exportCSV;
document.getElementById('lang').onclick = () => {{
  lang = (lang === 'en') ? 'zh' : 'en';
  paintHeader(); paintChips(); buildSearchIndex();
  qEl.placeholder = t('search_ph');
  if (qEl.value) runSearch();
  tip.style.opacity = 0; schedule();
}};

function paintHeader() {{
  document.getElementById('hTitle').textContent = t('title');
  document.getElementById('hSub').textContent =
    t('subtitle_tpl').replace('{{author}}', D.meta.author)
                      .replace('{{n_ent}}', D.entities.length)
                      .replace('{{n_span}}', D.spans.length)
                      .replace('{{y0}}', Math.abs(Y0)).replace('{{y1}}', Y1);
  document.getElementById('foot').textContent = t('hint') + '　·　' + t('foot');
  document.getElementById('reset').textContent = t('reset');
  document.getElementById('fit').textContent = t('fit');
  document.getElementById('expng').textContent = t('export_png');
  document.getElementById('excsv').textContent = t('export_csv');
  document.getElementById('lang').textContent = lang === 'en' ? '中文' : 'EN';
  document.getElementById('zin').title = t('zoom_in');
  document.getElementById('zout').title = t('zoom_out');
  document.title = t('title') + ' — timeline viewer';
}}

function paintChips() {{
  const box = document.getElementById('chips');
  box.innerHTML = '';
  D.families.forEach(f => {{
    const b = document.createElement('span');
    b.className = 'chip' + (famOn.has(f.name) ? '' : ' off');
    b.innerHTML = `<i style="background:${{f.hex}}"></i>${{esc(famName(f.name))}}`;
    b.onclick = () => {{
      if (famOn.has(f.name)) {{
        if (famOn.size > 1) {{ famOn.delete(f.name); b.classList.add('off'); }}
      }} else {{ famOn.add(f.name); b.classList.remove('off'); }}
      tip.style.opacity = 0; schedule();
    }};
    box.appendChild(b);
  }});
}}

window.addEventListener('resize', resize);
buildSearchIndex();
paintHeader();
paintChips();
qEl.placeholder = t('search_ph');
resize();
applySizes();
schedule();
</script>
</body></html>"""


def main():
    meta = load("meta.json")
    ents = load("entities.json")
    spans = load("spans.json")
    legend = load("legend.json")
    zh = i18n.load("zh-CN")
    zui = zh.get("ui") or {}
    zfam = zh.get("families") or {}

    fams, seen = [], set()
    for f in legend["families"]:
        if f["name"] in seen:
            continue
        seen.add(f["name"])
        fams.append({"name": f["name"], "hex": f["subgroups"][0]["languages"][0]["hex"]})

    fam_names = sorted({s["language_family"] for s in spans if s["language_family"]})
    fam_names.append("—")

    ui = {
        "en": {
            "title": meta["title"],
            "subtitle_tpl": "{author} · {n_ent} bands · {n_span} spans · {y0} BCE – {y1} CE",
            "zoom_in": "Zoom in", "zoom_out": "Zoom out", "reset": "Reset", "fit": "Fit",
            "export_png": "PNG", "export_csv": "CSV",
            "hint": "wheel = zoom at cursor · shift+wheel = row height · drag = pan · double-click = zoom in",
            "readout_1px": "1 px ≈ {v} yr", "no_label": "(no printed label)",
            "search_ph": "search a band, dynasty, people…  (Enter = next)",
            "search_hits": "{n} matches · {i}",
            "search_none": "no match",
            "foot": "Chinese is a translation; English is what the poster prints.",
        },
        "zh": {
            "title": zui.get("title", meta["title"]),
            "subtitle_tpl": zui.get("subtitle_tpl", "{author} · {n_ent} 条横带 · {n_span} 个时间段"),
            "zoom_in": "放大", "zoom_out": "缩小",
            "reset": zui.get("reset", "重置"),
            "fit": zui.get("fit", "全览"),
            "export_png": "导出图片", "export_csv": "导出 CSV",
            "hint": "滚轮=按鼠标位置缩放 · Shift+滚轮=行高 · 拖拽=平移 · 双击=放大",
            "readout_1px": "1 px ≈ {v} 年",
            "no_label": zui.get("no_label", "（无印刷标签）"),
            "search_ph": "搜索横带、朝代、族群…（回车跳到下一处）",
            "search_hits": "共 {n} 条匹配 · 第 {i} 条",
            "search_none": "没有匹配",
            "foot": "中文为译写，英文才是原图原文。",
        },
    }

    payload = json.dumps({
        "meta": meta,
        "entities": [{k: e.get(k) for k in ("id", "name", "name_zh", "language_family", "section")}
                     for e in ents],
        "spans": [{k: s.get(k) for k in ("entity_id", "start_year", "end_year", "color_hex",
                                         "label", "label_zh", "language_family")}
                  for s in spans],
        "families": fams,
        "families_zh": {k: v for k, v in zfam.items()},
        "familiesOn": fam_names,
        "ui": ui,
    }, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")

    html = HTML.format(title=meta["title"], payload=payload)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    print("wrote", OUT, len(html), "bytes")


if __name__ == "__main__":
    main()
