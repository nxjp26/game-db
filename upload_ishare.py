#!/usr/bin/env python3
"""
upload_ishare.py — index.html을 iShare 웹호스팅에 업로드/갱신

사용법:
  python upload_ishare.py           # 자동: 첫 실행은 번들 생성, 이후는 파일 갱신
  python upload_ishare.py --new     # 강제로 새 번들 생성 (기존 상태 무시)
  python upload_ishare.py --status  # 현재 호스팅 상태 조회
"""

import sys, json, warnings
from pathlib import Path

warnings.filterwarnings('ignore')  # SSL 경고 억제

try:
    import httpx
except ImportError:
    print('❌ httpx가 없습니다: pip install httpx')
    sys.exit(1)

# ── 설정 ────────────────────────────────────────────────────────────────────
import os

def _load_env():
    envf = Path(__file__).parent / '.env'
    if envf.exists():
        for line in envf.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip())

_load_env()

ISHARE_BASE  = 'https://ishare-app.nexon.com'
TOKEN        = os.environ.get('ISHARE_TOKEN', '')
if not TOKEN:
    print('❌ ISHARE_TOKEN이 .env에 없습니다.')
    sys.exit(1)

BUNDLE_NAME  = 'nexon-jp-game-db'
SITE_URL     = 'jp-gamedb'
IS_PRIVATE   = 'true'           # 소유자만 보기

# 동시 배포 대상 (index.html을 함께 갱신할 번들들)
SITES = [
    {'site_url': 'jp-gamedb',   'bundle_id': 1574},
    {'site_url': 'jp-pipeline', 'bundle_id': 2279},
]

HTML_FILE    = Path(__file__).parent / 'index.html'
STATE_FILE   = Path(__file__).parent / '.ishare_state.json'  # bundle_id 저장(레거시)

HEADERS = {'Authorization': f'Bearer {TOKEN}'}
client  = httpx.Client(verify=False, timeout=60)

# ── 상태 파일 ─────────────────────────────────────────────────────────────
def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding='utf-8'))
    return {}

def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding='utf-8')

# ── 호스팅 상태 조회 ─────────────────────────────────────────────────────
def get_status(bundle_id: int):
    url = f'{ISHARE_BASE}/api/v2/external/hosting/{bundle_id}'
    r = client.get(url, headers=HEADERS)
    if r.status_code == 200:
        data = r.json()
        print(f'✅ 호스팅 상태:')
        print(f'   URL    : {data.get("hosting_url")}')
        print(f'   버전   : {data.get("hosting_version")}')
        print(f'   진입파일: {data.get("entry_file")}')
        return data
    else:
        print(f'❌ 상태 조회 실패: HTTP {r.status_code} — {r.text[:200]}')
        return None

# ── 신규 번들 생성 + 파일 업로드 ─────────────────────────────────────────
def create_bundle() -> int | None:
    url = f'{ISHARE_BASE}/api/v2/external/hosting'
    print(f'📦 새 번들 생성 중: {BUNDLE_NAME}')
    print(f'   site_url  : {SITE_URL}')
    print(f'   is_private: {IS_PRIVATE}')

    if not HTML_FILE.exists():
        print(f'❌ {HTML_FILE} 파일 없음')
        sys.exit(1)

    with open(HTML_FILE, 'rb') as f:
        r = client.post(
            url,
            headers=HEADERS,
            data={
                'bundle_name': BUNDLE_NAME,
                'version':     '1.0.0',
                'site_url':    SITE_URL,
                'entry_file':  'index.html',
                'is_private':  IS_PRIVATE,
                'relative_paths': 'index.html',
            },
            files={'files': ('index.html', f, 'text/html; charset=utf-8')},
        )

    print(f'   HTTP {r.status_code}: {r.text[:300]}')

    if r.status_code == 200:
        data = r.json()
        bundle_id = data['bundle_id']
        version   = data.get('version', '1.0.0')
        print(f'\n✅ 번들 생성 완료!')
        print(f'   bundle_id : {bundle_id}')
        print(f'   version   : {version}')
        print(f'   접속 URL  : https://ishare.nexon.com/sites/{SITE_URL}/')
        return bundle_id
    else:
        print(f'\n❌ 번들 생성 실패')
        return None

# ── 기존 번들 파일 갱신 ───────────────────────────────────────────────────
def update_bundle(bundle_id: int, site_url: str = SITE_URL) -> bool:
    url = f'{ISHARE_BASE}/api/v2/external/hosting/{bundle_id}/upload'
    print(f'🔄 파일 갱신 중: {site_url} (bundle_id={bundle_id})')

    if not HTML_FILE.exists():
        print(f'❌ {HTML_FILE} 파일 없음')
        sys.exit(1)

    size = HTML_FILE.stat().st_size
    print(f'   파일: {HTML_FILE.name} ({size:,} bytes)')

    with open(HTML_FILE, 'rb') as f:
        r = client.post(
            url,
            headers=HEADERS,
            data={
                'entry_file':     'index.html',
                'relative_paths': 'index.html',
            },
            files={'files': ('index.html', f, 'text/html; charset=utf-8')},
        )

    print(f'   HTTP {r.status_code}: {r.text[:300]}')

    if r.status_code == 200:
        data = r.json()
        version = data.get('version', '?')
        print(f'\n✅ 갱신 완료! version={version}')
        print(f'   접속 URL: https://ishare.nexon.com/sites/{site_url}/')
        return True
    else:
        print(f'\n❌ 갱신 실패 (HTTP {r.status_code})')
        return False

# ── 메인 ─────────────────────────────────────────────────────────────────
def main():
    args = sys.argv[1:]

    # 상태 조회: 모든 대상 번들 상태 출력
    if '--status' in args:
        for s in SITES:
            print(f"— {s['site_url']} —")
            get_status(s['bundle_id'])
        return

    # 강제 신규 생성 (jp-gamedb 기준)
    if '--new' in args:
        bundle_id = create_bundle()
        if bundle_id:
            save_state({'bundle_id': bundle_id})
        return

    # 기본: 등록된 모든 번들에 index.html 갱신 배포
    results = []
    for s in SITES:
        ok = update_bundle(s['bundle_id'], s['site_url'])
        results.append((s['site_url'], ok))
        print()
    print('📊 배포 결과:')
    for site, ok in results:
        print(f"   {'✅' if ok else '❌'} {site}")
    if not all(ok for _, ok in results):
        print('💡 실패한 번들은 권한/삭제 여부를 확인하세요.')

if __name__ == '__main__':
    main()
