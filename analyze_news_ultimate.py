import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time
import os
import sys
import re
import feedparser
from newsapi import NewsApiClient

# UTF-8 출력 설정 (Windows)
if sys.platform == 'win32':
    os.system('chcp 65001 > nul')

# News API 설정 (무료 플랜: 월 500건)
# API 키를 환경 변수 또는 config 파일에서 가져오세요
# 무료 가입: https://newsapi.org/
NEWS_API_KEY = os.environ.get('NEWS_API_KEY', 'YOUR_API_KEY_HERE')  # 환경변수에서 가져오기

def detect_category(keyword):
    """키워드 카테고리를 자동 인식합니다."""

    # 거시경제 키워드
    macro_keywords = [
        '증시', '환율', '금리', '유가', '달러', '원화', '인플레이션',
        '연준', 'Fed', '기준금리', '통화정책', '경제', 'GDP', 'CPI',
        '무역', '관세', '경기', '침체', '경제성장', '재정', '예산'
    ]

    # 미국 시장 키워드
    us_market_keywords = [
        '미국', 'US', '나스닥', '다우', 'S&P', 'NASDAQ', 'NYSE',
        '월스트리트', '실리콘밸리'
    ]

    # 산업/테마 키워드
    theme_keywords = [
        'AI', '반도체', '2차전지', '바이오', '원자력', '수소', 'ESS',
        '전기차', 'EV', '로봇', '우주', '방산', '제약', 'IT',
        '클라우드', '메타버스', 'NFT', '블록체인'
    ]

    # 미국 기업 키워드
    us_companies = [
        '엔비디아', 'NVIDIA', '테슬라', 'Tesla', '애플', 'Apple',
        '마이크로소프트', 'Microsoft', '아마존', 'Amazon', '구글', 'Google',
        '메타', 'Meta', 'AMD', '인텔', 'Intel'
    ]

    keyword_lower = keyword.lower()

    # 카테고리 판정
    if any(k in keyword for k in us_market_keywords):
        return '미국증시'
    elif any(k in keyword for k in macro_keywords):
        return '거시경제'
    elif any(k in keyword for k in us_companies):
        return '미국기업'
    elif any(k in keyword for k in theme_keywords):
        return '산업테마'
    else:
        return '국내종목'

def translate_keyword_for_english(keyword):
    """한글 키워드를 영어 검색어로 변환합니다."""
    translation_map = {
        '엔비디아': 'NVIDIA',
        '테슬라': 'Tesla',
        '애플': 'Apple',
        '마이크로소프트': 'Microsoft',
        '아마존': 'Amazon',
        '구글': 'Google',
        '메타': 'Meta',
        '미국 증시': 'US stock market',
        '나스닥': 'NASDAQ',
        '다우': 'Dow Jones',
        '미국 증시 핫한 종목': 'US hot stocks trending',
    }

    # 직접 매칭
    if keyword in translation_map:
        return translation_map[keyword]

    # 부분 매칭
    for kor, eng in translation_map.items():
        if kor in keyword:
            return eng

    # 변환 실패 시 원본 반환
    return keyword

def get_enhanced_keywords(category):
    """카테고리별 맞춤 키워드를 반환합니다."""

    # 기본 호재/악재 키워드
    base_positive = [
        '상승', '호재', '증가', '성장', '확대', '개선', '흑자', '수주', '계약',
        '신규', '출시', '개발', '성공', '호조', '상향', '긍정', '투자', '협력',
        '제휴', '특허', '수출', '실적', '배당', '증설', '확장', '진출', '도약',
        '수익', '매출', '순이익', '돌파', '신기록', '최고', '급등', '강세',
        # 영문 키워드 추가
        'surge', 'soar', 'rally', 'gain', 'rise', 'jump', 'climb', 'advance',
        'bull', 'bullish', 'growth', 'profit', 'revenue', 'beat', 'outperform',
        'upgrade', 'positive', 'strong', 'boost', 'record', 'high', 'peak'
    ]

    base_negative = [
        '하락', '악재', '감소', '축소', '부진', '적자', '취소', '지연', '실패',
        '하향', '부정', '리스크', '우려', '손실', '감사', '규제', '소송',
        '사고', '문제', '위반', '중단', '폐기', '철수', '파산', '구조조정',
        '적자', '손해', '급락', '약세', '위기', '불안', '침체',
        # 영문 키워드 추가
        'fall', 'drop', 'plunge', 'decline', 'slump', 'tumble', 'sink', 'slip',
        'bear', 'bearish', 'loss', 'miss', 'disappoint', 'downgrade', 'negative',
        'weak', 'concern', 'worry', 'risk', 'cut', 'low', 'crisis'
    ]

    # 카테고리별 추가 키워드
    if category == '미국증시':
        positive_add = [
            '랠리', '사상최고', 'ATH', '사고가', '기록경신', '불기둥',
            '호황', '반등', '상승장', '강세장', '신고가', '급등',
            '매수세', '자금유입', '수급', '인상', '펀더멘털', '밸류에이션',
            'all-time high', 'breakout', 'momentum', 'strength'
        ]
        negative_add = [
            '폭락', '급락', '약세장', '하락장', '조정', '패닉',
            '차익실현', '매도세', '자금이탈', '버블', '공포', '변동성',
            '하락세', '침체', '우려', '긴축', '금리인상',
            'selloff', 'correction', 'volatility', 'crash', 'panic'
        ]

    elif category == '거시경제':
        positive_add = [
            '금리인하', '완화', '부양', '경기회복', '호전', '반등',
            '확장', '개선', '성장률', '고용증가', '소비증가', '수출증가',
            '투자증가', '경기확장', '인하', '경기회복', '안정',
            'rate cut', 'easing', 'stimulus', 'recovery', 'expansion'
        ]
        negative_add = [
            '금리인상', '긴축', '경기침체', '불황', '위축', '둔화',
            '하락', '감소', '리세션', '경기후퇴', '경기위축', '인상',
            '위기', '붕괴', '불안', '급등', '물가상승',
            'rate hike', 'tightening', 'recession', 'slowdown', 'contraction'
        ]

    elif category in ['미국기업', '산업테마', '국내종목']:
        positive_add = [
            'FDA승인', '계약체결', '수주', '매출증가', '신제품', '혁신',
            '기술개발', '특허등록', '인수합병', 'M&A', '투자유치', '상장',
            'IPO', '시장점유율', '경쟁력', '글로벌진출', '파트너십',
            'FDA approval', 'contract', 'deal', 'innovation', 'breakthrough',
            'partnership', 'collaboration', 'acquisition', 'expansion'
        ]
        negative_add = [
            '리콜', '제재', '벌금', '영업정지', '허가취소', '임상실패',
            '계약취소', '수주취소', '손실', '매출감소', '시장이탈',
            '경쟁심화', '점유율하락', '실적부진', '적자지속',
            'recall', 'penalty', 'lawsuit', 'investigation', 'failure',
            'cancellation', 'delay', 'competition', 'challenge'
        ]
    else:
        positive_add = []
        negative_add = []

    return {
        'positive': base_positive + positive_add,
        'negative': base_negative + negative_add
    }

def get_report_path(keyword, date_str=None):
    """뉴스 리포트 경로를 반환합니다."""
    if date_str is None:
        date_str = datetime.now().strftime('%Y-%m-%d')

    # news 폴더 생성
    report_dir = os.path.join('report', date_str, 'news')
    os.makedirs(report_dir, exist_ok=True)

    # 파일명에서 사용할 수 없는 문자 제거
    safe_keyword = re.sub(r'[\\/*?:"<>|]', '', keyword)
    return os.path.join(report_dir, f'news_{safe_keyword}.md')

def crawl_google_news_rss(keyword, days=14):
    """Google News RSS를 통해 뉴스를 수집합니다."""
    print(f"\n[Google News RSS] '{keyword}' 뉴스 수집 중...")

    articles = []

    try:
        # Google News RSS URL
        # 한글 키워드는 URL 인코딩
        import urllib.parse
        encoded_keyword = urllib.parse.quote(keyword)
        rss_url = f"https://news.google.com/rss/search?q={encoded_keyword}&hl=ko&gl=KR&ceid=KR:ko"

        # RSS 파싱
        feed = feedparser.parse(rss_url)

        print(f"  발견된 RSS 항목: {len(feed.entries)}개")

        for entry in feed.entries[:30]:  # 최대 30개
            try:
                title = entry.title if hasattr(entry, 'title') else ''
                link = entry.link if hasattr(entry, 'link') else ''
                content = entry.summary if hasattr(entry, 'summary') else ''

                # HTML 태그 제거
                content = BeautifulSoup(content, 'html.parser').get_text(strip=True)

                # 날짜 파싱
                if hasattr(entry, 'published_parsed'):
                    date = datetime(*entry.published_parsed[:6])
                else:
                    date = datetime.now()

                # 출처 추출
                source = entry.source.title if hasattr(entry, 'source') and hasattr(entry.source, 'title') else 'Google News'

                articles.append({
                    'title': title,
                    'content': content,
                    'source': source,
                    'date': date,
                    'date_text': date.strftime('%Y-%m-%d %H:%M'),
                    'link': link
                })

            except Exception as e:
                continue

        print(f"  수집 완료: {len(articles)}개")

    except Exception as e:
        print(f"  Google News RSS 수집 실패: {e}")

    return articles

def crawl_newsapi(keyword, days=14):
    """News API를 통해 영문 뉴스를 수집합니다."""
    print(f"\n[News API] '{keyword}' 뉴스 수집 중...")

    articles = []

    # API 키 확인
    if NEWS_API_KEY == 'YOUR_API_KEY_HERE':
        print("  [WARNING] News API key is not configured.")
        print("  Set environment variable NEWS_API_KEY or enter directly in code.")
        print("  Free signup: https://newsapi.org/")
        return articles

    try:
        # News API 클라이언트 초기화
        newsapi = NewsApiClient(api_key=NEWS_API_KEY)

        # 날짜 범위 설정
        to_date = datetime.now()
        from_date = to_date - timedelta(days=days)

        # 뉴스 검색
        all_articles = newsapi.get_everything(
            q=keyword,
            from_param=from_date.strftime('%Y-%m-%d'),
            to=to_date.strftime('%Y-%m-%d'),
            language='en',
            sort_by='relevancy',
            page_size=50  # 최대 50개
        )

        print(f"  발견된 기사: {len(all_articles.get('articles', []))}개")

        for article in all_articles.get('articles', []):
            try:
                title = article.get('title', '')
                content = article.get('description', '') or article.get('content', '')
                source = article.get('source', {}).get('name', 'Unknown')
                link = article.get('url', '')

                # 날짜 파싱
                published_at = article.get('publishedAt', '')
                if published_at:
                    date = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                else:
                    date = datetime.now()

                articles.append({
                    'title': title,
                    'content': content,
                    'source': source,
                    'date': date,
                    'date_text': date.strftime('%Y-%m-%d %H:%M'),
                    'link': link
                })

            except Exception as e:
                continue

        print(f"  수집 완료: {len(articles)}개")

    except Exception as e:
        print(f"  News API 수집 실패: {e}")
        if "apiKey" in str(e):
            print("  [WARNING] API key is invalid. Check at https://newsapi.org/")

    return articles

def crawl_naver_news(keyword, days=14):
    """네이버 뉴스를 크롤링합니다."""
    print(f"\n[Naver News] '{keyword}' 뉴스 수집 중...")

    # 날짜 계산
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    # 네이버 뉴스 검색 URL
    base_url = "https://search.naver.com/search.naver"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    articles = []

    # 여러 페이지 수집 (최대 3페이지)
    for page in range(1, 4):
        params = {
            'where': 'news',
            'query': keyword,
            'start': (page - 1) * 10 + 1,
            'sort': '1'  # 최신순 정렬
        }

        try:
            response = requests.get(base_url, params=params, headers=headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # 뉴스 기사 검색
            news_items = soup.select('.vs1RfKE1eTzMZ5RqnhIv')

            if not news_items:
                break

            for item in news_items:
                try:
                    # 제목 추출
                    title_elem = item.select_one('a[data-heatmap-target=".tit"] span')
                    if not title_elem:
                        continue

                    # <mark> 태그 제거
                    for mark in title_elem.find_all('mark'):
                        mark.unwrap()

                    title = title_elem.get_text(strip=True)

                    # 링크 추출
                    link_elem = item.select_one('a[data-heatmap-target=".tit"]')
                    link = link_elem.get('href', '') if link_elem else ''

                    # 본문 요약 추출
                    content_elem = item.select_one('a[data-heatmap-target=".body"] span')
                    if content_elem:
                        for mark in content_elem.find_all('mark'):
                            mark.unwrap()
                        content = content_elem.get_text(strip=True)
                    else:
                        content = ''

                    # 언론사 추출
                    source_elem = item.select_one('a[data-heatmap-target=".prof"] span')
                    source = source_elem.get_text(strip=True) if source_elem else '출처 미상'

                    # 날짜 추출
                    date_elem = item.select_one('.U1zN1wdZWj0pyvj9oyR0 span')
                    date_text = date_elem.get_text(strip=True) if date_elem else ''

                    # 날짜 파싱
                    article_date = parse_date(date_text)

                    # 기간 필터링
                    if article_date and article_date < start_date:
                        continue

                    articles.append({
                        'title': title,
                        'content': content,
                        'source': source,
                        'date': article_date,
                        'date_text': date_text,
                        'link': link
                    })

                except Exception as e:
                    continue

            time.sleep(1)

        except requests.RequestException as e:
            break

    print(f"  수집 완료: {len(articles)}개")

    return articles

def parse_date(date_text):
    """날짜 텍스트를 datetime 객체로 변환합니다."""
    try:
        now = datetime.now()

        # "n분 전", "n시간 전" 형식
        if '분 전' in date_text or '분전' in date_text:
            minutes = int(re.search(r'(\d+)', date_text).group(1))
            return now - timedelta(minutes=minutes)
        elif '시간 전' in date_text or '시간전' in date_text:
            hours = int(re.search(r'(\d+)', date_text).group(1))
            return now - timedelta(hours=hours)
        elif '일 전' in date_text or '일전' in date_text:
            days = int(re.search(r'(\d+)', date_text).group(1))
            return now - timedelta(days=days)

        # "YYYY.MM.DD" 형식
        date_match = re.search(r'(\d{4})\.(\d{1,2})\.(\d{1,2})', date_text)
        if date_match:
            year, month, day = date_match.groups()
            return datetime(int(year), int(month), int(day))

        return None

    except:
        return None

def crawl_ultimate_news(keyword, days=14):
    """모든 소스에서 뉴스를 수집합니다: Google RSS + News API + Naver"""

    # 카테고리 감지
    category = detect_category(keyword)

    all_articles = []

    # 1. Google News RSS (한글 + 영문 모두 지원)
    google_articles = crawl_google_news_rss(keyword, days)
    all_articles.extend(google_articles)

    # 2. News API (영문 뉴스 - 미국 증시/기업인 경우)
    if category in ['미국증시', '미국기업']:
        english_keyword = translate_keyword_for_english(keyword)
        newsapi_articles = crawl_newsapi(english_keyword, days)
        all_articles.extend(newsapi_articles)

    # 3. 네이버 뉴스 (한글 뉴스)
    naver_articles = crawl_naver_news(keyword, days)
    all_articles.extend(naver_articles)

    # 중복 제거 (제목 기준)
    seen_titles = set()
    unique_articles = []

    for article in all_articles:
        # 제목 정규화 (공백, 특수문자 제거)
        normalized_title = re.sub(r'[\s\W]+', '', article['title'].lower())

        if normalized_title not in seen_titles and normalized_title:
            seen_titles.add(normalized_title)
            unique_articles.append(article)

    # 날짜순 정렬 (최신순)
    unique_articles.sort(key=lambda x: x['date'] if x['date'] else datetime.min, reverse=True)

    print(f"\n{'='*80}")
    print(f"총 {len(unique_articles)}개의 고유 기사를 수집했습니다.")
    print(f"  - Google News RSS: {len(google_articles)}개")
    print(f"  - News API: {len([a for a in all_articles if a['source'] not in ['Google News', '출처 미상'] and a not in google_articles and a not in naver_articles])}개")
    print(f"  - Naver News: {len(naver_articles)}개")
    print(f"  - 중복 제거 후: {len(unique_articles)}개")
    print(f"{'='*80}\n")

    return unique_articles

def analyze_sentiment(articles, category):
    """기사의 호재/악재를 분석합니다. (카테고리별 맞춤 키워드 기반)"""

    # 카테고리별 키워드 가져오기
    keywords = get_enhanced_keywords(category)
    positive_keywords = keywords['positive']
    negative_keywords = keywords['negative']

    analyzed = []

    for article in articles:
        text = (article['title'] + ' ' + article['content']).lower()

        # 키워드 카운트
        positive_count = sum(1 for keyword in positive_keywords if keyword.lower() in text)
        negative_count = sum(1 for keyword in negative_keywords if keyword.lower() in text)

        # 감성 분류
        if positive_count > negative_count:
            sentiment = '호재'
            score = min(positive_count, 5)  # 최대 5점
        elif negative_count > positive_count:
            sentiment = '악재'
            score = min(negative_count, 5)
        else:
            sentiment = '중립'
            score = 0

        # 중요도 계산 (호재/악재 키워드 개수 + 최신성)
        importance = positive_count + negative_count

        analyzed.append({
            **article,
            'sentiment': sentiment,
            'score': score,
            'importance': importance,
            'positive_count': positive_count,
            'negative_count': negative_count
        })

    return analyzed

def generate_enhanced_report(keyword, analyzed_articles, category, date_str=None):
    """개선된 뉴스 분석 리포트를 마크다운으로 생성합니다."""

    if date_str is None:
        date_str = datetime.now().strftime('%Y-%m-%d')

    # 호재/악재/중립 분류 및 중요도순 정렬
    positive_news = sorted([a for a in analyzed_articles if a['sentiment'] == '호재'],
                          key=lambda x: x['importance'], reverse=True)
    negative_news = sorted([a for a in analyzed_articles if a['sentiment'] == '악재'],
                          key=lambda x: x['importance'], reverse=True)
    neutral_news = [a for a in analyzed_articles if a['sentiment'] == '중립']

    # 카테고리별 아이콘
    category_icons = {
        '미국증시': '🇺🇸',
        '거시경제': '📊',
        '미국기업': '🏢',
        '산업테마': '🏭',
        '국내종목': '📈'
    }

    icon = category_icons.get(category, '📰')

    md_content = f"""# {icon} {keyword} 뉴스 분석 리포트 (Ultimate Multi-Source)

**분석 일시**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**분석 대상 날짜**: {date_str}
**수집 기간**: 최근 14일
**카테고리**: {category}
**데이터 소스**: Google News RSS, News API, Naver News

---

## 📊 요약 통계

| 구분 | 건수 | 비율 |
|------|------|------|
| **전체 기사** | {len(analyzed_articles)}건 | 100% |
| 🟢 **호재성 기사** | {len(positive_news)}건 | {len(positive_news)/len(analyzed_articles)*100:.1f}% |
| 🔴 **악재성 기사** | {len(negative_news)}건 | {len(negative_news)/len(analyzed_articles)*100:.1f}% |
| ⚪ **중립 기사** | {len(neutral_news)}건 | {len(neutral_news)/len(analyzed_articles)*100:.1f}% |

### 💹 시장 분위기
"""

    # 시장 분위기 판단
    sentiment_ratio = len(positive_news) / len(analyzed_articles) if analyzed_articles else 0

    if sentiment_ratio >= 0.7:
        market_mood = "**매우 긍정적** 🔥 - 강한 호재 뉴스 우세"
    elif sentiment_ratio >= 0.5:
        market_mood = "**긍정적** ✅ - 호재 뉴스 우세"
    elif sentiment_ratio >= 0.4:
        market_mood = "**중립적** ⚖️ - 호재와 악재 균형"
    elif sentiment_ratio >= 0.2:
        market_mood = "**부정적** ⚠️ - 악재 뉴스 우세"
    else:
        market_mood = "**매우 부정적** 🚨 - 강한 악재 뉴스 우세"

    md_content += f"- {market_mood}\n"
    md_content += f"- 호재/악재 비율: {len(positive_news)}:{len(negative_news)}\n\n"

    md_content += "---\n\n"

    # 호재성 뉴스
    md_content += f"## 🟢 호재성 뉴스 ({len(positive_news)}건)\n\n"

    if positive_news:
        for idx, article in enumerate(positive_news, 1):
            md_content += f"""### {idx}. {article['title']}

- **출처**: {article['source']}
- **날짜**: {article['date_text']}
- **중요도**: {'⭐' * article['score']} ({article['positive_count']}개 호재 키워드)

**📝 요약**:
{article['content'] if article['content'] else '(요약 없음)'}

[📰 기사 원문 보기]({article['link']})

---

"""
    else:
        md_content += "호재성 뉴스가 없습니다.\n\n---\n\n"

    # 악재성 뉴스
    md_content += f"## 🔴 악재성 뉴스 ({len(negative_news)}건)\n\n"

    if negative_news:
        for idx, article in enumerate(negative_news, 1):
            md_content += f"""### {idx}. {article['title']}

- **출처**: {article['source']}
- **날짜**: {article['date_text']}
- **중요도**: {'⭐' * article['score']} ({article['negative_count']}개 악재 키워드)

**📝 요약**:
{article['content'] if article['content'] else '(요약 없음)'}

[📰 기사 원문 보기]({article['link']})

---

"""
    else:
        md_content += "악재성 뉴스가 없습니다.\n\n---\n\n"

    # 중립 뉴스 (최대 10개)
    md_content += f"## ⚪ 중립 뉴스 ({len(neutral_news)}건)\n\n"

    if neutral_news:
        display_count = min(len(neutral_news), 10)
        md_content += f"*최신 {display_count}건만 표시*\n\n"

        for idx, article in enumerate(neutral_news[:display_count], 1):
            md_content += f"""### {idx}. {article['title']}

- **출처**: {article['source']}
- **날짜**: {article['date_text']}

**📝 요약**:
{article['content'] if article['content'] else '(요약 없음)'}

[📰 기사 원문 보기]({article['link']})

---

"""
    else:
        md_content += "중립 뉴스가 없습니다.\n\n---\n\n"

    # 분석 인사이트
    md_content += """## 💡 분석 인사이트

### 📌 주요 포인트
"""

    # Top 3 호재/악재 추출
    if positive_news:
        md_content += "\n#### 🟢 주요 호재\n"
        for i, article in enumerate(positive_news[:3], 1):
            md_content += f"{i}. {article['title']}\n"

    if negative_news:
        md_content += "\n#### 🔴 주요 악재\n"
        for i, article in enumerate(negative_news[:3], 1):
            md_content += f"{i}. {article['title']}\n"

    md_content += """

### ⚠️ 투자 시 유의사항
- 본 분석은 키워드 기반 자동 분석으로 **참고용**으로만 사용하세요.
- 실제 투자 결정은 **전문가의 조언**과 **종합적인 분석**이 필요합니다.
- 뉴스의 중요도는 키워드 빈도를 기반으로 한 단순 지표입니다.
- 최신 뉴스일수록 시장에 미치는 영향이 클 수 있습니다.

---

## 📌 참고사항

- **분석 방법**: Ultimate Multi-Source 크롤링 + 키워드 기반 감성 분석
- **데이터 소스**:
  - Google News RSS (한글/영문 통합)
  - News API (영문 전문 뉴스, 월 500건 무료)
  - Naver News (한글 뉴스)
- **분석 키워드 수**: 호재/악재 키워드 각각 약 70개 (영문 포함)
- **카테고리별 맞춤 분석**: 미국증시, 거시경제, 산업테마 등 카테고리별 특화 키워드 적용
- **중복 제거**: 제목 기반 중복 제거로 고품질 뉴스만 선별

---

*🤖 Generated with Claude Code (Ultimate Multi-Source Version)*
*📅 Generated at: """ + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + "*"

    output_file = get_report_path(keyword, date_str)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(md_content)

    print(f"\n[OK] 뉴스 분석 리포트가 '{output_file}' 파일로 저장되었습니다.")

    return output_file

def safe_print(text):
    """이모지를 안전하게 출력합니다."""
    try:
        print(text)
    except UnicodeEncodeError:
        # 이모지 제거 후 출력
        text_clean = text.encode('ascii', 'ignore').decode('ascii')
        print(text_clean)

def main():
    """메인 함수"""
    print("=" * 80)
    safe_print("📰 Ultimate Multi-Source 뉴스 분석 도구")
    safe_print("   (Google News RSS + News API + Naver News)")
    print("=" * 80)

    # News API 키 확인
    if NEWS_API_KEY == 'YOUR_API_KEY_HERE':
        print("\n[WARNING] News API key is not configured!")
        print("   Using only Google RSS + Naver (News API skipped)")
        print("   Free signup: https://newsapi.org/")
        print("   Set environment variable: set NEWS_API_KEY=your_api_key")
        print()

    # 키워드 입력
    if len(sys.argv) > 1:
        keyword = sys.argv[1]
    else:
        keyword = input("\n분석할 키워드를 입력하세요 (종목명/테마/시장): ").strip()

    if not keyword:
        print("키워드를 입력해야 합니다.")
        return

    try:
        # 카테고리 자동 인식
        category = detect_category(keyword)
        safe_print(f"\n🏷️  인식된 카테고리: {category}")

        # 1. Ultimate 멀티 소스 뉴스 크롤링
        articles = crawl_ultimate_news(keyword, days=14)

        if not articles:
            print("수집된 뉴스가 없습니다.")
            return

        # 2. 감성 분석 (카테고리별 맞춤)
        safe_print(f"\n📊 뉴스 분석 중... (카테고리: {category})")
        analyzed = analyze_sentiment(articles, category)

        # 3. 개선된 리포트 생성
        output_file = generate_enhanced_report(keyword, analyzed, category)

        # 4. 요약 출력
        positive_count = sum(1 for a in analyzed if a['sentiment'] == '호재')
        negative_count = sum(1 for a in analyzed if a['sentiment'] == '악재')
        neutral_count = sum(1 for a in analyzed if a['sentiment'] == '중립')

        print("\n" + "=" * 80)
        safe_print("✅ 분석 완료!")
        print("=" * 80)
        safe_print(f"📰 전체 기사: {len(analyzed)}건")
        safe_print(f"🟢 호재성 기사: {positive_count}건 ({positive_count/len(analyzed)*100:.1f}%)")
        safe_print(f"🔴 악재성 기사: {negative_count}건 ({negative_count/len(analyzed)*100:.1f}%)")
        safe_print(f"⚪ 중립 기사: {neutral_count}건 ({neutral_count/len(analyzed)*100:.1f}%)")
        safe_print(f"\n🏷️  카테고리: {category}")
        safe_print(f"📁 저장 위치: {output_file}")
        print("=" * 80)

    except Exception as e:
        safe_print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
