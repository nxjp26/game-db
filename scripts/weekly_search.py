#!/usr/bin/env python3
"""
weekly_search.py — 주간 게임업계 서칭 → Notion 리포트 자동 생성

사용법:
  python3 scripts/weekly_search.py          # 주간 서칭 실행
  python3 scripts/weekly_search.py --days 3 # 최근 N일치 수집 (기본 7일)
  python3 scripts/weekly_search.py --test   # 소스 연결 테스트만

환경변수 (.env):
  NOTION_TOKEN, NOTION_DB_ID, ANTHROPIC_API_KEY
  NOTION_REPORT_PARENT_ID (첫 실행 시 자동 생성·저장)
"""

import os, re, sys, json, time, ssl
from pathlib import Path
from datetime import datetime, timezone, timedelta

# SSL 인증서 검증 우회 (macOS Python 환경 이슈)
if hasattr(ssl, '_create_unverified_context'):
    ssl._create_default_https_context = ssl._create_unverified_context

# ── 환경변수 로드 ─────────────────────────────────────────────────────────────
def load_env():
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        for line in env_path.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ[k.strip()] = v.strip()

load_env()

NOTION_TOKEN     = os.environ.get('NOTION_TOKEN', '')
NOTION_DB_ID     = os.environ.get('NOTION_DB_ID', '')
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
HTML_FILE        = Path(__file__).parent.parent / 'index.html'
ENV_FILE         = Path(__file__).parent.parent / '.env'

# ── RSS 소스 목록 (검증된 26개) ───────────────────────────────────────────────
RSS_SOURCES = [
    # 일본 게임업계 전문 (7개)
    ("4Gamer.net",             "https://www.4gamer.net/rss/index.xml",                       "jp_game"),
    ("AUTOMATON",              "https://automaton-media.com/feed/",                          "jp_game"),
    ("Game Watch",             "https://game.watch.impress.co.jp/data/rss/1.0/gmw/feed.rdf","jp_game"),
    ("IGN Japan",              "https://jp.ign.com/feed.xml",                               "jp_game"),
    ("denfaminicogamer",       "https://news.denfaminicogamer.jp/feed/",                    "jp_game"),
    ("AppBank",                "https://appbank.net/feed",                                  "jp_game"),
    ("Anime!Anime!",           "https://animeanime.jp/rss/index.rdf",                       "jp_game"),

    # 글로벌 게임 미디어 (10개)
    ("GamesIndustry.biz",      "https://www.gamesindustry.biz/feed",                        "gl_game"),
    ("GamesBeat (VentureBeat)","https://venturebeat.com/category/games/feed/",              "gl_game"),
    ("Gematsu",                "https://www.gematsu.com/feed",                              "gl_game"),
    ("Siliconera",             "https://www.siliconera.com/feed/",                          "gl_game"),
    ("Kotaku",                 "https://kotaku.com/rss",                                    "gl_game"),
    ("Eurogamer",              "https://www.eurogamer.net/feed",                            "gl_game"),
    ("PC Gamer",               "https://www.pcgamer.com/rss/",                              "gl_game"),
    ("IGN",                    "https://feeds.ign.com/ign/all",                             "gl_game"),
    ("Polygon",                "https://www.polygon.com/rss/index.xml",                     "gl_game"),
    ("Nintendo Life",          "https://www.nintendolife.com/feeds/news",                   "gl_game"),

    # 비즈니스·M&A·투자 (4개)
    ("TechCrunch Japan",       "https://techcrunch.com/tag/japan/feed/",                    "biz"),
    ("日経クロステック",        "https://xtech.nikkei.com/rss/xtech-it.rdf",                 "biz"),
    ("VentureBeat AI",         "https://venturebeat.com/ai/feed/",                          "biz"),
    ("Crunchbase News",        "https://news.crunchbase.com/rss/",                          "biz"),

    # 애니·만화·IP (2개)
    ("Anime News Network",     "https://www.animenewsnetwork.com/all/rss.xml?ann-edition=ja","ip"),
    ("Comic Natalie",          "https://natalie.mu/comic/feed/news",                        "ip"),

    # 커뮤니티 (3개)
    ("Reddit r/Games",         "https://www.reddit.com/r/Games/.rss",                       "community"),
    ("Reddit r/gamedev",       "https://www.reddit.com/r/gamedev/.rss",                     "community"),
    ("Reddit r/gachagaming",   "https://www.reddit.com/r/gachagaming/.rss",                 "community"),
]

# ── 기존 D[] 기업 목록 추출 ───────────────────────────────────────────────────
def get_existing_companies():
    html = HTML_FILE.read_text(encoding='utf-8')
    # D[] 배열에서 nk(한국어명) 또는 n(일본어명)만 추출
    # {n:'xxx', nk:'yyy', ...} 패턴에서 첫 번째 n 또는 nk 값만 추출
    entries = re.findall(r"\{n:'([^']+)'(?:,nk:'([^']+)')?", html)
    names = set()
    for n, nk in entries:
        names.add(nk if nk else n)
        if n: names.add(n)
    return names

# ── RSS 수집 ──────────────────────────────────────────────────────────────────
def fetch_rss(days=7):
    try:
        import feedparser
    except ImportError:
        print('❌ feedparser 미설치: pip3 install feedparser')
        sys.exit(1)

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    articles = []
    stats = {'ok': 0, 'fail': 0, 'total': 0}

    for name, url, category in RSS_SOURCES:
        try:
            feed = feedparser.parse(url)
            count = 0
            for entry in feed.entries:
                # 날짜 파싱
                pub = None
                for attr in ('published_parsed', 'updated_parsed', 'created_parsed'):
                    if hasattr(entry, attr) and getattr(entry, attr):
                        import calendar
                        ts = calendar.timegm(getattr(entry, attr))
                        pub = datetime.fromtimestamp(ts, tz=timezone.utc)
                        break

                if pub and pub < cutoff:
                    continue  # 오래된 기사 스킵

                title   = getattr(entry, 'title', '').strip()
                summary = getattr(entry, 'summary', '')
                # HTML 태그 제거
                summary = re.sub(r'<[^>]+>', '', summary)[:300]
                link    = getattr(entry, 'link', '')

                if title:
                    articles.append({
                        'source': name,
                        'category': category,
                        'title': title,
                        'summary': summary,
                        'link': link,
                        'pub': pub.strftime('%Y-%m-%d') if pub else '날짜미상'
                    })
                    count += 1

            stats['total'] += count
            if count > 0:
                stats['ok'] += 1
                print(f'  ✅ {name}: {count}개')
            else:
                stats['fail'] += 1
                print(f'  ⚠️  {name}: 0개 (피드 없음 또는 최근 기사 없음)')

        except Exception as e:
            stats['fail'] += 1
            print(f'  ❌ {name}: {e}')

    print(f'\n수집 완료: {stats["ok"]}/{len(RSS_SOURCES)} 소스, 총 {stats["total"]}개 기사')
    return articles

# ── 기사 사전 필터링 ──────────────────────────────────────────────────────────
BUSINESS_KEYWORDS = [
    # M&A / 투자
    '買収','合併','出資','M&A','IPO','上場','資金調達','ファンド',
    'acquisition','merger','investment','funding','raises','IPO',
    # 기업 이벤트
    '設立','解散','倒産','売却','分社','子会社','統合',
    'founded','shutdown','acquired','sold','subsidiary',
    # 재무
    '決算','売上','赤字','黒字','業績','リストラ','希望退職',
    'revenue','profit','loss','layoff','restructure',
    # 신규 스튜디오/기업
    'スタジオ','新会社','新スタジオ','studio','new company',
    # 게임업계
    'ゲーム会社','ゲームスタジオ','パブリッシャー','デベロッパー',
    'game company','publisher','developer','anime','IP',
]

def prefilter_articles(articles):
    """M&A·기업·재무 관련 기사만 우선 선별 (최대 150개)"""
    scored = []
    for a in articles:
        text = (a['title'] + ' ' + a['summary']).lower()
        score = sum(1 for kw in BUSINESS_KEYWORDS if kw.lower() in text)
        if score > 0:
            scored.append((score, a))

    # 점수 높은 순 + 소스 다양성 확보
    scored.sort(key=lambda x: -x[0])
    selected = [a for _, a in scored[:150]]

    # 점수 0이어도 biz 카테고리는 포함
    biz_articles = [a for a in articles if a['category'] == 'biz' and a not in selected]
    selected.extend(biz_articles[:30])

    return selected[:180]

# ── Claude API 분석 ───────────────────────────────────────────────────────────
def analyze_with_claude(articles, existing_companies):
    try:
        import anthropic
    except ImportError:
        print('❌ anthropic 미설치: pip3 install anthropic')
        sys.exit(1)

    if not ANTHROPIC_API_KEY:
        print('❌ ANTHROPIC_API_KEY가 설정되지 않았습니다.')
        sys.exit(1)

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    # 기사 사전 필터링
    filtered = prefilter_articles(articles)
    print(f'  📌 필터링: {len(articles)}개 → 핵심 {len(filtered)}개 선별')

    articles_text = ''
    for i, a in enumerate(filtered):
        articles_text += f"[{i+1}][{a['source']}] {a['title']}\n"
        if a['summary']:
            articles_text += f"  {a['summary'][:150]}\n"

    existing_list = ', '.join(sorted(existing_companies))

    prompt = f"""You are an M&A intelligence analyst for Nexon Japan's corporate development team. Analyze this week's game industry news.

EXISTING MONITORED COMPANIES (do NOT include these as new_candidates):
{existing_list}

THIS WEEK'S NEWS ({len(filtered)} articles selected from {len(articles)} total):
{articles_text}

Output ONLY valid JSON (no markdown, no explanation):

{{"new_candidates":[{{"name_jp":"JP name","name_kr":"KR name","reason":"Why notable for Nexon M&A (2-3 sentences)","category":"개발사/판권사/AI기술/수탁개발 etc","ma_potential":"O/T/X/N","source_title":"article title","priority":"high/medium/low"}}],"ma_news":[{{"title":"news title","companies":["company"],"summary":"1-2 sentence summary","nexon_relevance":"high/medium/low","source":"source name"}}],"financial_events":[{{"company":"name","event":"type","summary":"1 sentence","source":"source"}}],"industry_trends":[{{"trend":"keyword","summary":"2-3 sentences","nexon_implication":"implication"}}],"stats":{{"articles_analyzed":{len(articles)},"filtered":{len(filtered)}}}}}

Rules:
- new_candidates: ONLY companies NOT in the existing list above
- Focus on Japan/Asia game companies, anime IP holders, game AI tech firms
- Keep each field concise to avoid truncation
- ma_news: include M&A, acquisitions, funding rounds, IPO news
- financial_events: earnings, losses, layoffs for EXISTING monitored companies only
- Max 8 new_candidates, 10 ma_news, 10 financial_events, 5 trends"""

    print('\n🤖 Claude API 분석 중...')
    try:
        msg = client.messages.create(
            model='claude-sonnet-4-6',
            max_tokens=6000,
            messages=[{'role': 'user', 'content': prompt}]
        )
        raw = msg.content[0].text.strip()

        # JSON 추출 시도 (여러 방법)
        # 1. 직접 파싱
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass
        # 2. 코드블록 제거 후 파싱
        clean = re.sub(r'^```(?:json)?\s*|\s*```$', '', raw, flags=re.MULTILINE).strip()
        try:
            return json.loads(clean)
        except json.JSONDecodeError:
            pass
        # 3. 첫 번째 { ~ 마지막 } 추출
        m = re.search(r'(\{[\s\S]*\})', clean)
        if m:
            return json.loads(m.group(1))

        print('⚠️ JSON 추출 실패. 원본:', raw[:200])
        return None

    except Exception as e:
        print(f'❌ Claude API 오류: {e}')
        return None

# ── Notion 리포트 페이지 생성 ─────────────────────────────────────────────────
def get_or_create_report_parent(notion):
    """리포트 전용 부모 페이지 ID를 반환 (없으면 생성)"""
    # .env에서 기존 ID 확인
    env_text = ENV_FILE.read_text(encoding='utf-8')
    m = re.search(r'NOTION_REPORT_PARENT_ID=(.+)', env_text)
    if m:
        return m.group(1).strip()

    # 기업 DB의 부모 페이지 찾기
    print('📁 리포트 전용 Notion 페이지 생성 중...')
    db_info = notion.databases.retrieve(NOTION_DB_ID)
    parent = db_info.get('parent', {})

    # 부모 페이지 ID 결정
    if parent.get('type') == 'page_id':
        parent_config = {'type': 'page_id', 'page_id': parent['page_id']}
    else:
        parent_config = {'type': 'workspace', 'workspace': True}

    # "📡 주간 서칭 리포트" 페이지 생성
    new_page = notion.pages.create(
        parent=parent_config,
        properties={
            'title': {
                'title': [{'text': {'content': '📡 주간 게임업계 서칭 리포트'}}]
            }
        },
        children=[
            {
                'object': 'block',
                'type': 'paragraph',
                'paragraph': {
                    'rich_text': [{
                        'text': {'content': '매주 자동 생성되는 일본 게임업계 인텔리전스 리포트 모음입니다.'}
                    }]
                }
            }
        ]
    )
    parent_id = new_page['id']

    # .env에 저장
    with open(ENV_FILE, 'a', encoding='utf-8') as f:
        f.write(f'\nNOTION_REPORT_PARENT_ID={parent_id}\n')
    print(f'  ✅ 부모 페이지 생성 완료: {parent_id}')
    return parent_id

def rich_text(content, bold=False, color=None):
    t = {'type': 'text', 'text': {'content': content}}
    if bold or color:
        t['annotations'] = {}
        if bold:  t['annotations']['bold'] = True
        if color: t['annotations']['color'] = color
    return t

def heading(level, text):
    t = f'heading_{level}'
    return {'object':'block','type':t, t:{'rich_text':[rich_text(text)]}}

def paragraph(parts):
    return {'object':'block','type':'paragraph','paragraph':{'rich_text': parts if isinstance(parts, list) else [rich_text(parts)]}}

def divider():
    return {'object':'block','type':'divider','divider':{}}

def callout(text, emoji='💡', color='blue_background'):
    return {
        'object':'block','type':'callout',
        'callout':{
            'icon':{'type':'emoji','emoji':emoji},
            'color': color,
            'rich_text':[rich_text(text)]
        }
    }

def bulleted(text):
    return {'object':'block','type':'bulleted_list_item','bulleted_list_item':{'rich_text':[rich_text(text)]}}

def build_report_blocks(result, articles, days):
    now = datetime.now().strftime('%Y년 %m월 %d일')
    blocks = []

    # 헤더
    blocks.append(callout(
        f"자동 생성 | 수집 기간: 최근 {days}일 | 소스: {len(RSS_SOURCES)}개 | 기사: {result['stats']['articles_analyzed']}개 분석",
        '🤖', 'gray_background'
    ))
    blocks.append(divider())

    # 1. 신규 기업 후보
    new_c = result.get('new_candidates', [])
    blocks.append(heading(2, f'🆕 신규 기업 후보 ({len(new_c)}개)'))

    if new_c:
        high   = [c for c in new_c if c.get('priority') == 'high']
        medium = [c for c in new_c if c.get('priority') == 'medium']
        low    = [c for c in new_c if c.get('priority') == 'low']

        for group, label, emoji in [(high,'우선도 높음','🔴'), (medium,'우선도 중간','🟡'), (low,'우선도 낮음','🟢')]:
            if not group: continue
            blocks.append(paragraph([rich_text(f'{emoji} {label}', bold=True)]))
            for c in group:
                ma_label = {'O':'매수가능','T':'조건부','X':'매수불가','N':'미검토'}.get(c.get('ma_potential','N'),'미검토')
                blocks.append(callout(
                    f"{c.get('name_kr','?')} ({c.get('name_jp','?')})  [{c.get('category','?')}]  M&A: {ma_label}\n{c.get('reason','')}\n출처: {', '.join(c.get('source_articles',[])[:2])}",
                    emoji, 'default'
                ))
    else:
        blocks.append(paragraph('이번 주 신규 후보 없음'))

    blocks.append(divider())

    # 2. M&A / 인수 / 투자 뉴스
    ma_news = result.get('ma_news', [])
    blocks.append(heading(2, f'💼 M&A · 인수 · 투자 뉴스 ({len(ma_news)}건)'))
    if ma_news:
        for n in ma_news:
            rel = {'high':'🔴 관련도 높음','medium':'🟡 관련도 중간','low':'🟢 관련도 낮음'}.get(n.get('nexon_relevance','low'),'')
            blocks.append(bulleted(f"[{n.get('source','')}] {n.get('title','')}  {rel}"))
            blocks.append(paragraph(f"  → {n.get('summary','')}  관련기업: {', '.join(n.get('companies',[]))}"))
    else:
        blocks.append(paragraph('해당 뉴스 없음'))

    blocks.append(divider())

    # 3. 기존 기업 재무 이벤트
    fin = result.get('financial_events', [])
    blocks.append(heading(2, f'📊 기존 기업 재무 이벤트 ({len(fin)}건)'))
    if fin:
        for f in fin:
            blocks.append(bulleted(f"[{f.get('company','')}] {f.get('event','')}  — {f.get('summary','')}  출처: {f.get('source','')}"))
    else:
        blocks.append(paragraph('해당 이벤트 없음'))

    blocks.append(divider())

    # 4. 업계 트렌드
    trends = result.get('industry_trends', [])
    blocks.append(heading(2, f'🌊 업계 트렌드 ({len(trends)}개)'))
    if trends:
        for t in trends:
            blocks.append(callout(
                f"{t.get('trend','')}\n{t.get('summary','')}\n넥슨 시사점: {t.get('nexon_implication','')}",
                '📌', 'yellow_background'
            ))
    else:
        blocks.append(paragraph('해당 트렌드 없음'))

    blocks.append(divider())

    # 5. 수집 통계
    blocks.append(heading(2, '📈 수집 통계'))
    category_count = {}
    for a in articles:
        category_count[a['category']] = category_count.get(a['category'], 0) + 1
    cat_labels = {
        'jp_game':'일본 게임업계', 'gl_game':'글로벌 게임미디어',
        'biz':'비즈니스/M&A', 'ip':'애니/IP', 'mobile':'모바일/앱', 'community':'커뮤니티'
    }
    for cat, cnt in sorted(category_count.items(), key=lambda x:-x[1]):
        blocks.append(bulleted(f"{cat_labels.get(cat,cat)}: {cnt}개"))

    return blocks

def create_notion_report(result, articles, days):
    try:
        from notion_client import Client
    except ImportError:
        print('❌ notion-client 미설치')
        sys.exit(1)

    if not NOTION_TOKEN:
        print('❌ NOTION_TOKEN이 설정되지 않았습니다.')
        sys.exit(1)

    notion = Client(auth=NOTION_TOKEN)
    now_str = datetime.now().strftime('%Y-%m-%d')
    title = f'📡 주간 서칭 리포트 {now_str}'

    print('\n📝 Notion 리포트 작성 중...')
    parent_id = get_or_create_report_parent(notion)
    blocks = build_report_blocks(result, articles, days)

    # 페이지 생성 (Notion API는 한 번에 100블록 제한)
    page = notion.pages.create(
        parent={'type': 'page_id', 'page_id': parent_id},
        properties={
            'title': {'title': [{'text': {'content': title}}]}
        },
        children=blocks[:100]
    )
    page_id = page['id']

    # 100개 초과 블록은 append
    for i in range(100, len(blocks), 100):
        notion.blocks.children.append(page_id, children=blocks[i:i+100])
        time.sleep(0.3)

    page_url = f"https://notion.so/{page_id.replace('-','')}"
    print(f'  ✅ 리포트 생성 완료: {title}')
    print(f'  🔗 {page_url}')
    return page_url

# ── 메인 ─────────────────────────────────────────────────────────────────────
def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--days',  type=int, default=7,     help='수집 기간(일)')
    parser.add_argument('--test',  action='store_true',     help='소스 연결 테스트만')
    args = parser.parse_args()

    print(f'🔍 주간 게임업계 서칭 시작 (최근 {args.days}일)')
    print(f'📡 소스: {len(RSS_SOURCES)}개\n')

    # RSS 수집
    articles = fetch_rss(days=args.days)
    if args.test:
        print('\n테스트 완료.')
        return

    if not articles:
        print('⚠️ 수집된 기사가 없습니다.')
        return

    # 기존 기업 목록
    existing = get_existing_companies()
    print(f'\n📋 기존 모니터링 기업: {len(existing)}개')

    # Claude 분석
    result = analyze_with_claude(articles, existing)
    if not result:
        print('❌ 분석 실패')
        return

    new_c = result.get('new_candidates', [])
    ma_n  = result.get('ma_news', [])
    fin   = result.get('financial_events', [])
    trend = result.get('industry_trends', [])
    print(f'\n📊 분석 결과: 신규후보 {len(new_c)}개 | M&A뉴스 {len(ma_n)}건 | 재무이벤트 {len(fin)}건 | 트렌드 {len(trend)}개')

    # Notion 리포트 생성
    create_notion_report(result, articles, args.days)

if __name__ == '__main__':
    main()
