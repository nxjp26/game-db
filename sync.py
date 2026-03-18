#!/usr/bin/env python3
"""
sync.py — Notion Database → index.html 동기화 스크립트

사용법:
  python3 sync.py              # Notion → index.html 갱신 (push 없음)
  python3 sync.py --push       # Notion → index.html 갱신 + git push
  python3 sync.py --import     # 기존 D[] 데이터를 Notion DB로 일괄 업로드
  python3 sync.py --dry-run    # 변환 결과만 출력 (파일 수정 없음)

환경변수 (또는 .env 파일):
  NOTION_TOKEN   = secret_xxxx...
  NOTION_DB_ID   = xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
"""

import os, re, json, sys, subprocess
from pathlib import Path

# ── 환경변수 로드 ────────────────────────────────────────────────────────────
def load_env():
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        for line in env_path.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip())

load_env()

NOTION_TOKEN = os.environ.get('NOTION_TOKEN', '')
NOTION_DB_ID  = os.environ.get('NOTION_DB_ID',  '')
HTML_FILE     = Path(__file__).parent / 'index.html'

if not NOTION_TOKEN or not NOTION_DB_ID:
    print('❌ NOTION_TOKEN 또는 NOTION_DB_ID가 설정되지 않았습니다.')
    print('   .env 파일을 생성하거나 환경변수를 설정해주세요.')
    sys.exit(1)

# ── Notion 클라이언트 ────────────────────────────────────────────────────────
try:
    from notion_client import Client
except ImportError:
    print('❌ notion-client가 설치되지 않았습니다. 아래 명령어를 실행하세요:')
    print('   pip3 install notion-client')
    sys.exit(1)

notion = Client(auth=NOTION_TOKEN, notion_version="2022-06-28")

# ── Notion 컬럼명 → D[] 필드명 매핑 ─────────────────────────────────────────
# Notion 컬럼명 (왼쪽) → D[] 객체 필드명 (오른쪽)
COL_MAP = {
    '기업명(일본어)': 'n',
    '기업명(한국어)': 'nk',
    '국가':         'ct',
    '업종':         'bz',
    '장르':         'gn',
    'MA접근':       'ma',
    '딜형태':       'iv',
    '시총_억엔':    'mk',    # 억엔 → × 1e8
    '매출_억엔':    'rv',    # 억엔 → × 1e8
    '이익률':       'mg',
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
    '순서':         '_order',
}

# 억엔 × 1e8 변환 대상 필드
MONEY_FIELDS = {'mk', 'rv'}

# ── Notion DB 전체 조회 ──────────────────────────────────────────────────────
def fetch_all_pages():
    pages = []
    cursor = None
    while True:
        params = {'database_id': NOTION_DB_ID, 'page_size': 100}
        if cursor:
            params['start_cursor'] = cursor
        res = notion.databases.query(**params)
        pages.extend(res['results'])
        if not res.get('has_more'):
            break
        cursor = res['next_cursor']
    return pages

# ── Notion 속성 값 추출 ──────────────────────────────────────────────────────
def get_prop(props, name):
    prop = props.get(name)
    if prop is None:
        return None
    t = prop['type']
    if t == 'title':
        parts = prop['title']
        return ''.join(p['plain_text'] for p in parts) if parts else None
    if t == 'rich_text':
        parts = prop['rich_text']
        return ''.join(p['plain_text'] for p in parts) if parts else None
    if t == 'select':
        sel = prop['select']
        return sel['name'] if sel else None
    if t == 'number':
        return prop['number']  # float or None
    if t == 'checkbox':
        return prop['checkbox']  # bool
    return None

# ── Notion 페이지 → D[] 객체 변환 ────────────────────────────────────────────
def page_to_company(page):
    props = page['properties']
    company = {}
    for col, field in COL_MAP.items():
        val = get_prop(props, col)
        if val is None:
            company[field] = None
        elif field in MONEY_FIELDS and val is not None:
            # 억엔 단위 숫자 → 엔 단위 (× 1e8)
            company[field] = val * 1e8
        else:
            company[field] = val
    return company

# ── D[] 객체를 JS 표현 문자열로 직렬화 ──────────────────────────────────────
def js_value(v, field=''):
    if v is None:
        return 'null'
    if isinstance(v, bool):
        return 'true' if v else 'false'
    if isinstance(v, float):
        # 억엔 단위로 변환된 수치는 과학적 표기법으로
        if v == 0:
            return '0'
        # 적절한 정밀도의 과학적 표기법
        exp = 0
        x = v
        while abs(x) >= 10:
            x /= 10
            exp += 1
        while abs(x) < 1 and x != 0:
            x *= 10
            exp -= 1
        # 소수점 2자리까지
        mantissa = round(v / (10**exp), 2)
        if mantissa == int(mantissa):
            return f'{int(mantissa)}e{exp}'
        return f'{mantissa}e{exp}'
    if isinstance(v, int):
        return str(v)
    # 문자열: 특수문자 이스케이프
    escaped = (str(v)
               .replace('\\', '\\\\')
               .replace("'", "\\'")
               .replace('\n', '\\n')
               .replace('\r', ''))
    return f"'{escaped}'"

def company_to_js(c):
    fields_order = ['n','nk','ct','bz','gn','ma','mk','rv','mg',
                    'rep','tt','ch','pr','cn','sh','src','ip','emp','iv','mr','fix']
    parts = []
    for f in fields_order:
        v = c.get(f)
        parts.append(f"{f}:{js_value(v, f)}")
    return '  {' + ','.join(parts) + '}'

# ── index.html D[] 블록 교체 ─────────────────────────────────────────────────
def update_html(companies):
    html = HTML_FILE.read_text(encoding='utf-8')

    # "const D=[" 부터 "];" 까지 교체
    new_d = 'const D=[\n'
    new_d += ',\n'.join(company_to_js(c) for c in companies)
    new_d += '\n];'

    # 정규식으로 기존 D[] 블록 탐지 및 교체
    pattern = r'const D=\[[\s\S]*?\];'
    if not re.search(pattern, html):
        print('❌ index.html에서 "const D=[...];" 블록을 찾을 수 없습니다.')
        sys.exit(1)

    new_html = re.sub(pattern, new_d, html)
    HTML_FILE.write_text(new_html, encoding='utf-8')

# ── git push ─────────────────────────────────────────────────────────────────
def git_push():
    repo_dir = HTML_FILE.parent
    cmds = [
        ['git', '-C', str(repo_dir), 'add', 'index.html'],
        ['git', '-C', str(repo_dir), 'commit', '-m',
         f'데이터 업데이트 (sync.py)'],
        ['git', '-C', str(repo_dir), 'push'],
    ]
    for cmd in cmds:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            # commit 시 "nothing to commit"은 정상
            if 'nothing to commit' in result.stdout + result.stderr:
                print('ℹ️  변경 사항 없음 (이미 최신 상태)')
                return
            print(f'❌ git 오류: {result.stderr.strip()}')
            sys.exit(1)
    print('✅ git push 완료')

# ── Notion DB로 기존 D[] 데이터 일괄 업로드 ──────────────────────────────────
def import_to_notion():
    """기존 index.html의 D[] 배열을 파싱해서 Notion DB에 업로드"""
    html = HTML_FILE.read_text(encoding='utf-8')

    # D[] 블록 추출
    match = re.search(r'const D=\[([\s\S]*?)\];', html)
    if not match:
        print('❌ index.html에서 D[] 블록을 찾을 수 없습니다.')
        sys.exit(1)

    # 간단한 파싱: 각 기업 줄에서 JSON-like 객체 추출
    # 실제 파싱은 eval 불가하므로 정규식으로 각 필드 추출
    d_block = match.group(1)
    # 각 {n:...,nk:..., ...} 블록 추출
    obj_pattern = re.compile(r'\{([^{}]+)\}')
    companies_raw = obj_pattern.findall(d_block)

    print(f'📦 {len(companies_raw)}개 기업 데이터를 Notion DB에 업로드합니다...')

    # 역방향 매핑: field → col
    FIELD_TO_COL = {v: k for k, v in COL_MAP.items()}

    order = 1
    success = 0
    for raw in companies_raw:
        # 필드:값 파싱
        company = {}
        # 문자열 값 (작은따옴표)
        for m in re.finditer(r"(\w+):'([^']*)'", raw):
            company[m.group(1)] = m.group(2)
        # 숫자/null/bool 값
        for m in re.finditer(r"(\w+):([\d.e+\-]+|null|true|false)(?=[,}])", raw):
            k, v = m.group(1), m.group(2)
            if k not in company:
                if v == 'null':
                    company[k] = None
                elif v == 'true':
                    company[k] = True
                elif v == 'false':
                    company[k] = False
                else:
                    try:
                        company[k] = float(v)
                    except:
                        company[k] = v

        # Notion 속성 구성
        properties = {}

        # Title (기업명 일본어)
        n_val = company.get('n', '')
        properties['기업명(일본어)'] = {
            'title': [{'text': {'content': n_val or ''}}]
        }

        def text_prop(val):
            return {'rich_text': [{'text': {'content': str(val or '')}}]}

        def select_prop(val):
            return {'select': {'name': str(val)} if val else None} if val else {'select': None}

        def number_prop(val):
            if val is None: return {'number': None}
            return {'number': float(val)}

        col_builders = {
            '기업명(한국어)': lambda v: text_prop(v),
            '국가':         lambda v: select_prop(v),
            '업종':         lambda v: select_prop(v),
            '장르':         lambda v: select_prop(v),
            'MA접근':       lambda v: select_prop(v),
            '딜형태':       lambda v: select_prop(v),
            '시총_억엔':    lambda v: number_prop(round(v / 1e8, 2) if v else None),
            '매출_억엔':    lambda v: number_prop(round(v / 1e8, 2) if v else None),
            '이익률':       lambda v: number_prop(v),
            '직원수':       lambda v: number_prop(v),
            '대표이사':     lambda v: text_prop(v),
            '주요타이틀':   lambda v: text_prop(v),
            '기업특징':     lambda v: text_prop(v),
            '장점':         lambda v: text_prop(v),
            '단점리스크':   lambda v: text_prop(v),
            '주주구조':     lambda v: text_prop(v),
            'MA판단근거':   lambda v: text_prop(v),
            '자체IP':       lambda v: {'checkbox': bool(v)},
            '소스':         lambda v: select_prop(v),
            '수정메모':     lambda v: text_prop(v),
            '순서':         lambda v: number_prop(order),
        }

        for col, builder in col_builders.items():
            field = COL_MAP.get(col)
            val = company.get(field) if field else None
            try:
                prop = builder(val)
                if prop is not None:
                    properties[col] = prop
            except Exception:
                pass

        try:
            notion.pages.create(
                parent={'database_id': NOTION_DB_ID},
                properties=properties
            )
            success += 1
            nk = company.get('nk') or company.get('n', '?')
            print(f'  ✅ [{order:3d}] {nk}')
        except Exception as e:
            nk = company.get('nk') or company.get('n', '?')
            print(f'  ❌ [{order:3d}] {nk}: {e}')

        order += 1

    print(f'\n📊 완료: {success}/{len(companies_raw)}개 업로드 성공')

# ── 메인 ─────────────────────────────────────────────────────────────────────
def main():
    args = sys.argv[1:]

    # --import: D[] → Notion DB
    if '--import' in args:
        print('📤 기존 index.html 데이터를 Notion DB로 업로드합니다...')
        import_to_notion()
        return

    # --dry-run: 미리보기만
    dry = '--dry-run' in args
    push = '--push' in args

    print('📥 Notion DB에서 기업 데이터를 가져오는 중...')
    pages = fetch_all_pages()
    print(f'   {len(pages)}개 기업 로드 완료')

    companies = [page_to_company(p) for p in pages]

    # _order 기준 정렬 (없으면 뒤로)
    companies.sort(key=lambda c: (c.get('_order') or 9999))

    # _order 필드는 D[]에 포함하지 않음 (내부 정렬용)
    for c in companies:
        c.pop('_order', None)

    if dry:
        print('\n--- D[] 미리보기 (처음 3개) ---')
        for c in companies[:3]:
            print(company_to_js(c))
        print(f'...\n총 {len(companies)}개')
        return

    update_html(companies)
    print(f'✅ index.html D[] 배열 업데이트 완료 ({len(companies)}개 기업)')

    if push:
        print('📤 GitHub에 push 중...')
        git_push()
        print('🌐 약 30~60초 후 공개 URL에 반영됩니다.')

if __name__ == '__main__':
    main()
