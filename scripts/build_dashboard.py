#!/usr/bin/env python3
"""
build_dashboard.py — CSV → index.html 빌드 스크립트

사용법:
  python3 scripts/build_dashboard.py \\
      --csv data/기업DB.csv \\
      --template index.html \\
      --out index.html

  # 드라이런(파일 수정 없음, 출력만):
  python3 scripts/build_dashboard.py --csv data/기업DB.csv --template index.html --dry-run

주의:
  - 기존 sync.py(Notion 기반)와 동일한 const D=[...] 포맷을 생성합니다.
  - mk/rv 컬럼은 CSV 단위(億円)에서 엔(×1e8) 단위로 변환됩니다.
  - 문자열 이스케이프 로직은 sync.py의 js_value()와 동일합니다.
"""

import argparse, re, sys, csv, math
from pathlib import Path

# ── CSV 컬럼 → D[] 필드 매핑 ─────────────────────────────────────────────────
COL_MAP = {
    '기업명(일본어)': 'n',
    '기업명(한국어)': 'nk',
    '국가':         'ct',
    '업종':         'bz',
    '장르':         'gn',
    'MA접근':       'ma',
    '딜형태':       'iv',
    '시총_억엔':    'mk',   # 억엔 → ×1e8
    '매출_억엔':    'rv',   # 억엔 → ×1e8
    '이익률(%)':    'mg',
    '직원수':       'emp',
    '대표이사':     'rep',
    '주요타이틀':   'tt',
    '기업특징':     'ch',
    '장점':         'pr',
    '단점리스크':   'cn',
    '주주구조':     'sh',
    'MA판단근거':   'mr',
    '자체IP':       'ip',
    '소스':         'src',
    '수정메모':     'fix',
    '분류':         'type',
    '순서':         '_order',
}

MONEY_FIELDS = {'mk', 'rv'}

FIELDS_ORDER = ['n','nk','ct','bz','gn','ma','mk','rv','mg',
                'rep','tt','ch','pr','cn','sh','src','ip','emp','iv','mr','fix']


# ── JS 값 직렬화 (sync.py와 동일 로직) ───────────────────────────────────────
def js_value(v):
    if v is None:
        return 'null'
    if isinstance(v, bool):
        return 'true' if v else 'false'
    if isinstance(v, float):
        if v == 0:
            return '0'
        exp = 0
        x = v
        while abs(x) >= 10:
            x /= 10
            exp += 1
        while abs(x) < 1 and x != 0:
            x *= 10
            exp -= 1
        mantissa = round(v / (10 ** exp), 2)
        if mantissa == int(mantissa):
            return f'{int(mantissa)}e{exp}'
        return f'{mantissa}e{exp}'
    if isinstance(v, int):
        return str(v)
    escaped = (str(v)
               .replace('\\', '\\\\')
               .replace("'", "\\'")
               .replace('\n', '\\n')
               .replace('\r', ''))
    return f"'{escaped}'"


def company_to_js(c):
    parts = []
    for f in FIELDS_ORDER:
        v = c.get(f)
        parts.append(f"{f}:{js_value(v)}")
    tp = c.get('type')
    if tp == 'accel':
        parts.append("type:'accel'")
    return '  {' + ','.join(parts) + '}'


# ── CSV 행 → company dict ────────────────────────────────────────────────────
def _to_num(s, as_int=False):
    """문자열 → 숫자 or None.
    정수값(소수점 없음)은 항상 int로 반환 — Notion API와 동일한 동작.
    (Notion은 소수점 없는 수를 Python int로 반환하므로 js_value가 '44'로 직렬화)
    """
    if not s or str(s).strip() in ('', 'nan', 'None', '-'):
        return None
    s = str(s).strip()
    try:
        f = float(s)
        # 정수값이면 int로 반환 (js_value에서 과학적 표기 방지)
        if f == int(f) and not math.isinf(f):
            return int(f)
        return f
    except ValueError:
        return None


def _to_bool(s):
    """Y/N/True/False → bool or None"""
    if not s or str(s).strip() in ('', 'nan', 'None'):
        return None
    return str(s).strip().upper() in ('Y', 'YES', 'TRUE', '1', 'T')


def row_to_company(row):
    company = {}
    for col, field in COL_MAP.items():
        raw = row.get(col, '').strip() if row.get(col) else ''
        if not raw or raw in ('nan', 'None'):
            company[field] = None
            continue

        if field in MONEY_FIELDS:
            num = _to_num(raw)
            company[field] = num * 1e8 if num is not None else None
        elif field in ('emp', 'mg'):
            company[field] = _to_num(raw)
        elif field == 'ip':
            company[field] = _to_bool(raw)
        else:
            company[field] = raw if raw else None

    return company


# ── D[] 블록 생성 ─────────────────────────────────────────────────────────────
def build_d_block(companies):
    new_d = 'const D=[\n'
    new_d += ',\n'.join(company_to_js(c) for c in companies)
    new_d += '\n];'
    return new_d


# ── HTML 주입 (lambda로 re.sub 버그 방지) ────────────────────────────────────
def inject_into_html(html, d_block):
    pattern = r'const D=\[[\s\S]*?\];'
    if not re.search(pattern, html):
        print('❌ index.html에서 "const D=[...];" 블록을 찾을 수 없습니다.')
        sys.exit(1)
    return re.sub(pattern, lambda m: d_block, html)


# ── main ─────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description='CSV → dashboard HTML 빌드')
    ap.add_argument('--csv',      required=True, help='입력 CSV 파일 경로')
    ap.add_argument('--template', required=True, help='HTML 템플릿 파일 경로')
    ap.add_argument('--out',      default=None,  help='출력 파일 경로 (기본: --template과 동일)')
    ap.add_argument('--dry-run',  action='store_true', help='파일 수정 없이 미리보기만')
    args = ap.parse_args()

    csv_path      = Path(args.csv)
    template_path = Path(args.template)
    out_path      = Path(args.out) if args.out else template_path

    if not csv_path.exists():
        print(f'❌ CSV 파일 없음: {csv_path}')
        sys.exit(1)
    if not template_path.exists():
        print(f'❌ 템플릿 파일 없음: {template_path}')
        sys.exit(1)

    # CSV 읽기
    with open(csv_path, encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))

    companies = [row_to_company(r) for r in rows]

    # 순서 정렬
    companies.sort(key=lambda c: float(c.get('_order') or 9999)
                   if c.get('_order') is not None else 9999)
    for c in companies:
        c.pop('_order', None)

    d_block = build_d_block(companies)

    if args.dry_run:
        print(f'✅ 드라이런: {len(companies)}개 기업 처리 완료')
        print('--- const D=[] 미리보기 (처음 2개) ---')
        lines = d_block.split('\n')
        print('\n'.join(lines[:4]))
        print('...')
        return

    # HTML 주입
    html = template_path.read_text(encoding='utf-8')
    new_html = inject_into_html(html, d_block)

    out_path.write_text(new_html, encoding='utf-8')
    size_kb = out_path.stat().st_size // 1024
    print(f'✅ 빌드 완료: {out_path} ({len(companies)}개 기업, {size_kb}KB)')


if __name__ == '__main__':
    main()
