#!/usr/bin/env python3
"""
patch_korean_only.py — V2 UI 한국어 전용 강제 패치

1. sanitizeToKorean() 헬퍼
2. 모든 정적 라벨 한국어 검증/맵
3. TL;DR/Changelog 파생 문자열에 sanitize 적용
4. Drawer에 '원문' 필드 명시적 레이블 추가
"""
from pathlib import Path

BASE = Path(__file__).parent.parent

PATCH_CSS = """
/* ── 한국어 전용: 원문 필드 스타일 ──────────────────────────────────────── */
.v2-gentext{font-size:11px;color:#aaa;letter-spacing:.3px;font-style:italic;}
.v2-orig-field{font-size:12px;color:#999;line-height:1.5;}
"""

PATCH_JS = r"""
// ═══════════════════════════════════════════════════════════════════════════
// 한국어 전용 (Korean-only display) — HARD CONSTRAINT
// ═══════════════════════════════════════════════════════════════════════════

// 일본어 감지 regex (히라가나 + 가타카나 + CJK 한자)
const JP_REGEX = /[぀-ヿ㐀-䶿一-鿿]/;

/**
 * sanitizeToKorean(text)
 * - 파생 문자열(TL;DR, 변경이력 요약)에서 일본어 문자를 제거한다.
 * - 결과가 비면 '정보 확인 필요'를 반환한다.
 * - 영문·숫자·기호는 유지한다.
 */
function sanitizeToKorean(text) {
  if (!text) return '';
  // 일본어 제거 (한자 포함)
  let cleaned = String(text).replace(/[぀-ヿ㐀-䶿一-鿿]+/g, ' ');
  // 이중 공백 정리
  cleaned = cleaned.replace(/\s{2,}/g, ' ').trim();
  return cleaned || '정보 확인 필요';
}

/**
 * hasJapanese(text)
 * UI 문자열에 일본어가 포함되는지 검사한다.
 */
function hasJapanese(text) {
  return JP_REGEX.test(text || '');
}

// ── UI 정적 레이블 검증 맵 (모두 한국어여야 함) ────────────────────────────
const V2_UI_LABELS = {
  // 탭
  tabFav:        '★ 즐겨찾기',
  tabCl:         '📋 변경이력',
  // 드로어
  drawerClose:   '✕',
  tldrPoint:     '포인트',
  tldrRisk:      '리스크',
  actMemo:       '📝 메모/태그',
  actSrc:        '🔗 출처 열기',
  secTt:         '주요 타이틀',
  secPr:         '장점',
  secCn:         '단점/리스크',
  secSh:         '주주구조',
  secRep:        '대표이사',
  secConf:       '신뢰도',
  secAsof:       '기준 시점',
  secOrig:       '원문 (Original)',
  secFix:        '최근 업데이트',
  srcLabel:      '📌 출처',
  // 필터
  filterAll:     '전체',
  // 태그
  tagAll:        '전체',
  // 변경이력
  clTitle:       '📋 변경이력',
  clEmpty:       '업데이트 기록 없음',
  clPeriod:      '기간:',
  // 기타
  confWarn:      '출처/시점 확인 필요',
  memoPlaceholder: '메모 입력...',
  favEmpty:      '즐겨찾기한 기업이 없습니다.',
  infoCheck:     '정보 확인 필요',
};

// 정적 레이블에 일본어 없음 확인 (개발 시 콘솔 경고)
if (FEATURE_UI_V2 && typeof console !== 'undefined') {
  Object.entries(V2_UI_LABELS).forEach(([k, v]) => {
    if (hasJapanese(v)) {
      console.warn(`[V2 한국어 전용] 레이블 '${k}' 에 일본어 포함됨:`, v);
    }
  });
}

// ── TL;DR 파생 함수 오버라이드 (sanitize 적용) ──────────────────────────────
const _v2_rawDeriveTldr = v2DeriveTldr;
v2DeriveTldr = function(c, idx) {
  const raw = _v2_rawDeriveTldr(c, idx);
  return {
    point: sanitizeToKorean(raw.point),
    risk:  sanitizeToKorean(raw.risk),
  };
};

// ── 변경이력 노트 sanitize (v2RenderChangelog 오버라이드) ───────────────────
const _v2_rawChangelog = v2RenderChangelog;
v2RenderChangelog = function() {
  // grid 렌더 전에 sanitize를 적용하는 wrapper
  // v2RenderChangelog 내부에서 직접 DOM을 그리므로,
  // 렌더 후 note 텍스트를 후처리한다.
  _v2_rawChangelog();
  if (!FEATURE_UI_V2) return;
  document.querySelectorAll('.v2-cl-note').forEach(el => {
    if (hasJapanese(el.textContent)) {
      el.textContent = sanitizeToKorean(el.textContent);
    }
  });
};

// ── Drawer 원문 필드 주입 (v2OpenDrawer 오버라이드) ─────────────────────────
const _v2_preKoOpenDrawer = v2OpenDrawer;
v2OpenDrawer = function(idx) {
  _v2_preKoOpenDrawer(idx);
  const c = D[idx];
  if (!c || !FEATURE_UI_V2) return;

  const dbody = document.getElementById('v2dbody');
  if (!dbody) return;

  // 일본어 원문 회사명이 있으면 '원문' 필드 표시
  const origName = c.n || '';
  if (origName && hasJapanese(origName)) {
    // 이미 추가됐으면 skip
    if (!dbody.querySelector('.v2-orig-block')) {
      const origHtml = `<div class="v2-dsec v2-orig-block">
        <div class="v2-dsl v2-gentext">${V2_UI_LABELS.secOrig}</div>
        <div class="v2-orig-field">${origName}</div>
      </div>`;
      dbody.insertAdjacentHTML('beforeend', origHtml);
    }
  }

  // Drawer 내 일본어 누출 체크 (원문 섹션 제외)
  setTimeout(() => {
    if (!dbody) return;
    const origBlock = dbody.querySelector('.v2-orig-block');
    // 원문 블록을 임시 제거하고 체크
    const origClone = origBlock ? origBlock.cloneNode(true) : null;
    if (origBlock) origBlock.remove();

    const allText = dbody.textContent || '';
    if (hasJapanese(allText)) {
      // 일본어 포함된 텍스트 노드 sanitize
      sanitizeDomJapanese(dbody);
    }

    // 원문 블록 복원
    if (origClone) dbody.appendChild(origClone);
  }, 0);
};

/**
 * sanitizeDomJapanese(container)
 * container 내의 텍스트 노드에서 일본어를 제거한다.
 * 원문 필드(.v2-orig-field, .v2-orig-block)는 건드리지 않는다.
 */
function sanitizeDomJapanese(container) {
  const walker = document.createTreeWalker(
    container, NodeFilter.SHOW_TEXT, {
      acceptNode(node) {
        // 원문 블록 내 텍스트는 건너뜀
        let p = node.parentElement;
        while (p && p !== container) {
          if (p.classList && (p.classList.contains('v2-orig-block') ||
                               p.classList.contains('v2-orig-field'))) {
            return NodeFilter.FILTER_REJECT;
          }
          p = p.parentElement;
        }
        return NodeFilter.FILTER_ACCEPT;
      }
    }
  );
  const nodes = [];
  let n;
  while ((n = walker.nextNode())) nodes.push(n);
  nodes.forEach(textNode => {
    if (hasJapanese(textNode.textContent)) {
      textNode.textContent = sanitizeToKorean(textNode.textContent);
    }
  });
}
"""

def patch(src=None, out=None):
    html_path = Path(src or BASE / 'index.html')
    out_path  = Path(out or html_path)
    html = html_path.read_text(encoding='utf-8')

    CSS_SENTINEL = '/* ── 한국어 전용: 원문 필드 스타일'
    if CSS_SENTINEL not in html:
        html = html.replace('</style>', PATCH_CSS + '\n</style>', 1)
        print('✅ 한국어 전용 CSS 삽입')
    else:
        print('ℹ️  CSS 이미 존재')

    JS_SENTINEL = '한국어 전용 (Korean-only display)'
    if JS_SENTINEL not in html:
        html = html.replace('</script>', PATCH_JS + '\n</script>', 1)
        print('✅ 한국어 전용 JS 삽입')
    else:
        print('ℹ️  JS 이미 존재')

    out_path.write_text(html, encoding='utf-8')
    print(f'✅ 완료: {out_path.stat().st_size:,} bytes')

if __name__ == '__main__':
    patch()
