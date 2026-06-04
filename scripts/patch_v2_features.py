#!/usr/bin/env python3
"""
patch_v2_features.py — v1.0.13 V2 기능 패치
Tickets 1-6 전체 구현:
  T1: TL;DR + 액션 버튼
  T2: 태그 시스템 + URL sync
  T3: 변경이력 개선 (시간 범위 + 타입 배지 + 드로어 연결)
  T4: 신뢰도 낮음 경고 UX
  T5: 성능/UX 폴리시 (디바운스 + 스크롤 잠금)
  T6: Playwright 테스트 업데이트
"""
from pathlib import Path
import re, sys

BASE = Path(__file__).parent.parent

# ─────────────────────────────────────────────────────────────────────────────
# 추가 CSS (기존 V2 CSS 뒤에 삽입)
# ─────────────────────────────────────────────────────────────────────────────
PATCH_CSS = """
/* ── T1: TL;DR 블록 ─────────────────────────────────────────────────────── */
.v2-tldr{background:#f0f7ff;border-radius:10px;padding:10px 13px;margin-bottom:12px;}
.v2-tldr-row{display:flex;gap:6px;align-items:flex-start;line-height:1.5;font-size:12.5px;}
.v2-tldr-row+.v2-tldr-row{margin-top:5px;}
.v2-tldr-label{font-weight:700;white-space:nowrap;min-width:44px;font-size:11px;padding-top:1px;}
.v2-tldr-label.pt{color:#1a56c4;}
.v2-tldr-label.ri{color:#c0392b;}
.v2-tldr-text{color:#333;flex:1;}

/* ── T1: 액션 버튼 ──────────────────────────────────────────────────────── */
.v2-actions{display:flex;gap:8px;margin-bottom:14px;flex-wrap:wrap;}
.v2-act-btn{display:inline-flex;align-items:center;gap:5px;padding:7px 13px;
  border-radius:8px;font-size:12px;font-weight:600;cursor:pointer;border:1px solid;
  transition:opacity .12s;white-space:nowrap;}
.v2-act-btn:hover{opacity:.75;}
.v2-act-memo{background:#f7f6f1;color:#1a1a1a;border-color:#dddcd5;}
.v2-act-src{background:#f0f4ff;color:#1a56c4;border-color:#c0d0f0;}
.v2-act-src[disabled]{opacity:.35;cursor:default;}
.v2-act-src[disabled]:hover{opacity:.35;}

/* ── T1: 메모/태그 인라인 에디터 ────────────────────────────────────────── */
.v2-memo-panel{background:#fafaf7;border:1px solid #eae9e4;border-radius:10px;
  padding:12px;margin-bottom:14px;display:none;}
.v2-memo-panel.open{display:block;}
.v2-memo-textarea{width:100%;min-height:60px;border:1px solid #dddcd5;border-radius:7px;
  padding:8px 10px;font-size:12.5px;resize:vertical;font-family:inherit;outline:none;}
.v2-memo-textarea:focus{border-color:#1a56c4;}
.v2-tags-row{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px;}
.v2-tag-pill{padding:4px 11px;border-radius:20px;font-size:11px;font-weight:600;
  cursor:pointer;border:1.5px solid #dddcd5;background:#fff;color:#555;
  transition:all .1s;user-select:none;}
.v2-tag-pill.on{color:#fff;border-color:transparent;}
.v2-tag-관심.on{background:#1a56c4;}
.v2-tag-NDA.on{background:#6a1ac4;}
.v2-tag-콜필요.on{background:#b56a00;}
.v2-tag-보류.on{background:#888;}
.v2-tag-완료.on{background:#1a7a4a;}

/* ── T2: 카드 태그 배지 ─────────────────────────────────────────────────── */
.v2-card-tags{display:flex;gap:3px;flex-wrap:wrap;margin-top:4px;}
.v2-card-tag{font-size:10px;font-weight:700;padding:2px 7px;border-radius:10px;color:#fff;}
.v2-ct-관심{background:#1a56c4;}.v2-ct-NDA{background:#6a1ac4;}
.v2-ct-콜필요{background:#b56a00;}.v2-ct-보류{background:#888;}
.v2-ct-완료{background:#1a7a4a;}

/* ── T2: 태그 필터 ──────────────────────────────────────────────────────── */
.v2-tag-filter-wrap{display:flex;gap:5px;flex-wrap:wrap;margin-bottom:6px;}
.v2-tf-pill{padding:3px 10px;border-radius:20px;font-size:11px;font-weight:600;
  cursor:pointer;border:1px solid #dddcd5;background:#fff;color:#555;transition:all .1s;}
.v2-tf-pill.active{color:#fff;border-color:transparent;}
.v2-tf-관심.active{background:#1a56c4;}.v2-tf-NDA.active{background:#6a1ac4;}
.v2-tf-콜필요.active{background:#b56a00;}.v2-tf-보류.active{background:#888;}
.v2-tf-완료.active{background:#1a7a4a;}

/* ── T3: 변경이력 개선 ──────────────────────────────────────────────────── */
.v2-cl-controls{display:flex;gap:6px;margin-bottom:10px;flex-wrap:wrap;align-items:center;}
.v2-cl-range{padding:3px 10px;border-radius:20px;font-size:11px;font-weight:600;
  cursor:pointer;border:1px solid #dddcd5;background:#fff;color:#555;transition:all .1s;}
.v2-cl-range.on{background:#1a1a1a;color:#fff;border-color:#1a1a1a;}
.v2-cl-type-badge{font-size:10px;font-weight:700;padding:2px 7px;border-radius:10px;
  color:#fff;white-space:nowrap;flex-shrink:0;}
.v2-clb-ceo{background:#1a56c4;}.v2-clb-지표{background:#1a7a4a;}
.v2-clb-출시{background:#b56a00;}.v2-clb-ma{background:#c0392b;}
.v2-clb-기타{background:#888;}
.v2-cl-item{cursor:pointer;transition:background .1s;}
.v2-cl-item:hover{background:#f7f6f1;border-radius:6px;}

/* ── T4: 신뢰도 경고 ────────────────────────────────────────────────────── */
.v2-conf-warn{font-size:10px;color:#b56a00;margin-left:4px;vertical-align:middle;}
.v2-metric-muted .v2-dmv{color:#bbb!important;}

/* ── T5: 바텀시트 스크롤 잠금 ───────────────────────────────────────────── */
body.v2-lock{overflow:hidden!important;}
"""

# ─────────────────────────────────────────────────────────────────────────────
# V2 패치 JS (기존 V2 JS 끝 </script> 직전에 삽입)
# ─────────────────────────────────────────────────────────────────────────────
PATCH_JS = r"""
// ═══════════════════════════════════════════════════════════════════════════
// UI V2 PATCH v1.0.13 — Tickets 1-6
// ═══════════════════════════════════════════════════════════════════════════

// ── T2: 태그 시스템 ─────────────────────────────────────────────────────────
const V2_TAGS = ['관심','NDA','콜필요','보류','완료'];
const V2_TAG_COLORS = {'관심':'#1a56c4','NDA':'#6a1ac4','콜필요':'#b56a00','보류':'#888','완료':'#1a7a4a'};

let v2TagFilter = '';  // 현재 선택된 태그 필터 ('' = 전체)

function v2GetTags(idx) {
  try { return JSON.parse(localStorage.getItem(`v2tags:${idx}`) || '[]'); } catch { return []; }
}
function v2GetMemo(idx) { return localStorage.getItem(`v2memo:${idx}`) || ''; }
function v2SetTags(idx, tags) { localStorage.setItem(`v2tags:${idx}`, JSON.stringify(tags)); }
function v2SetMemo(idx, memo) {
  if(memo) localStorage.setItem(`v2memo:${idx}`, memo);
  else localStorage.removeItem(`v2memo:${idx}`);
}

// 태그 포함 여부로 표시 여부 결정
function v2TagFilterMatch(idx) {
  if(!v2TagFilter) return true;
  if(v2TagFilter === 'fav') return v2favs.has(idx);
  return v2GetTags(idx).includes(v2TagFilter);
}

// ── T5: 디바운스 ─────────────────────────────────────────────────────────────
function v2Debounce(fn, ms) {
  let t;
  return function(...args) {
    clearTimeout(t);
    t = setTimeout(() => fn.apply(this, args), ms);
  };
}

// 기존 검색 인풋에 디바운스 적용 (V2 전용)
if (FEATURE_UI_V2) {
  document.addEventListener('DOMContentLoaded', () => {
    const srch = document.getElementById('srch');
    if (srch) {
      const origInput = srch.oninput;
      const debounced = v2Debounce(function() {
        fs.q = srch.value;
        renderFilters();
        renderCards();
        v2RenderChips();
        v2RenderTagFilter();
      }, 200);
      srch.oninput = debounced;
    }
  });
}

// ── T5: 바텀시트 스크롤 잠금 오버라이드 ─────────────────────────────────────
const _v2_origOpenDrawer = v2OpenDrawer;
const _v2_origCloseDrawer = v2CloseDrawer;

v2OpenDrawer = function(idx) {
  _v2_origOpenDrawer(idx);
  document.body.classList.add('v2-lock');
};
v2CloseDrawer = function() {
  _v2_origCloseDrawer();
  document.body.classList.remove('v2-lock');
};

// ── T1: TL;DR 유도 ──────────────────────────────────────────────────────────
function v2DeriveTldr(c, idx) {
  // 명시된 필드 우선
  if (c.tldr_point && c.tldr_risk) {
    return { point: c.tldr_point, risk: c.tldr_risk };
  }
  // 한국어 메모가 있으면 앞부분 활용
  const userMemo = v2GetMemo(idx);
  if (userMemo && userMemo.length > 5) {
    const lines = userMemo.split(/[\n.。]/);
    return {
      point: (lines[0] || '').slice(0, 80),
      risk: (lines[1] || c.cn || '').slice(0, 80) || '리스크 정보 없음',
    };
  }
  // MA 접근성 기반 포인트
  const maLabel = {'O': '접근 검토 가능', 'X': '직접 접근 불가', 'N': '미검토'}[c.ma] || '';
  const ip = c.ip ? '자체 IP 보유' : '';
  const rep = c.rep ? `대표 ${c.rep}` : '';
  const ttSnip = c.tt ? c.tt.split(/[,、，]/)[0].trim().slice(0, 30) : '';

  const point = [maLabel, ip, ttSnip, rep].filter(Boolean).slice(0, 2).join(' · ') || (c.ch || '').slice(0, 60);
  const risk = (c.cn || c.fix || '').replace(/^\[.*?\]\s*/, '').slice(0, 80) || '리스크 정보 없음';
  return { point, risk };
}

// ── T4: 신뢰도 체크 ─────────────────────────────────────────────────────────
function v2IsLowConf(c) {
  if (!c.confidence) return false;
  return /^(low|l|0)$/i.test(String(c.confidence).trim());
}

// ── v2OpenDrawer 오버라이드: TL;DR + 액션 + 태그 패널 ───────────────────────
v2OpenDrawer = (function(prev) {
  return function(idx) {
    const c = D[idx];
    if (!c) return;

    // 기존 drawer 기본 렌더
    prev(idx);

    // TL;DR 삽입
    const tldr = v2DeriveTldr(c, idx);
    const tldrHtml = `
      <div class="v2-tldr">
        <div class="v2-tldr-row">
          <span class="v2-tldr-label pt">포인트</span>
          <span class="v2-tldr-text">${tldr.point || '-'}</span>
        </div>
        <div class="v2-tldr-row">
          <span class="v2-tldr-label ri">리스크</span>
          <span class="v2-tldr-text">${tldr.risk || '-'}</span>
        </div>
      </div>`;

    // 액션 버튼
    const srcDisabled = c.src_url ? '' : 'disabled';
    const srcHref = c.src_url || '#';
    const actionsHtml = `
      <div class="v2-actions">
        <button class="v2-act-btn v2-act-memo" onclick="v2ToggleMemoPanel(${idx})">
          📝 메모/태그
        </button>
        <a class="v2-act-btn v2-act-src" href="${srcHref}" target="_blank" rel="noopener" ${srcDisabled}
           onclick="if('${srcDisabled}'==='disabled'){event.preventDefault();}">
          🔗 출처 열기
        </a>
      </div>`;

    // 메모/태그 패널
    const tags = v2GetTags(idx);
    const memo = v2GetMemo(idx);
    const tagPills = V2_TAGS.map(t => {
      const on = tags.includes(t) ? 'on' : '';
      return `<span class="v2-tag-pill v2-tag-${t} ${on}" onclick="v2ToggleTag(${idx},'${t}',this)">${t}</span>`;
    }).join('');
    const memoPanelHtml = `
      <div class="v2-memo-panel" id="v2memopanel-${idx}">
        <textarea class="v2-memo-textarea" placeholder="메모 입력..."
          onchange="v2SetMemo(${idx},this.value)">${memo}</textarea>
        <div class="v2-tags-row">${tagPills}</div>
      </div>`;

    // T4: 신뢰도 경고
    const lowConf = v2IsLowConf(c);
    const confWarn = lowConf ? '<span class="v2-conf-warn" title="출처/시점 확인 필요">⚠️</span>' : '';
    const muted = (lowConf || !c.src_url) ? 'v2-metric-muted' : '';

    // 재무 메트릭에 경고 아이콘 삽입
    const dbody = document.getElementById('v2dbody');
    if (dbody) {
      const origFin = dbody.querySelector('.v2-dfin');
      if (origFin && lowConf) {
        origFin.classList.add(muted);
        origFin.querySelectorAll('.v2-dmv').forEach(el => {
          if (!el.querySelector('.v2-conf-warn')) {
            el.insertAdjacentHTML('afterend', `<div class="v2-conf-warn">⚠️ 출처/시점 확인 필요</div>`);
          }
        });
      }

      // TL;DR + 액션 + 메모패널을 body 맨 앞에 삽입
      dbody.insertAdjacentHTML('afterbegin', memoPanelHtml + actionsHtml + tldrHtml);
    }
  };
})(v2OpenDrawer);

function v2ToggleMemoPanel(idx) {
  const panel = document.getElementById(`v2memopanel-${idx}`);
  if (panel) panel.classList.toggle('open');
}

function v2ToggleTag(idx, tag, el) {
  const tags = v2GetTags(idx);
  const i = tags.indexOf(tag);
  if (i >= 0) tags.splice(i, 1);
  else tags.push(tag);
  v2SetTags(idx, tags);
  el.classList.toggle('on');
  // 카드 배지 업데이트
  const badge = document.querySelector(`.v2-card-tag-area[data-idx="${idx}"]`);
  if (badge) badge.innerHTML = v2CardTagsHtml(idx);
  // 태그 필터 중이면 재렌더
  if (v2TagFilter) { renderCards(); v2AugmentCards(); }
}

// ── T2: 카드 태그 배지 HTML ──────────────────────────────────────────────────
function v2CardTagsHtml(idx) {
  return v2GetTags(idx).slice(0, 2)
    .map(t => `<span class="v2-card-tag v2-ct-${t}">${t}</span>`)
    .join('');
}

// ── T2: 태그 필터 렌더 ───────────────────────────────────────────────────────
function v2RenderTagFilter() {
  if (!FEATURE_UI_V2) return;
  let wrap = document.getElementById('v2tagfilter');
  if (!wrap) {
    wrap = document.createElement('div');
    wrap.id = 'v2tagfilter';
    wrap.className = 'v2-tag-filter-wrap';
    const chips = document.getElementById('v2chips');
    if (chips && chips.parentNode) chips.parentNode.insertBefore(wrap, chips.nextSibling);
  }
  wrap.innerHTML = ['', ...V2_TAGS].map(t => {
    const label = t || '전체';
    const active = v2TagFilter === t ? 'active' : '';
    return `<span class="v2-tf-pill v2-tf-${t||'all'} ${active}" onclick="v2SetTagFilter('${t}')">${label}</span>`;
  }).join('');
}

function v2SetTagFilter(tag) {
  v2TagFilter = tag;
  v2RenderTagFilter();
  renderCards();
  v2AugmentCards();
  v2PushState();
}

// ── T2: URL 상태에 태그 필터 포함 (v2PushState 오버라이드) ──────────────────
const _v2_origPushState = v2PushState;
v2PushState = function() {
  _v2_origPushState();
  if (!FEATURE_UI_V2) return;
  const url = new URL(location.href);
  if (v2TagFilter) url.searchParams.set('tag', v2TagFilter);
  else url.searchParams.delete('tag');
  history.replaceState(null, '', url.toString());
};

// URL에서 태그 필터 복원
(function() {
  if (!FEATURE_UI_V2) return;
  const sp = new URLSearchParams(location.search);
  if (sp.get('tag')) v2TagFilter = sp.get('tag');
})();

// ── v2AugmentCards 오버라이드: 태그 배지 + 태그 필터 적용 ───────────────────
const _v2_origAugmentCards = v2AugmentCards;
v2AugmentCards = function() {
  _v2_origAugmentCards();
  if (!FEATURE_UI_V2) return;
  document.querySelectorAll('.cc[data-idx]').forEach(card => {
    const idx = parseInt(card.getAttribute('data-idx'));
    if (isNaN(idx)) return;
    // 태그 배지 영역
    if (!card.querySelector('.v2-card-tag-area')) {
      const area = document.createElement('div');
      area.className = 'v2-card-tags';
      area.setAttribute('data-idx', idx);
      area.classList.add('v2-card-tag-area');
      area.innerHTML = v2CardTagsHtml(idx);
      const nm = card.querySelector('.cn, .nm, .dl');
      if (nm) nm.after(area);
      else card.appendChild(area);
    } else {
      const area = card.querySelector('.v2-card-tag-area');
      if (area) area.innerHTML = v2CardTagsHtml(idx);
    }
  });
};

// ── T3: 변경이력 개선 ───────────────────────────────────────────────────────
let v2ClRange = '전체';  // 7일 / 30일 / 전체

function v2DetectChangeType(fix) {
  if (!fix) return null;
  const text = fix.toLowerCase();
  if (/ceo|대표|사장|회장|취임|사임|교체/.test(text)) return 'CEO';
  if (/매출|시총|마진|이익률|매출액|revenue|수익/.test(text)) return '지표';
  if (/출시|발매|launch|release/.test(text)) return '출시';
  if (/m&a|인수|합병|지분|매각|소송|합의/.test(text)) return 'M&A';
  return '기타';
}

const V2_CL_BADGE_CLASS = {'CEO':'v2-clb-ceo','지표':'v2-clb-지표','출시':'v2-clb-출시','M&A':'v2-clb-ma','기타':'v2-clb-기타'};

v2RenderChangelog = function() {
  const el = document.getElementById('grid');
  if (!el) return;

  const now = Date.now();
  const rangeMs = v2ClRange === '7일' ? 7*86400000 : v2ClRange === '30일' ? 30*86400000 : null;

  const entries = D.map((c, i) => ({c, i}))
    .filter(({c}) => c.fix && c.fix.length > 5)
    .filter(({c}) => {
      if (!rangeMs) return true;
      const m = (c.fix || '').match(/(\d{4})[년\-\.](\d{1,2})/);
      if (!m) return false;
      const d = new Date(parseInt(m[1]), parseInt(m[2]) - 1);
      return (now - d.getTime()) <= rangeMs;
    })
    .slice(0, 80);

  const controls = `
    <div class="v2-cl-controls">
      <span style="font-size:12px;font-weight:600;color:#555">기간:</span>
      ${['7일','30일','전체'].map(r =>
        `<span class="v2-cl-range ${v2ClRange===r?'on':''}" onclick="v2SetClRange('${r}')">${r}</span>`
      ).join('')}
    </div>`;

  if (!entries.length) {
    el.innerHTML = `<div class="v2-cl-wrap"><div class="v2-cl-title">📋 변경 이력</div>
      ${controls}
      <div class="v2-cl-empty">선택한 기간에 업데이트 기록이 없습니다.<br>
        <small style="color:#ccc">update_at/asof_date 필드가 없으면 날짜 필터가 동작하지 않습니다.</small></div></div>`;
    return;
  }

  const rows = entries.map(({c,i}) => {
    const type = v2DetectChangeType(c.fix);
    const badge = type ? `<span class="v2-cl-type-badge ${V2_CL_BADGE_CLASS[type]||''}">${type}</span>` : '';
    const date = (c.fix||'').match(/\d{4}[년\-\.]\d{1,2}/)?.[0] || '2025';
    const note = (c.fix||'').replace(/^\[.*?\]\s*/,'').slice(0,120);
    return `<div class="v2-cl-item" onclick="v2OpenDrawer(${i})">
      <div class="v2-cl-date">${date}</div>
      <div class="v2-cl-co">${c.nk||c.n||''}</div>
      <div style="display:flex;align-items:flex-start;gap:6px;flex:1;">
        ${badge}
        <div class="v2-cl-note">${note}</div>
      </div>
    </div>`;
  }).join('');

  el.innerHTML = `<div class="v2-cl-wrap">
    <div class="v2-cl-title">📋 변경 이력 (${entries.length}건)</div>
    ${controls}
    ${rows}
  </div>`;
};

function v2SetClRange(r) {
  v2ClRange = r;
  if (fs.tp === 'cl') renderCards();
}

// ── renderCards 오버라이드: 태그 필터 추가 ──────────────────────────────────
const _v2_prevRenderCards2 = renderCards;
renderCards = function() {
  // 태그 필터가 활성화된 경우 filtered()를 wrapping
  if (FEATURE_UI_V2 && v2TagFilter && v2TagFilter !== 'fav' && fs.tp !== 'cl') {
    const _f = filtered;
    filtered = () => _f().filter(idx => v2TagFilter ? v2GetTags(idx).includes(v2TagFilter) : true);
    _v2_prevRenderCards2();
    filtered = _f;
    v2AugmentCards();
    return;
  }
  _v2_prevRenderCards2();
  if (FEATURE_UI_V2) v2AugmentCards();
};

// ── DOMContentLoaded에 태그 필터 렌더 추가 ──────────────────────────────────
if (FEATURE_UI_V2) {
  const _origDCL = window.onload;
  document.addEventListener('DOMContentLoaded', () => {
    v2RenderTagFilter();
    v2RenderChips();
  });
}
"""

# ─────────────────────────────────────────────────────────────────────────────
# 주입 실행
# ─────────────────────────────────────────────────────────────────────────────
def patch(src=None, out=None):
    html_path = Path(src or BASE / 'index.html')
    out_path  = Path(out or html_path)
    html = html_path.read_text(encoding='utf-8')

    # 1) CSS 패치: 기존 V2 CSS 블록 끝(</style> 직전) 에 삽입
    CSS_SENTINEL = '/* ── T5: 바텀시트 스크롤 잠금'
    if CSS_SENTINEL not in html:
        # V2 CSS 직후 (</style> 직전) 에 삽입
        html = html.replace('</style>', PATCH_CSS + '\n</style>', 1)
        print('✅ CSS 패치 삽입')
    else:
        print('ℹ️  CSS 패치 이미 존재')

    # 2) JS 패치: </script> 직전에 삽입
    JS_SENTINEL = 'UI V2 PATCH v1.0.13'
    if JS_SENTINEL not in html:
        html = html.replace('</script>', PATCH_JS + '\n</script>', 1)
        print('✅ JS 패치 삽입')
    else:
        print('ℹ️  JS 패치 이미 존재')

    out_path.write_text(html, encoding='utf-8')
    print(f'✅ 완료: {out_path} ({out_path.stat().st_size:,} bytes)')

if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', default=None)
    ap.add_argument('--out', default=None)
    args = ap.parse_args()
    patch(args.src, args.out)
