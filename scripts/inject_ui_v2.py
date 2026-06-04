#!/usr/bin/env python3
"""
inject_ui_v2.py — index.html に UI V2 コードを注入する

FEATURE_UI_V2 = false がデフォルト。
?ui=v2 または localStorage.setItem('ui','v2') で ON になる。
"""

import re, sys
from pathlib import Path

BASE = Path(__file__).parent.parent

# ═══════════════════════════════════════════════════════════════════════════════
# V2 CSS (</style> 直前に挿入)
# ═══════════════════════════════════════════════════════════════════════════════
V2_CSS = """
/* ══ UI V2 ═══════════════════════════════════════════════════════════════════
   FEATURE_UI_V2 が ON のとき body[data-ui="v2"] クラスで適用される。
   既存 v1 スタイルは一切変更しない。
   ══════════════════════════════════════════════════════════════════════════ */

/* ── A: スティッキー ctrl バー ────────────────────────────────────────────── */
[data-ui="v2"] .ctrl{
  position:sticky;top:57px;z-index:90;
  background:#f5f4f0;
  padding-top:10px;padding-bottom:6px;
  box-shadow:0 2px 8px rgba(0,0,0,.07);
  transition:box-shadow .15s;
}

/* ── B: フィルターチップ ──────────────────────────────────────────────────── */
.v2-chips{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:8px;min-height:0;transition:min-height .15s;}
.v2-chip{display:inline-flex;align-items:center;gap:4px;padding:4px 11px;
  background:#1a1a1a;color:#fff;border-radius:20px;font-size:11px;
  font-weight:600;cursor:pointer;user-select:none;transition:background .1s;}
.v2-chip:hover{background:#333;}
.v2-chip-x{font-size:14px;line-height:1;margin-left:1px;}
.v2-fav-chip{background:#c0392b;}
.v2-fav-chip:hover{background:#a93226;}

/* ── C: ドロワー / ボトムシート ──────────────────────────────────────────── */
.v2-drawer-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.45);z-index:600;}
.v2-drawer-overlay.open{display:flex;justify-content:flex-end;align-items:stretch;}
.v2-drawer{
  width:min(500px,100vw);background:#fff;overflow-y:auto;
  display:flex;flex-direction:column;padding:0;
  animation:v2slideRight .22s ease;
}
@keyframes v2slideRight{from{transform:translateX(30px);opacity:0}to{transform:translateX(0);opacity:1}}
.v2-dh{padding:18px 20px 14px;border-bottom:1px solid #eae9e4;flex-shrink:0;}
.v2-dh-top{display:flex;justify-content:space-between;align-items:flex-start;}
.v2-dname{font-size:17px;font-weight:700;line-height:1.3;}
.v2-djp{font-size:12px;color:#999;margin-top:2px;}
.v2-dbadges{display:flex;flex-wrap:wrap;gap:4px;margin-top:8px;}
.v2-dclose{background:none;border:none;font-size:22px;cursor:pointer;color:#bbb;
  min-width:44px;min-height:44px;display:flex;align-items:center;justify-content:flex-end;flex-shrink:0;}
.v2-dclose:hover{color:#333;}
.v2-dbody{flex:1;overflow-y:auto;padding:16px 20px 32px;}
.v2-dfin{display:grid;grid-template-columns:repeat(3,1fr);gap:7px;margin-bottom:14px;}
.v2-dm{background:#f7f6f1;border-radius:8px;padding:8px 10px;}
.v2-dml{font-size:10px;color:#aaa;margin-bottom:3px;}
.v2-dmv{font-size:13px;font-weight:700;color:#1a1a1a;}
.v2-dmv.pos{color:#1a7a4a;}.v2-dmv.neg{color:#c0392b;}.v2-dmv.hi{color:#1a56c4;}
.v2-dsec{margin-bottom:12px;}
.v2-dsl{font-size:10px;color:#aaa;text-transform:uppercase;letter-spacing:.5px;font-weight:700;margin-bottom:4px;}
.v2-dsv{font-size:12.5px;color:#333;line-height:1.65;overflow-wrap:break-word;}
.v2-dsv.pros{color:#1a7a4a;}.v2-dsv.cons{color:#c0392b;}
.v2-summary-box{background:#f0f4ff;border-left:3px solid #1a56c4;border-radius:0 8px 8px 0;
  padding:10px 12px;margin-bottom:14px;font-size:13px;line-height:1.7;color:#333;}
.v2-fix-box{font-size:11px;background:#fffbe6;border:1px solid #ffe566;
  border-radius:6px;padding:5px 10px;margin-bottom:12px;color:#7a5a00;}
.v2-src-link{display:inline-flex;align-items:center;gap:5px;padding:6px 12px;
  border-radius:7px;font-size:12px;font-weight:600;text-decoration:none;
  border:1px solid;background:#f0f4ff;color:#1a56c4;border-color:#c0d0f0;margin-top:4px;}
.v2-src-link:hover{opacity:.7;}

/* Mobile: ボトムシート */
@media(max-width:599px){
  .v2-drawer-overlay.open{align-items:flex-end;justify-content:center;}
  .v2-drawer{width:100%;max-height:92vh;border-radius:18px 18px 0 0;
    animation:v2slideUp .22s ease;}
  @keyframes v2slideUp{from{transform:translateY(30px);opacity:0}to{transform:translateY(0);opacity:1}}
  .v2-dfin{grid-template-columns:repeat(2,1fr);}
}

/* ── D: お気に入り ─────────────────────────────────────────────────────────── */
.v2-fav-btn{
  position:absolute;top:8px;right:8px;
  background:none;border:none;font-size:18px;cursor:pointer;
  line-height:1;padding:4px;opacity:.3;transition:opacity .12s,transform .1s;
}
.v2-fav-btn:hover{opacity:.8;transform:scale(1.15);}
.v2-fav-btn.on{opacity:1;color:#e74c3c;}
[data-ui="v2"] .cc{position:relative;}

/* ── G: 変更履歴ビュー ────────────────────────────────────────────────────── */
.v2-cl-wrap{background:#fff;border:1px solid #eae9e4;border-radius:12px;
  padding:16px;margin-bottom:14px;}
.v2-cl-title{font-size:13px;font-weight:700;color:#1a1a1a;margin-bottom:10px;}
.v2-cl-empty{font-size:13px;color:#bbb;text-align:center;padding:20px 0;}
.v2-cl-item{display:flex;gap:10px;padding:7px 0;border-bottom:1px solid #f0efe9;align-items:flex-start;}
.v2-cl-item:last-child{border-bottom:none;}
.v2-cl-date{font-size:10px;color:#aaa;min-width:70px;padding-top:2px;}
.v2-cl-co{font-size:12px;font-weight:600;min-width:110px;}
.v2-cl-note{font-size:11.5px;color:#555;line-height:1.55;flex:1;}

/* ── タブナビ V2 ────────────────────────────────────────────────────────────── */
[data-ui="v2"] .stab[data-tab="fav"]{border-color:#e74c3c;}
[data-ui="v2"] .stab[data-tab="fav"].on{background:#e74c3c;border-color:#e74c3c;}
[data-ui="v2"] .stab[data-tab="cl"].on{background:#1a56c4;border-color:#1a56c4;}
"""

# ═══════════════════════════════════════════════════════════════════════════════
# V2 HTML (</header> の後に挿入)
# ═══════════════════════════════════════════════════════════════════════════════
V2_HTML = """
<!-- ── UI V2: ドロワー オーバーレイ ──────────────────────────────────────── -->
<div class="v2-drawer-overlay" id="v2drawer" onclick="v2DrawerOverlayClick(event)">
  <div class="v2-drawer" id="v2drawerPanel" onclick="event.stopPropagation()">
    <div class="v2-dh">
      <div class="v2-dh-top">
        <div>
          <div class="v2-dname" id="v2dname"></div>
          <div class="v2-djp" id="v2djp"></div>
        </div>
        <button class="v2-dclose" onclick="v2CloseDrawer()">✕</button>
      </div>
      <div class="v2-dbadges" id="v2dbadges"></div>
    </div>
    <div class="v2-dbody" id="v2dbody"></div>
  </div>
</div>

<!-- ── UI V2: フィルターチップ コンテナ ──────────────────────────────────── -->
<div class="v2-chips" id="v2chips" style="display:none"></div>
"""

# ═══════════════════════════════════════════════════════════════════════════════
# V2 JavaScript (</script> 直前に挿入)
# ═══════════════════════════════════════════════════════════════════════════════
V2_JS = r"""
// ══════════════════════════════════════════════════════════════════════════════
// UI V2 — FEATURE FLAG
// ON: ?ui=v2  OR  localStorage.setItem('ui','v2')
// OFF: ?ui=v1  OR  localStorage.setItem('ui','v1') (またはデフォルト)
// ══════════════════════════════════════════════════════════════════════════════
(function(){
  const sp = new URLSearchParams(location.search);
  if(sp.has('ui')){
    if(sp.get('ui')==='v2') localStorage.setItem('ui','v2');
    else localStorage.removeItem('ui');
  }
})();

const FEATURE_UI_V2 = localStorage.getItem('ui')==='v2';

if(FEATURE_UI_V2){
  document.body.setAttribute('data-ui','v2');
  // v2チップコンテナを表示
  const chipsEl = document.getElementById('v2chips');
  if(chipsEl) chipsEl.style.display = 'flex';
}

// ── E: URL 状態管理 ──────────────────────────────────────────────────────────
function v2PushState(){
  if(!FEATURE_UI_V2) return;
  const p = new URLSearchParams({ui:'v2'});
  if(fs.q) p.set('q', fs.q);
  if(fs.ct && fs.ct!=='전체') p.set('ct', fs.ct);
  if(fs.gn && fs.gn!=='전체') p.set('gn', fs.gn);
  if(fs.ma && fs.ma!=='전체') p.set('ma', fs.ma);
  if(fs.tp && fs.tp!=='전체') p.set('tp', fs.tp);
  if(fs.ip && fs.ip!=='전체') p.set('ip', fs.ip);
  if(sortMode && sortMode!=='default') p.set('sort', sortMode);
  history.replaceState(null,'',location.pathname+'?'+p.toString());
}

function v2RestoreState(){
  if(!FEATURE_UI_V2) return;
  const p = new URLSearchParams(location.search);
  if(p.get('q'))    { fs.q=p.get('q'); const el=document.getElementById('srch'); if(el) el.value=fs.q; }
  if(p.get('ct'))   fs.ct=p.get('ct');
  if(p.get('gn'))   fs.gn=p.get('gn');
  if(p.get('ma'))   fs.ma=p.get('ma');
  if(p.get('tp'))   fs.tp=p.get('tp');
  if(p.get('ip'))   fs.ip=p.get('ip');
  if(p.get('sort')) sortMode=p.get('sort');
}

// ── D: お気に入り (localStorage) ─────────────────────────────────────────────
let v2favs = new Set(JSON.parse(localStorage.getItem('v2favs')||'[]'));

function v2SaveFavs(){
  localStorage.setItem('v2favs', JSON.stringify([...v2favs]));
}

function v2ToggleFav(idx, ev){
  if(ev){ ev.stopPropagation(); }
  if(v2favs.has(idx)) v2favs.delete(idx);
  else v2favs.add(idx);
  v2SaveFavs();
  // ボタン UI 更新
  const btn = document.querySelector(`.v2-fav-btn[data-idx="${idx}"]`);
  if(btn) btn.classList.toggle('on', v2favs.has(idx));
  // お気に入りタブ中なら再描画
  if(fs.tp==='fav') renderCards();
  v2RenderChips();
}

// ── B: フィルターチップ ──────────────────────────────────────────────────────
const V2_CHIP_LABELS = {ct:'国',gn:'ジャンル',ma:'MA',ip:'自社IP',tp:'タブ',q:'検索'};

function v2RenderChips(){
  if(!FEATURE_UI_V2) return;
  const el = document.getElementById('v2chips');
  if(!el) return;
  const chips = [];
  const add = (k,v,label)=>{
    chips.push(`<span class="v2-chip${k==='fav'?' v2-fav-chip':''}"
      onclick="v2RemoveChip('${k}')">${label}<span class="v2-chip-x">✕</span></span>`);
  };
  if(fs.q) add('q',fs.q,`"${fs.q}"`);
  if(fs.ct!=='전체') add('ct',fs.ct,`国: ${fs.ct}`);
  if(fs.gn!=='전체') add('gn',fs.gn,`ジャンル: ${fs.gn}`);
  if(fs.ma!=='전체') add('ma',fs.ma,`MA: ${fs.ma}`);
  if(fs.ip!=='전체') add('ip',fs.ip,`自社IP: ${fs.ip}`);
  if(fs.tp==='fav') add('fav','fav','★ お気に入り');
  el.innerHTML = chips.join('');
  el.style.display = chips.length ? 'flex' : 'none';
  v2PushState();
}

function v2RemoveChip(k){
  if(k==='q'){ fs.q=''; const e=document.getElementById('srch'); if(e) e.value=''; }
  else if(k==='fav') fs.tp='전체';
  else if(k==='ct') fs.ct='전체';
  else if(k==='gn') fs.gn='전체';
  else if(k==='ma') fs.ma='전체';
  else if(k==='ip') fs.ip='전체';
  renderFilters(); renderCards();
  v2RenderChips();
}

// ── C: ドロワー ───────────────────────────────────────────────────────────────
function v2OpenDrawer(idx){
  const c = D[idx];
  if(!c) return;

  // ヘッダー
  document.getElementById('v2dname').textContent = c.nk||c.n||'';
  document.getElementById('v2djp').textContent = c.n||'';

  // バッジ
  const maMap={O:'매수 가능',X:'직접 접근 불가',N:'미검토','조건부':'조건부','accel':'Accel'};
  const maLabel = c.type==='accel'?'Accel':(maMap[c.ma]||c.ma||'');
  const maCol   = c.ma==='O'?'g':c.ma==='X'?'r':'d';
  const gnB = c.gn?`<span class="modal-badge" style="background:#f0f4ff;color:#1a56c4;border:1px solid #c0d0f0;padding:3px 9px;border-radius:20px;font-size:11px;font-weight:600">${c.gn}</span>`:'';
  const maB = maLabel?`<span class="modal-badge modal-badge-${maCol}" style="padding:3px 9px;border-radius:20px;font-size:11px;font-weight:600">${maLabel}</span>`:'';
  document.getElementById('v2dbadges').innerHTML = gnB + maB;

  // 6行 エグゼクティブサマリー
  const sumLines = [
    c.ch ? c.ch.slice(0,120)+(c.ch.length>120?'…':'') : null,
    c.pr ? '✅ '+c.pr.slice(0,80) : null,
    c.cn ? '⚠️ '+c.cn.slice(0,80) : null,
    c.sh ? '📊 주주: '+c.sh.slice(0,60) : null,
    c.mr ? '🔍 MA: '+c.mr.slice(0,80) : null,
  ].filter(Boolean).slice(0,6).join('\n');

  // 財務
  const fmt = v => v==null?'-':
    v>=1e12?(v/1e12).toFixed(1)+'조엔':
    v>=1e8 ?(v/1e8).toFixed(0)+'억엔':
    v+'엔';
  const fmtMg = v => v==null?'-':v>0?'+'+v+'%':v+'%';
  const mgCls = c.mg>15?'pos':c.mg<0?'neg':'';

  // ソースリンク(H: メタデータ)
  let srcHtml='';
  if(c.src_url) srcHtml += `<a class="v2-src-link" href="${c.src_url}" target="_blank" rel="noopener">🔗 ソース</a>`;

  // 修正メモ
  const fixHtml = c.fix ? `<div class="v2-fix-box">📝 ${c.fix.slice(0,200)}${c.fix.length>200?'…':''}</div>` : '';

  // 信頼度 (H: confidence があれば表示)
  const confHtml = c.confidence ? `<div class="v2-dsec"><div class="v2-dsl">信頼度</div><div class="v2-dsv">${c.confidence}</div></div>` : '';
  // asof_date (H)
  const asofHtml = c.asof_date ? `<div class="v2-dsec"><div class="v2-dsl">기준 시점</div><div class="v2-dsv">${c.asof_date}</div></div>` : '';

  document.getElementById('v2dbody').innerHTML = `
    <div class="v2-dfin">
      <div class="v2-dm"><div class="v2-dml">시총</div><div class="v2-dmv hi">${fmt(c.mk)}</div></div>
      <div class="v2-dm"><div class="v2-dml">매출</div><div class="v2-dmv">${fmt(c.rv)}</div></div>
      <div class="v2-dm"><div class="v2-dml">이익률</div><div class="v2-dmv ${mgCls}">${fmtMg(c.mg)}</div></div>
    </div>
    ${sumLines ? `<div class="v2-summary-box">${sumLines.replace(/\n/g,'<br>')}</div>` : ''}
    ${fixHtml}
    ${c.tt?`<div class="v2-dsec"><div class="v2-dsl">주요 타이틀</div><div class="v2-dsv">${c.tt.slice(0,200)}</div></div>`:''}
    ${c.pr?`<div class="v2-dsec"><div class="v2-dsl">장점</div><div class="v2-dsv pros">${c.pr.slice(0,200)}</div></div>`:''}
    ${c.cn?`<div class="v2-dsec"><div class="v2-dsl">단점/리스크</div><div class="v2-dsv cons">${c.cn.slice(0,200)}</div></div>`:''}
    ${c.sh?`<div class="v2-dsec"><div class="v2-dsl">주주구조</div><div class="v2-dsv">${c.sh.slice(0,200)}</div></div>`:''}
    ${c.rep?`<div class="v2-dsec"><div class="v2-dsl">대표이사</div><div class="v2-dsv">${c.rep}</div></div>`:''}
    ${confHtml}${asofHtml}
    ${srcHtml?`<div class="v2-dsec">${srcHtml}</div>`:''}
  `;

  document.getElementById('v2drawer').classList.add('open');
  document.body.style.overflow = 'hidden';
}

function v2CloseDrawer(){
  document.getElementById('v2drawer').classList.remove('open');
  document.body.style.overflow = '';
}

function v2DrawerOverlayClick(e){
  if(e.target === document.getElementById('v2drawer')) v2CloseDrawer();
}

// ── G: 変更履歴ビュー ─────────────────────────────────────────────────────────
function v2RenderChangelog(){
  const el = document.getElementById('grid');
  if(!el) return;
  // fix フィールドに '[2025-2026 업데이트]' または日付を持つエントリを抽出
  const entries = D.map((c,i)=>({c,i}))
    .filter(({c})=> c.fix && c.fix.length > 5)
    .slice(0, 50); // 最大50件

  if(!entries.length){
    el.innerHTML = `<div class="v2-cl-wrap"><div class="v2-cl-title">📋 변경 이력</div>
      <div class="v2-cl-empty">업데이트 메모가 있는 기업이 없습니다.</div></div>`;
    return;
  }

  const rows = entries.map(({c,i})=>`
    <div class="v2-cl-item" onclick="FEATURE_UI_V2?v2OpenDrawer(${i}):openModal(${i})" style="cursor:pointer">
      <div class="v2-cl-date">${(c.fix||'').match(/\d{4}[년\-\.]\d{1,2}/)?.[0]||'2025'}</div>
      <div class="v2-cl-co">${c.nk||c.n||''}</div>
      <div class="v2-cl-note">${(c.fix||'').replace(/^\[2025-2026 업데이트\]\s*/,'').slice(0,120)}</div>
    </div>`).join('');

  el.innerHTML = `<div class="v2-cl-wrap">
    <div class="v2-cl-title">📋 변경 이력 (최근 ${entries.length}건)</div>
    ${rows}
  </div>`;
}

// ── V2 カードに ★ ボタンを追加 ─────────────────────────────────────────────
const _origRenderCards = typeof renderCards === 'function' ? renderCards : null;

function v2AugmentCards(){
  if(!FEATURE_UI_V2) return;
  document.querySelectorAll('.cc[data-idx]').forEach(card=>{
    const idx = parseInt(card.getAttribute('data-idx'));
    if(isNaN(idx)) return;
    if(card.querySelector('.v2-fav-btn')) return; // すでに追加済み
    const btn = document.createElement('button');
    btn.className = 'v2-fav-btn' + (v2favs.has(idx)?' on':'');
    btn.setAttribute('data-idx', idx);
    btn.setAttribute('aria-label', 'お気に入り');
    btn.textContent = '★';
    btn.onclick = (e)=>v2ToggleFav(idx,e);
    card.appendChild(btn);
  });
}

// ── セットアップ & 既存関数をラップ ─────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function(){
  if(!FEATURE_UI_V2) return;

  // E: URL 状態を復元
  v2RestoreState();

  // タブに「★お気に入り」「📋변경이력」を追加
  const ctb = document.getElementById('ctb');
  if(ctb){
    const favBtn = document.createElement('span');
    favBtn.className = 'stab' + (fs.tp==='fav'?' on':'');
    favBtn.setAttribute('data-tab','fav');
    favBtn.textContent = '★ 즐겨찾기';
    favBtn.onclick = ()=>{ setF('tp','fav'); };

    const clBtn = document.createElement('span');
    clBtn.className = 'stab' + (fs.tp==='cl'?' on':'');
    clBtn.setAttribute('data-tab','cl');
    clBtn.textContent = '📋 변경이력';
    clBtn.onclick = ()=>{ setF('tp','cl'); };

    ctb.appendChild(favBtn);
    ctb.appendChild(clBtn);
  }

  // チップを ctrl の前に挿入
  const ctrl = document.querySelector('.ctrl');
  const chipsEl = document.getElementById('v2chips');
  if(ctrl && chipsEl && ctrl.parentNode){
    ctrl.parentNode.insertBefore(chipsEl, ctrl);
  }

  // ESC キー
  document.addEventListener('keydown', e=>{
    if(e.key==='Escape') v2CloseDrawer();
  });

  v2RenderChips();
});

// ── setF / renderCards をラップして V2 処理を追加 ────────────────────────────
const _v2_origSetF = setF;
setF = function(k,v){
  _v2_origSetF(k,v);
  if(FEATURE_UI_V2){
    v2RenderChips();
    // タブボタンの on クラスを更新
    document.querySelectorAll('.stab[data-tab]').forEach(btn=>{
      btn.classList.toggle('on', btn.getAttribute('data-tab')===fs.tp);
    });
  }
};

const _v2_origRenderCards = renderCards;
renderCards = function(){
  if(FEATURE_UI_V2 && fs.tp==='cl'){
    // 変更履歴ビュー
    const grid = document.getElementById('grid');
    if(grid){ v2RenderChangelog(); return; }
  }
  if(FEATURE_UI_V2 && fs.tp==='fav'){
    // お気に入りフィルター
    const origTp = fs.tp;
    fs.tp = '전체';
    const allFiltered = filtered();
    fs.tp = origTp;
    const favFiltered = allFiltered.filter(idx => v2favs.has(idx));
    // favFiltered を使って描画 (filtered() をモンキーパッチ)
    const _f = filtered;
    filtered = ()=>favFiltered;
    _v2_origRenderCards();
    filtered = _f;
    v2AugmentCards();
    return;
  }
  _v2_origRenderCards();
  if(FEATURE_UI_V2){
    v2AugmentCards();
    // カードクリックをドロワーに差し替え
    document.querySelectorAll('.cc[data-idx]').forEach(card=>{
      const idx = parseInt(card.getAttribute('data-idx'));
      if(isNaN(idx)) return;
      // 既存の onclick を退避して上書き
      card.onclick = function(e){
        if(e.target.classList.contains('v2-fav-btn')) return;
        if(e.target.classList.contains('arr')) return;
        v2OpenDrawer(idx);
      };
    });
  }
};
"""

# ═══════════════════════════════════════════════════════════════════════════════
# 注入処理
# ═══════════════════════════════════════════════════════════════════════════════
def inject(src: str = None, out: str = None):
    src = Path(src or BASE / 'index.html')
    out = Path(out or src)
    html = src.read_text(encoding='utf-8')

    # 1) </style> 直前に CSS を挿入
    if '/* ══ UI V2' not in html:
        html = html.replace('</style>', V2_CSS + '\n</style>', 1)
        print('✅ CSS 挿入')
    else:
        print('ℹ️  CSS 既存スキップ')

    # 2) </header> の後に HTML を挿入 (id="v2drawer" で判定)
    if 'id="v2drawer"' not in html:
        html = html.replace('</header>', '</header>\n' + V2_HTML, 1)
        print('✅ HTML 挿入')
    else:
        print('ℹ️  HTML 既存スキップ')

    # 3) </script> 直前に JS を挿入 (v2OpenDrawer で判定)
    if 'v2OpenDrawer' not in html:
        html = html.replace('</script>', V2_JS + '\n</script>', 1)
        print('✅ JS 挿入')
    else:
        print('ℹ️  JS 既存スキップ')

    out.write_text(html, encoding='utf-8')
    kb = out.stat().st_size // 1024
    print(f'✅ 完了: {out} ({kb}KB)')


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', default=None)
    ap.add_argument('--out', default=None)
    args = ap.parse_args()
    inject(args.src, args.out)
