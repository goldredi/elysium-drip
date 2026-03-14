'use strict';

// ============================================================
// EMOJIREAN APP — UI controller, auth, API communication
// ============================================================

const EM = (() => {
const E = EmojireanEngine;

// -- STATE --
let authToken = localStorage.getItem('em_token') || null;
let currentUser = null;
let langs = [];
let activeLang = null;
let langMode = 'ru';
let curShape = 'grid';
let lastEncoded = [];
let lastShape = 'grid';
let botTimer = null;
let encMade = parseInt(localStorage.getItem('em_e') || '0');

// -- API --
async function api(path, method = 'GET', body = null) {
  const opts = { method, headers: {} };
  if (authToken) opts.headers['Authorization'] = 'Bearer ' + authToken;
  if (body) { opts.headers['Content-Type'] = 'application/json'; opts.body = JSON.stringify(body); }
  const res = await fetch('/api' + path, opts);
  if (!res.ok) {
    if (res.status === 401) { logout(); throw new Error('session expired'); }
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'request failed');
  }
  return res.json();
}

function logout() {
  authToken = null;
  currentUser = null;
  localStorage.removeItem('em_token');
  document.getElementById('authPage').style.display = '';
  document.getElementById('authPage').classList.remove('out');
  document.getElementById('mainApp').style.display = 'none';
}

// -- AUTH --
async function doAuth(username, password, code) {
  const errEl = document.getElementById('authErr');
  try {
    const tgData = window.Telegram?.WebApp?.initDataUnsafe;
    const body = {
      username,
      password,
      telegram_id: tgData?.user?.id || null,
      telegram_username: tgData?.user?.username || null,
    };
    if (code) body.code = code;
    const data = await api('/auth', 'POST', body);
    authToken = data.token;
    currentUser = data;
    localStorage.setItem('em_token', authToken);
    localStorage.setItem('em_username', username);
    errEl.textContent = '// identity confirmed';
    errEl.className = 'auth-err ok';
    setTimeout(enterMain, 700);
  } catch (e) {
    errEl.textContent = '// identity rejected';
    errEl.className = 'auth-err bad';
    document.getElementById('authInput').value = '';
  }
}

async function checkSession() {
  if (!authToken) return false;
  try {
    currentUser = await api('/me');
    return true;
  } catch {
    authToken = null;
    localStorage.removeItem('em_token');
    return false;
  }
}

function enterMain() {
  const auth = document.getElementById('authPage');
  auth.classList.add('out');
  setTimeout(() => {
    auth.style.display = 'none';
    document.getElementById('mainApp').style.display = 'block';
    if (currentUser) {
      const displayName = localStorage.getItem('em_username') || currentUser.username || 'anon';
      document.getElementById('hdrUser').textContent = '// ' + displayName;
      // Hide create panel if user can't create languages
      if (!currentUser.can_create_languages && !currentUser.is_admin) {
        const cp = document.getElementById('createLangPanel');
        if (cp) cp.style.display = 'none';
      }
    }
    loadLangs();
  }, 600);
}

// -- LANGUAGE MANAGEMENT --
function saveLocal() {
  try {
    localStorage.setItem('em_langs3', JSON.stringify(langs));
    localStorage.setItem('em_aid3', activeLang ? activeLang.id : '');
  } catch (e) {}
}

function loadLocal() {
  try {
    const s = localStorage.getItem('em_langs3');
    if (s) {
      const raw = JSON.parse(s);
      langs = raw.map(l => {
        if (l.i && !l.id) { const exp = E.decodeToken(l._b64 || ''); return exp || l; }
        if (!l.letters && l.mapping) { l.letters = l.mapping; l.bigrams = l.bigrams || {}; }
        return l;
      }).filter(Boolean);
    }
    const aid = localStorage.getItem('em_aid3');
    activeLang = langs.find(l => l.id === aid) || langs[0] || null;
  } catch (e) {}
}

async function loadLangs() {
  // Load from localStorage first for instant display
  loadLocal();
  renderLangList();
  updateActiveUI();
  // Then sync from server
  try {
    const serverLangs = await api('/languages');
    for (const sl of serverLangs) {
      const existing = langs.find(l => l.lang_id === sl.lang_id || l.id === sl.lang_id);
      if (!existing && sl.token_b64) {
        const decoded = E.decodeToken(sl.token_b64);
        if (decoded) langs.push(decoded);
      }
    }
    saveLocal();
    renderLangList();
    updateActiveUI();
  } catch (e) { /* offline mode - use localStorage */ }
}

async function saveLangToServer(lang) {
  try {
    await api('/languages', 'POST', {
      lang_id: lang.id,
      name: lang.name,
      token_data: { mode: lang.mode, type: lang.type, decoStyle: lang.decoStyle },
      token_b64: lang._b64,
      mode: lang.mode || 'ru',
    });
  } catch (e) { /* offline — will sync later */ }
}

// -- TOKEN GENERATION --
function genToken() {
  const name = (document.getElementById('langName').value.trim() || 'UNNAMED').toUpperCase();
  const ttlSel = document.getElementById('ttlSel').value;
  const obj = E.generateToken(name, langMode);

  if (ttlSel === 'date') obj.ttl = new Date(Date.now() + 30*24*3600000).toISOString();
  else if (ttlSel !== 'never') obj.ttl = parseInt(ttlSel);
  obj._b64 = E.encodeToken(obj);

  langs.push(obj);
  activeLang = obj;
  saveLocal();
  saveLangToServer(obj);
  renderLangList();
  updateActiveUI();
  document.getElementById('langName').value = '';
  document.getElementById('sbLangs').textContent = langs.length;
  const ds = ['WING','BOX','MATH','RUNE','BRAILLE'][obj.decoStyle];
  toast('// "' + name + '" | ' + Object.keys(obj.letters).length + ' chars | deco: ' + ds);
  showDecoPreview(obj.decoStyle);
}

function genReaderToken() {
  if (!activeLang || activeLang.type === 'reader') { toast('// need master language'); return; }
  const rObj = E.generateReaderToken(activeLang);
  if (!rObj) return;
  fbCopy(rObj._b64, () => toast('// reader token copied'));
}

function importToken() {
  const raw = document.getElementById('importTok').value.trim();
  if (!raw) { toast('// paste token first'); return; }
  try {
    let obj = E.decodeToken(raw);
    if (!obj) throw new Error('bad token');
    if (!obj.letters && !obj.rev_mapping) throw new Error('invalid');
    if (!obj.id) obj.id = 'lang_' + Date.now();
    obj._b64 = raw;
    if (obj.ttl && typeof obj.ttl === 'string' && new Date(obj.ttl) < new Date()) { toast('// token expired'); return; }
    const ex = langs.findIndex(l => l._b64 === raw || l.id === obj.id);
    if (ex >= 0) activeLang = langs[ex];
    else { langs.push(obj); activeLang = obj; }
    saveLocal();
    saveLangToServer(obj);
    renderLangList();
    updateActiveUI();
    document.getElementById('importTok').value = '';
    toast('// imported: ' + obj.name + ' [' + (obj.type || 'master') + ']');
  } catch (e) { toast('// invalid token'); }
}

function selectLang(id) {
  const l = langs.find(x => x.id === id);
  if (!l) return;
  activeLang = l;
  saveLocal();
  renderLangList();
  updateActiveUI();
  if (l.decoStyle !== undefined) showDecoPreview(l.decoStyle);
  toast('// active: ' + l.name.toLowerCase());
}

function deleteLang(id) {
  if (!confirm('delete language?')) return;
  langs = langs.filter(l => l.id !== id);
  if (activeLang?.id === id) activeLang = langs[0] || null;
  saveLocal();
  renderLangList();
  updateActiveUI();
  document.getElementById('sbLangs').textContent = langs.length;
  // Server delete
  api('/languages/' + id, 'DELETE').catch(() => {});
  toast('// deleted');
}

function renderLangList() {
  const box = document.getElementById('langList');
  if (!langs.length) { box.innerHTML = '<div style="font-size:11px;color:#333;padding:6px">// empty</div>'; return; }
  box.innerHTML = langs.map(l => {
    const on = activeLang?.id === l.id;
    const isR = l.type === 'reader';
    const cntL = Object.keys(l.letters || l.rev_mapping || {}).length;
    const cntB = Object.keys(l.bigrams || {}).length;
    const dNames = ['WING','BOX','MATH','RUNE','BRAIL'];
    const dLabel = l.decoStyle !== undefined ? dNames[l.decoStyle] || '' : '';
    return `<div class="li${on ? ' on' : ''}" onclick="EM.selectLang('${l.id}')">
      <div style="flex:1">
        <div class="li-name">${on ? '> ' : '  '}${l.name.toLowerCase()}</div>
        <div class="li-info" style="display:flex;gap:4px;align-items:center;margin-top:1px;flex-wrap:wrap">
          ${isR ? '<span class="reader-tag">READ</span>' : ''}
          <span>${cntL}c ${cntB ? '|' + cntB + 'bi' : ''} ${dLabel ? '|' + dLabel : ''}</span>
        </div>
      </div>
      <button class="li-del" onclick="event.stopPropagation();EM.deleteLang('${l.id}')">x</button>
    </div>`;
  }).join('');
}

function updateActiveUI() {
  updPanelTitles();
  if (!activeLang) {
    document.getElementById('tokenDisplay').textContent = '// no active language';
    document.getElementById('tokenName').textContent = '------------';
    document.getElementById('tokenName').style.opacity = '.3';
    ['sL','sH','sE','sD'].forEach(i => { const el = document.getElementById(i); if (el) el.textContent = '--'; });
    const ab = document.getElementById('alphaBox');
    if (ab) ab.innerHTML = '<div style="font-size:11px;color:#222;text-align:center;padding:20px">// select a language first</div>';
    return;
  }
  const isR = activeLang.type === 'reader';
  document.getElementById('tokenDisplay').textContent = (activeLang._b64 || '').substring(0, 30) + '...';
  document.getElementById('tokenName').textContent = activeLang.name.toLowerCase();
  document.getElementById('tokenName').style.opacity = '1';
  const chars = Object.keys(activeLang.letters || activeLang.rev_mapping || {});
  const bigs = Object.keys(activeLang.bigrams || {}).length;
  const total = isR ? chars.length : Object.values(activeLang.letters || {}).reduce((a, v) => a + v.length, 0);
  document.getElementById('sL').textContent = chars.length + (bigs ? '+' + bigs : '');
  document.getElementById('sH').textContent = isR ? 'READ' : total;
  document.getElementById('sE').textContent = isR ? 'ONLY' : Math.round(Math.log2(Math.max(total, 1)) * 10) / 10 + 'b';
  document.getElementById('sD').textContent = activeLang.created ? new Date(activeLang.created).toLocaleDateString('en') : '--';
  renderAlpha();
  if (activeLang.decoStyle !== undefined) showDecoPreview(activeLang.decoStyle);
}

function renderAlpha() {
  if (!activeLang) return;
  const ab = document.getElementById('alphaBox'); if (!ab) return;
  if (activeLang.type === 'reader') { ab.innerHTML = '<div style="font-size:11px;color:#2a3a2a;padding:8px">// reader token | alphabet hidden</div>'; return; }
  const m = activeLang.letters || {};
  let html = '';
  const sec = (title, col, chs) => {
    const f = chs.filter(c => m[c]); if (!f.length) return;
    html += `<div style="font-size:9px;color:${col};margin:6px 0 3px;letter-spacing:2px">${title}</div><div class="alpha-wrap" style="margin-bottom:6px">`;
    for (const ch of f) {
      const es = m[ch] || [];
      html += `<div class="alpha-cell"><span class="alpha-l">${ch}</span>${es.map((e, i) => `<span class="${i === 0 ? 'alpha-e' : 'alpha-x'}">${e}</span>`).join('')}</div>`;
    }
    html += '</div>';
  };
  sec('// RU', 'rgba(57,255,20,.5)', E.RU_CHARS);
  sec('// EN', 'rgba(255,176,0,.45)', E.EN_CHARS);
  sec('// 0-9', 'rgba(0,229,255,.4)', E.DIGITS);
  const bg = activeLang.bigrams || {};
  if (Object.keys(bg).length) {
    html += `<div style="font-size:9px;color:rgba(255,34,68,.4);margin:6px 0 3px;letter-spacing:2px">// BIGRAMS</div><div class="alpha-wrap" style="margin-bottom:6px">`;
    for (const [pair, hs] of Object.entries(bg))
      html += `<div class="alpha-cell"><span class="alpha-l" style="font-size:10px;min-width:22px">${pair}</span>${hs.map((e, i) => `<span class="${i === 0 ? 'alpha-e' : 'alpha-x'}">${e}</span>`).join('')}</div>`;
    html += '</div>';
  }
  ab.innerHTML = html;
}

function showDecoPreview(styleIdx) {
  const dp = document.getElementById('decoPreview'); if (!dp) return;
  const s = E.DECO_SETS[styleIdx % E.DECO_SETS.length];
  dp.textContent = s.slice(0, 12).join(' ');
}

function copyToken() {
  if (!activeLang) { toast('// no active language'); return; }
  const txt = activeLang._b64 || '';
  fbCopy(txt, () => toast('// token copied (' + txt.length + ' chars)'));
}

// -- ENCODE --
function doEncode() {
  if (!activeLang) { toast('// no language'); return; }
  if (activeLang.type === 'reader') { toast('// reader token -- cannot encode'); return; }
  const text = document.getElementById('encIn').value;
  if (!text.trim()) { toast('// empty input'); return; }
  const nullDensity = parseFloat(document.getElementById('nullDensity').value) / 100;
  const useAnchor = document.getElementById('useAnchor').checked;
  const artMode = document.getElementById('artMode').checked;
  let encoded = E.encodeStr(text, activeLang);
  if (nullDensity > 0 && activeLang.nullEmojis?.length) encoded = E.addNulls(encoded, activeLang.nullEmojis, nullDensity);
  let sh = curShape;
  if (useAnchor && activeLang.nullEmojis?.length >= 5) encoded = E.addAnchor(encoded, sh, activeLang.nullEmojis);
  if (artMode) encoded = E.artModeWrap(encoded);
  lastEncoded = encoded; lastShape = sh;
  encMade++; localStorage.setItem('em_e', encMade);
  document.getElementById('sbEnc').textContent = String(encMade).padStart(6, '0');
  renderShapeDOM(encoded, sh, 'encOut', activeLang.decoStyle || 0);
  toast('// encoded: ' + encoded.length + ' symbols | ' + sh);
  // Log to server
  api('/encode-log', 'POST', {
    language_id: activeLang.id,
    char_count: text.length,
    emoji_count: encoded.length,
    source: 'web',
  }).catch(() => {});
}

function renderShapeDOM(emojis, shape, boxId, decoStyle) {
  const box = document.getElementById(boxId); box.innerHTML = '';
  if (!emojis?.length) { box.innerHTML = '<div class="ph-txt">// waiting...</div>'; return; }
  const isArtShape = (shape === 'rnd');
  const rows = isArtShape ? E.buildArtRows(emojis, E.lastArtKey || E.ART_KEYS[0]) : E.buildRows(emojis, shape);
  const maxW = Math.max(...rows.map(r => r.length));
  const PAD_EMOJI = E.FRAME_EMOJIS[(decoStyle || 0) % E.FRAME_EMOJIS.length];
  const wrap = document.createElement('div');
  wrap.style.cssText = 'display:flex;flex-direction:column;align-items:center;gap:0;padding:4px;width:100%';
  for (const row of rows) {
    const r = document.createElement('div'); r.className = 'sh-row';
    const padL = isArtShape ? 0 : Math.floor((maxW - row.length) / 2);
    const padR = isArtShape ? 0 : maxW - row.length - padL;
    for (let p = 0; p < padL; p++) { const pd = document.createElement('span'); pd.className = 'sh-pad'; pd.textContent = PAD_EMOJI; r.appendChild(pd); }
    for (const e of row) {
      const c = document.createElement('span');
      if (isArtShape && E.FRAME_EMOJIS.includes(e)) {
        c.className = 'sh-pad';
        c.style.cssText = 'display:inline-flex;width:28px;height:28px;align-items:center;justify-content:center;font-size:18px;opacity:.15;user-select:none';
      } else c.className = 'sh-cell';
      c.textContent = e; r.appendChild(c);
    }
    for (let p = 0; p < padR; p++) { const pd = document.createElement('span'); pd.className = 'sh-pad'; pd.textContent = PAD_EMOJI; r.appendChild(pd); }
    wrap.appendChild(r);
  }
  const lbl = document.createElement('div'); lbl.className = 'sh-label';
  lbl.textContent = '// ' + (shape === 'rnd' ? 'art' : shape) + ' | ' + emojis.length + ' symbols';
  wrap.appendChild(lbl); box.appendChild(wrap);
}

function copyEncoded(mode) {
  if (!lastEncoded.length) { toast('// encode something first'); return; }
  const rows = E.buildRows(lastEncoded, lastShape);
  const ds = activeLang?.decoStyle || 0;
  let text;
  if (mode === 'flat') text = E.rowsToFlat(rows);
  else if (mode === 'shaped') text = E.rowsToShaped(rows, ds);
  else text = E.rowsToArtistic(rows, ds, activeLang?.spaceSep);
  const ok = () => {
    document.querySelectorAll('.copy-mode-btn').forEach(b => {
      if (b.dataset.mode === mode) { b.classList.add('flash'); setTimeout(() => b.classList.remove('flash'), 400); }
    });
    toast('// copied | ' + mode);
  };
  if (navigator.clipboard?.writeText) navigator.clipboard.writeText(text).then(ok).catch(() => fbCopy(text, ok));
  else fbCopy(text, ok);
}

// -- DECODE --
function doDecode() {
  if (!activeLang) { toast('// no language'); return; }
  const raw = document.getElementById('decIn').value.trim();
  if (!raw) { toast('// paste message'); return; }
  const result = E.decode(raw, activeLang);
  // TTL
  if (activeLang.ttl && typeof activeLang.ttl === 'number') {
    activeLang.ttl--;
    if (activeLang.ttl <= 0) {
      langs = langs.filter(l => l.id !== activeLang.id); activeLang = langs[0] || null;
      saveLocal(); renderLangList(); updateActiveUI(); toast('// token used up');
    } else saveLocal();
  }
  const out = document.getElementById('decOut');
  if (!result.decoded) { out.innerHTML = '<span style="color:var(--red)">// decode failed</span>'; document.getElementById('decMeta').textContent = ''; return; }
  out.textContent = result.decoded;
  document.getElementById('decMeta').textContent = `// ${result.found} decoded | ${result.miss} unknown${result.anchorShape ? ' | anchor=' + result.anchorShape : ''}`;
}

// -- BOT SIM --
function simType() {
  clearTimeout(botTimer);
  const text = document.getElementById('botIn').value.trim();
  const opts = document.getElementById('botOpts');
  if (!text) { opts.innerHTML = '<div style="font-size:11px;color:#1a2a1a;text-align:center;padding:8px">// start typing...</div>'; return; }
  opts.innerHTML = '<div style="font-size:11px;color:#334;text-align:center;padding:4px"><span class="blink">*</span> encoding...</div>';
  botTimer = setTimeout(() => buildBotOpts(text), 350);
}

function buildBotOpts(text) {
  const ML = langs.filter(l => l.type !== 'reader');
  if (!ML.length) { document.getElementById('botOpts').innerHTML = '<div style="font-size:11px;color:#334;text-align:center;padding:8px">// create language first</div>'; return; }
  const shapes = ['grid','triangle','diamond','cross','frame','rnd'];
  const opts = ML.slice(0, 3).map(l => {
    const sh = shapes[~~(Math.random() * shapes.length)];
    let enc = E.encodeStr(text, l);
    enc = E.addNulls(enc, l.nullEmojis || [], 0.05);
    const rows = E.buildRows(enc, sh);
    const preview = E.rowsToArtistic(rows, l.decoStyle || 0, l.spaceSep);
    return { enc, shape: sh, label: l.name.toLowerCase() + ' | ' + sh, lang: l, preview, rows };
  });
  opts.push({ enc: null, label: 'plain text', plain: text, preview: text.substring(0, 40) + '...' });
  document.getElementById('botOpts')._data = opts;
  document.getElementById('botOpts').innerHTML = opts.map((opt, i) => {
    const lines = opt.preview.split('\n').slice(0, 3).join('\n');
    return `<div class="tg-opt" onclick="EM.chooseOpt(${i})"><span class="tg-opt-pre">${lines}</span><span class="tg-opt-tag">${opt.label}</span></div>`;
  }).join('');
}

function chooseOpt(i) {
  const d = document.getElementById('botOpts')._data; if (!d) return;
  document.querySelectorAll('.tg-opt').forEach((el, j) => el.classList.toggle('picked', j === i));
  setTimeout(() => addBotMsg(d[i]), 280);
}

function simSend() {
  const text = document.getElementById('botIn').value.trim(); if (!text) return;
  const shapes = ['grid','triangle','diamond','cross','frame'];
  const sh = shapes[~~(Math.random() * shapes.length)];
  const l = activeLang && activeLang.type !== 'reader' ? activeLang : langs.find(x => x.type !== 'reader');
  const enc = l ? E.encodeStr(text, l) : null;
  const rows = enc ? E.buildRows(enc, sh) : null;
  const preview = rows ? E.rowsToArtistic(rows, l?.decoStyle || 0, l?.spaceSep) : null;
  addBotMsg({ enc, shape: sh, label: l ? l.name.toLowerCase() + ' | ' + sh : 'plain', plain: text, lang: l, preview });
  document.getElementById('botIn').value = '';
  document.getElementById('botOpts').innerHTML = '<div style="font-size:11px;color:#1a2a1a;text-align:center;padding:8px">// start typing...</div>';
}

function addBotMsg(opt) {
  const chat = document.getElementById('chatBox');
  const time = new Date().toLocaleTimeString('en', { hour: '2-digit', minute: '2-digit', hour12: false });
  const oW = document.createElement('div'); oW.className = 'mw-o';
  const bub = document.createElement('div'); bub.className = 'bubble b-o';
  if (opt.enc?.length) {
    const pre = document.createElement('pre'); pre.className = 'msg-pre'; pre.textContent = opt.preview || '';
    bub.appendChild(pre);
    const lbl = document.createElement('div'); lbl.className = 'b-lang'; lbl.textContent = '// ' + opt.label;
    bub.appendChild(lbl);
  } else bub.textContent = opt.plain || opt.label || '';
  const uName = localStorage.getItem('em_username') || 'anon';
  const t = document.createElement('div'); t.className = 'b-t'; t.textContent = uName + ' | ' + time;
  oW.appendChild(bub); oW.appendChild(t); chat.appendChild(oW);
  if (opt.enc?.length) {
    setTimeout(() => {
      const iW = document.createElement('div'); iW.className = 'mw-i';
      const ib = document.createElement('div'); ib.className = 'bubble b-i';
      ib.textContent = 'token required | lang: ' + (opt.lang?.name?.toLowerCase() || '?');
      const it = document.createElement('div'); it.className = 'b-t b-t-i'; it.textContent = 'bot|' + time;
      iW.appendChild(ib); iW.appendChild(it); chat.appendChild(iW); chat.scrollTop = chat.scrollHeight;
    }, 600);
  }
  chat.scrollTop = chat.scrollHeight;
}

function toBot() {
  if (!lastEncoded.length) { toast('// encode first'); return; }
  document.getElementById('botIn').value = document.getElementById('encIn').value;
  swTab('Bot'); simType();
}

// -- TABS --
const TABS = ['Languages','Encode','Decode','Bot','Alpha'];
function swTab(name) {
  TABS.forEach(t => { const el = document.getElementById('tab' + t); if (el) el.style.display = t === name ? '' : 'none'; });
  document.querySelectorAll('.nd[data-tab]').forEach(b => b.classList.toggle('on', b.dataset.tab === name));
  updPanelTitles();
}

function updPanelTitles() {
  const n = activeLang ? activeLang.name.toLowerCase() : 'no_language';
  const ep = document.getElementById('encPT'); if (ep) ep.childNodes[0].textContent = 'encode() // ' + n + ' ';
  const dp = document.getElementById('decPT'); if (dp) dp.childNodes[0].textContent = 'decode() // ' + n + ' ';
  const h = document.getElementById('hdrLang'); if (h) h.textContent = activeLang ? '// active: ' + n : '// no language';
  const sb = document.getElementById('sbLangs'); if (sb) sb.textContent = langs.length;
}

function setMode(m) {
  langMode = m;
  ['RU','EN','BOTH'].forEach(x => document.getElementById('m' + x).classList.toggle('on', x.toLowerCase() === m));
}

function selSh(el, sh) {
  document.querySelectorAll('[data-sh]').forEach(b => b.classList.remove('on'));
  el.classList.add('on'); curShape = sh;
}

// -- CLOCK --
function updClock() {
  const n = new Date(), p = x => String(x).padStart(2, '0');
  document.getElementById('pxClock').textContent = p(n.getHours()) + ':' + p(n.getMinutes()) + ':' + p(n.getSeconds());
  document.getElementById('ndTime').textContent = p(n.getHours()) + ':' + p(n.getMinutes());
  const D = ['SUN','MON','TUE','WED','THU','FRI','SAT'];
  const M = ['JAN','FEB','MAR','APR','MAY','JUN','JUL','AUG','SEP','OCT','NOV','DEC'];
  document.getElementById('pxDate').textContent = D[n.getDay()] + ' ' + p(n.getDate()) + ' ' + M[n.getMonth()];
}
updClock(); setInterval(updClock, 1000);

// -- VISITORS --
let visits = parseInt(localStorage.getItem('em_v') || '0') + 1;
localStorage.setItem('em_v', visits);
function renderHitCounter(n) {
  const s = String(n).padStart(6, '0');
  document.getElementById('vcnt').innerHTML = s.split('').map(d => `<span class="hit-digit">${d}</span>`).join('');
}
renderHitCounter(visits);
document.getElementById('sbEnc').textContent = String(encMade).padStart(6, '0');

// -- MUSIC --
let audioCtx = null, musicGain = null, musicPlaying = false, npIdx = 0, npPos = 0, npInterval = null;
const TRACKS = [
  { t: 'NULL_SIGNAL.flac', a: '#nyashnydvizh' },
  { t: 'LAYER_07.exe', a: 'DRIPTECH_OST' },
  { t: 'ENCRYPT_ME', a: 'CYBER_PROPHET' },
  { t: 'GHOST_PROTOCOL', a: '#nyashnydvizh' },
];

function initAudio() {
  audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  musicGain = audioCtx.createGain(); musicGain.gain.setValueAtTime(0, audioCtx.currentTime);
  musicGain.connect(audioCtx.destination);
  const freqs = [55, 82.41, 110, 164.81, 220, 55 * 3];
  const vols = [.3, .18, .1, .05, .03, .08];
  for (let i = 0; i < freqs.length; i++) {
    const o = audioCtx.createOscillator(); o.type = i < 3 ? 'sine' : 'triangle';
    o.frequency.setValueAtTime(freqs[i], audioCtx.currentTime);
    const g = audioCtx.createGain(); g.gain.setValueAtTime(vols[i], audioCtx.currentTime);
    if (i >= 2) { const lfo = audioCtx.createOscillator(); lfo.frequency.setValueAtTime(.05 + i * .02, audioCtx.currentTime); const lg = audioCtx.createGain(); lg.gain.setValueAtTime(freqs[i] * .003, audioCtx.currentTime); lfo.connect(lg); lg.connect(o.frequency); lfo.start(); }
    o.connect(g); g.connect(musicGain); o.start();
  }
}

function toggleMusic() {
  if (!audioCtx) initAudio();
  if (audioCtx.state === 'suspended') audioCtx.resume();
  musicPlaying = !musicPlaying;
  const now = audioCtx.currentTime;
  if (musicPlaying) {
    musicGain.gain.linearRampToValueAtTime(.22, now + 3);
    if (!npInterval) npInterval = setInterval(() => {
      npPos += .2; if (npPos > 100) { npPos = 0; npIdx = (npIdx + 1) % TRACKS.length; updTrack(); }
      document.getElementById('npFill').style.width = npPos + '%';
      const s = ~~(npPos * 2.4);
      document.getElementById('npTime').textContent = ~~(s / 60) + ':' + (s % 60).toString().padStart(2, '0');
    }, 100);
  } else {
    musicGain.gain.linearRampToValueAtTime(0, now + 1.5);
    clearInterval(npInterval); npInterval = null;
  }
  document.getElementById('musicBtn').className = 'music-btn' + (musicPlaying ? ' on' : '');
  document.getElementById('musicBtn').textContent = musicPlaying ? 'stop music' : 'play music';
  animViz();
}

function animViz() {
  if (!musicPlaying) { document.querySelectorAll('.mv-bar').forEach(b => b.style.height = '2px'); return; }
  document.querySelectorAll('.mv-bar').forEach(b => b.style.height = (2 + Math.random() * 12) + 'px');
  setTimeout(animViz, 80);
}

function updTrack() { const t = TRACKS[npIdx]; document.getElementById('npTrack').textContent = t.t; document.getElementById('npArtist').textContent = t.a; }
function prevTrack() { npIdx = (npIdx - 1 + TRACKS.length) % TRACKS.length; npPos = 0; updTrack(); }
function nextTrack() { npIdx = (npIdx + 1) % TRACKS.length; npPos = 0; updTrack(); }
updTrack();

// -- MOOD --
(function () { try { const m = localStorage.getItem('em_mood'); if (m) document.getElementById('moLbl').textContent = m; } catch (e) {} })();
function setMood(el, lbl) {
  document.querySelectorAll('.mo').forEach(m => m.classList.remove('on'));
  el.classList.add('on'); document.getElementById('moLbl').textContent = lbl;
  try { localStorage.setItem('em_mood', lbl); } catch (e) {}
}

// -- PET --
const PET_STATES = ['\u{1F63A}','\u{1F638}','\u{1F63B}','\u{1F640}','\u{1F63F}','\u{1F63E}','\u{1F431}','\u{1F63D}'];
let petHunger = 80, petClicks = 0;
function petClick() {
  petClicks++; petHunger = Math.min(100, petHunger + 5);
  const moods = ['nyaa~','purrrr','*bites*','zzz...','hungry!','love u','hiss!','*kneads*'];
  document.getElementById('petMood').textContent = moods[~~(Math.random() * moods.length)];
  document.getElementById('petSprite').textContent = PET_STATES[~~(Math.random() * PET_STATES.length)];
  if (petClicks % 7 === 0) showEgg('pet');
}
function feedPet() { petHunger = Math.min(100, petHunger + 30); document.getElementById('petSprite').textContent = '\u{1F63B}'; document.getElementById('petMood').textContent = 'om nom nom'; toast('// fed'); }

// -- QUOTES --
const QS = [
  'token is the key, word is the door',
  'no matter where you go, everyone is connected',
  'those who dont know the alphabet see only art',
  'cipher is a bridge between worlds',
  'only the initiated read the messages',
  'i am connected to everyone on the wired',
  'a language known by two is no longer secret',
  'present day present time',
  'the wired is more real than the real world',
  'every emoji is a letter for those who know',
  'one token one world',
];
let qIdx = ~~(Math.random() * QS.length);
function nextQ() { qIdx = (qIdx + 1) % QS.length; document.getElementById('qb').textContent = QS[qIdx]; }
document.getElementById('qb').textContent = QS[qIdx];

// -- GUESTBOOK --
let GB = JSON.parse(localStorage.getItem('em_gb') || '[{"n":"lain","m":"lets all love lain"},{"n":"nyash","m":"#nyashnydvizh"}]');
function renderGB() {
  const b = document.getElementById('gbList');
  b.innerHTML = GB.slice(-8).map(e => `<div class="gb-e"><span class="gb-n">${e.n}:</span> ${e.m}</div>`).join('');
  b.scrollTop = b.scrollHeight;
}
function addGb() {
  const n = document.getElementById('gbN').value.trim() || 'anon';
  const m = document.getElementById('gbM').value.trim(); if (!m) return;
  GB.push({ n: n.slice(0, 12), m: m.slice(0, 40) });
  try { localStorage.setItem('em_gb', JSON.stringify(GB.slice(-20))); } catch (e) {}
  renderGB(); document.getElementById('gbN').value = ''; document.getElementById('gbM').value = '';
}
renderGB();

// -- EGGS --
const EGGS = {
  konami: { t: 'CHEAT_CODE.exe', b: 'up up down down left right left right B A<br><br>you found a code that existed before you.' },
  lain: { t: 'L A I N', b: 'no matter where you go,<br>everyone is connected.' },
  drip: { t: '#nyashnydvizh', b: '// ACCESS GRANTED<br><br>token is the key, word is the door' },
  pet: { t: 'NYAA', b: 'you found the cat.<br><br>the cat stares into you.<br>you stare into the cat.<br><br>~ meow ~' },
};
let kseq = [];
const KK = ['ArrowUp','ArrowUp','ArrowDown','ArrowDown','ArrowLeft','ArrowRight','ArrowLeft','ArrowRight','b','a'];
document.addEventListener('keydown', e => {
  kseq.push(e.key); kseq = kseq.slice(-10);
  if (kseq.join(',') === KK.join(',')) showEgg('konami');
  const last4 = kseq.slice(-4).join('').toLowerCase();
  if (last4 === 'lain') showEgg('lain');
  if (last4 === 'drip') showEgg('drip');
});
function showEgg(type) {
  const eg = EGGS[type] || EGGS.konami;
  document.getElementById('eggT').textContent = eg.t;
  document.getElementById('eggB').innerHTML = eg.b;
  document.getElementById('eggModal').classList.add('show');
}
function closeEgg() { document.getElementById('eggModal').classList.remove('show'); }

// -- TOAST --
const toastEl = document.getElementById('toast');
function toast(msg) { toastEl.textContent = msg; toastEl.classList.add('show'); clearTimeout(toastEl._t); toastEl._t = setTimeout(() => toastEl.classList.remove('show'), 3200); }

// -- COPY FALLBACK --
function fbCopy(txt, cb) {
  if (navigator.clipboard?.writeText) { navigator.clipboard.writeText(txt).then(cb).catch(() => _fbCopy(txt, cb)); return; }
  _fbCopy(txt, cb);
}
function _fbCopy(txt, cb) {
  const ta = document.createElement('textarea'); ta.value = txt;
  ta.style.cssText = 'position:fixed;top:-9999px;left:-9999px;opacity:0';
  document.body.appendChild(ta); ta.select(); ta.setSelectionRange(0, 99999);
  try { document.execCommand('copy'); if (cb) cb(); } catch (e) { toast('// copy manually'); }
  document.body.removeChild(ta);
}

// -- INIT --
// Auth input — login → password → code (optional) → submit
document.getElementById('authName').addEventListener('keydown', e => {
  if (e.key !== 'Enter') return;
  e.preventDefault();
  if (document.getElementById('authName').value.trim() === '12071998') { window.location.href = '/admin'; return; }
  document.getElementById('authInput').focus();
});
document.getElementById('authInput').addEventListener('keydown', e => {
  if (e.key !== 'Enter') return;
  e.preventDefault();
  document.getElementById('authCode').focus();
});
document.getElementById('authCode').addEventListener('keydown', e => {
  if (e.key !== 'Enter') return;
  const name = document.getElementById('authName').value.trim();
  const pass = document.getElementById('authInput').value.trim();
  const code = document.getElementById('authCode').value.trim();
  if (!name) { document.getElementById('authErr').textContent = '// vvedi login'; document.getElementById('authErr').className = 'auth-err bad'; document.getElementById('authName').focus(); return; }
  if (name === '12071998') { window.location.href = '/admin'; return; }
  if (!pass) { document.getElementById('authErr').textContent = '// vvedi parol\''; document.getElementById('authErr').className = 'auth-err bad'; document.getElementById('authInput').focus(); return; }
  doAuth(name, pass, code || null);
});

// Null density slider
const ndEl = document.getElementById('nullDensity');
if (ndEl) ndEl.addEventListener('input', function () { document.getElementById('nullDensityVal').textContent = this.value + '%'; });

// Encode/decode keyboard shortcuts
document.getElementById('encIn').addEventListener('keydown', e => { if (e.ctrlKey && e.key === 'Enter') { e.preventDefault(); doEncode(); } });
document.getElementById('decIn').addEventListener('keydown', e => { if (e.ctrlKey && e.key === 'Enter') { e.preventDefault(); doDecode(); } });

// Tab clicks
document.querySelectorAll('.nd[data-tab]').forEach(btn => {
  btn.addEventListener('click', () => swTab(btn.dataset.tab));
});

// Init tabs
TABS.forEach((t, i) => { const el = document.getElementById('tab' + t); if (el) el.style.display = i === 0 ? '' : 'none'; });
setMode('ru');

// Starfield canvas
const spC = document.getElementById('authCanvas');
if (spC) {
  const spCtx = spC.getContext('2d'); let spStars = [];
  function initSpC() {
    spC.width = window.innerWidth; spC.height = window.innerHeight;
    spStars = Array.from({ length: 80 }, () => ({
      x: Math.random() * spC.width, y: Math.random() * spC.height,
      r: Math.random() * .7 + .2, op: Math.random(), s: Math.random() * .012 + .003,
      col: ['#39ff14','#ffffff','#1a2a1a'][~~(Math.random() * 3)]
    }));
  }
  function animSpC() {
    if (document.getElementById('authPage').style.display === 'none') return;
    spCtx.clearRect(0, 0, spC.width, spC.height);
    for (const s of spStars) {
      s.op += s.s; if (s.op > 1 || s.op < 0) s.s = -s.s;
      spCtx.save(); spCtx.globalAlpha = Math.abs(s.op) * .5; spCtx.fillStyle = s.col;
      spCtx.shadowColor = s.col; spCtx.shadowBlur = 3;
      spCtx.beginPath(); spCtx.arc(s.x, s.y, s.r, 0, Math.PI * 2); spCtx.fill(); spCtx.restore();
    }
    requestAnimationFrame(animSpC);
  }
  initSpC(); animSpC(); window.addEventListener('resize', initSpC);
}

// Check existing session on load
(async () => {
  const valid = await checkSession();
  if (valid) {
    enterMain();
  } else {
    document.getElementById('authInput').focus();
  }
})();

// Telegram WebApp integration
if (window.Telegram?.WebApp) {
  window.Telegram.WebApp.ready();
  window.Telegram.WebApp.expand();
}

// -- PUBLIC API --
return {
  // Auth
  doAuth, logout,
  // Language
  genToken, genReaderToken, importToken, selectLang, deleteLang,
  copyToken, setMode,
  // Encode
  doEncode, copyEncoded, selSh, toBot,
  // Decode
  doDecode,
  // Bot
  simType, simSend, chooseOpt,
  // Tabs
  swTab,
  // Sidebar
  toggleMusic, prevTrack, nextTrack,
  setMood, petClick, feedPet,
  nextQ, addGb,
  // Eggs
  showEgg, closeEgg,
};

})();
