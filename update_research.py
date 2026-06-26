#!/usr/bin/env python3
"""
update_research.py — 리서치 결과를 Notion DB에 업데이트

수집된 _result_batch*.json 파일들을 읽어 Notion DB의 해당 기업 페이지를 업데이트합니다.
업데이트 항목: ch(기업특징), pr(장점), cn(단점리스크), sh(주주구조), tt(주요타이틀),
              rep(대표이사), emp(직원수), mg(이익률), mk(시총), rv(매출)
"""

import os, json, re, time, warnings, httpx
warnings.filterwarnings('ignore')
from pathlib import Path
from notion_client import Client

# ── 환경변수 로드
for line in (Path(__file__).parent / '.env').read_text(encoding='utf-8').splitlines():
    line = line.strip()
    if line and not line.startswith('#') and '=' in line:
        k, v = line.split('=', 1)
        os.environ[k.strip()] = v.strip()

PROXY = 'https://notion-pat-proxy.nexon.co.kr'
notion = Client(
    options={'auth': os.environ['NOTION_TOKEN'], 'notion_version': '2022-06-28', 'base_url': PROXY},
    client=httpx.Client(verify=False)
)
DB_ID = os.environ['NOTION_DB_ID']

# ── 전체 페이지 로드 (기업명(한국어) → page_id 매핑)
def load_all_pages():
    pages = {}
    cursor = None
    while True:
        params = {'database_id': DB_ID, 'page_size': 100}
        if cursor:
            params['start_cursor'] = cursor
        res = notion.databases.query(**params)
        for page in res['results']:
            props = page['properties']
            # 한국어 기업명
            nk_parts = props.get('기업명(한국어)', {}).get('rich_text', [])
            nk = ''.join(p['plain_text'] for p in nk_parts).strip()
            # 일본어 기업명
            n_parts = props.get('기업명(일본어)', {}).get('title', [])
            n = ''.join(p['plain_text'] for p in n_parts).strip()
            if nk:
                pages[nk] = page['id']
            if n:
                pages[n] = page['id']
        if not res.get('has_more'):
            break
        cursor = res['next_cursor']
    return pages

def text_prop(v):
    return {'rich_text': [{'text': {'content': str(v or '')[:2000]}}]}

def number_prop(v):
    if v is None:
        return {'number': None}
    try:
        return {'number': float(v)}
    except:
        return {'number': None}

def build_update_props(item):
    """리서치 결과 → Notion 업데이트 속성"""
    props = {}

    if item.get('ch'):
        props['기업특징'] = text_prop(item['ch'])
    if item.get('pr'):
        props['장점'] = text_prop(item['pr'])
    if item.get('cn'):
        props['단점리스크'] = text_prop(item['cn'])
    if item.get('sh'):
        props['주주구조'] = text_prop(item['sh'])
    if item.get('tt'):
        tt = item['tt']
        if isinstance(tt, list):
            tt = ', '.join(str(x) for x in tt)
        props['주요타이틀'] = text_prop(tt)
    if item.get('rep'):
        props['대표이사'] = text_prop(item['rep'])
    if item.get('mr'):
        props['MA판단근거'] = text_prop(item['mr'])
    if item.get('news'):
        # 수정메모에 최신 뉴스 저장
        props['수정메모'] = text_prop(f"[2025-2026 업데이트] {item['news']}")
    if item.get('emp') is not None:
        props['직원수'] = number_prop(item['emp'])
    if item.get('mg') is not None:
        props['이익률'] = number_prop(item['mg'])
    if item.get('mk_oku') is not None:
        # 億엔 → 엔 (×1e8)
        props['시총_억엔'] = number_prop(item['mk_oku'])
    if item.get('rv_oku') is not None:
        props['매출_억엔'] = number_prop(item['rv_oku'])

    return props

def normalize(name: str) -> str:
    """검색용 정규화"""
    return (name.strip()
            .replace('　', '').replace(' ', '')
            .replace('(', '').replace(')', '')
            .lower())

def find_page_id(item, pages):
    """nk 또는 n으로 페이지 ID 검색"""
    nk = item.get('nk', '')
    # 정확히 일치
    if nk in pages:
        return pages[nk]
    # 괄호 제거 후 검색
    nk_clean = re.sub(r'[\(\（].*?[\)\）]', '', nk).strip()
    if nk_clean in pages:
        return pages[nk_clean]
    # 정규화 후 검색
    nk_norm = normalize(nk)
    for k, pid in pages.items():
        if normalize(k) == nk_norm:
            return pid
    # 부분 일치
    for k, pid in pages.items():
        if nk_norm in normalize(k) or normalize(k) in nk_norm:
            return pid
    return None

def main():
    print('📥 Notion DB 페이지 목록 로드 중...')
    pages = load_all_pages()
    print(f'   {len(pages)}개 항목 로드 완료')

    # 배치 파일 로드
    batch_files = sorted(Path('.').glob('_result_batch*.json'))
    all_items = []
    for bf in batch_files:
        items = json.loads(bf.read_text(encoding='utf-8'))
        all_items.extend(items)
        print(f'   {bf.name}: {len(items)}개')

    print(f'\n📝 총 {len(all_items)}개 기업 업데이트 시작...\n')

    success = 0
    not_found = []
    failed = []

    for item in all_items:
        nk = item.get('nk', '?')
        page_id = find_page_id(item, pages)

        if not page_id:
            not_found.append(nk)
            print(f'  ⚠️  [{nk}] → DB에서 찾을 수 없음')
            continue

        props = build_update_props(item)
        if not props:
            print(f'  ℹ️  [{nk}] → 업데이트할 데이터 없음')
            continue

        try:
            notion.pages.update(page_id=page_id, properties=props)
            success += 1
            print(f'  ✅ [{nk}] → {len(props)}개 필드 업데이트')
            time.sleep(0.35)  # Rate limit 방지
        except Exception as e:
            failed.append((nk, str(e)[:80]))
            print(f'  ❌ [{nk}] → {str(e)[:80]}')
            time.sleep(1)

    print(f'\n📊 완료: {success}/{len(all_items)}개 성공')
    if not_found:
        print(f'⚠️  DB에서 못 찾은 기업 ({len(not_found)}개): {", ".join(not_found)}')
    if failed:
        print(f'❌ 업데이트 실패 ({len(failed)}개):')
        for nk, err in failed:
            print(f'   {nk}: {err}')

if __name__ == '__main__':
    main()
