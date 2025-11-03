import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time
import os
import sys
import re

def get_report_path(stock_name, date_str=None):
    """뉴스 리포트 경로를 반환합니다."""
    if date_str is None:
        date_str = datetime.now().strftime('%Y-%m-%d')

    # news 폴더 생성
    report_dir = os.path.join('report', date_str, 'news')
    os.makedirs(report_dir, exist_ok=True)

    # 파일명에서 사용할 수 없는 문자 제거
    safe_stock_name = re.sub(r'[\\/*?:"<>|]', '', stock_name)
    return os.path.join(report_dir, f'news_{safe_stock_name}.md')

def crawl_naver_news(stock_name, days=14):
    """네이버 뉴스를 크롤링합니다."""
    print(f"\n'{stock_name}' 관련 뉴스 수집 중...")
    print(f"수집 기간: 최근 {days}일")

    # 날짜 계산
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    # 네이버 뉴스 검색 URL
    base_url = "https://search.naver.com/search.naver"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    articles = []

    # 여러 페이지 수집 (최대 3페이지)
    for page in range(1, 4):
        params = {
            'where': 'news',
            'query': stock_name,
            'start': (page - 1) * 10 + 1,
            'sort': '1'  # 최신순 정렬
        }

        try:
            response = requests.get(base_url, params=params, headers=headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # 뉴스 기사 검색 (새로운 HTML 구조)
            news_items = soup.select('.vs1RfKE1eTzMZ5RqnhIv')

            if not news_items:
                print(f"  페이지 {page}: 기사를 찾을 수 없습니다.")
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
                        # <mark> 태그 제거
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
                    print(f"  기사 파싱 중 오류: {e}")
                    continue

            print(f"  페이지 {page}: {len(news_items)}개 기사 발견")

            # 요청 간격 (네이버 서버 부하 방지)
            time.sleep(1)

        except requests.RequestException as e:
            print(f"  페이지 {page} 요청 실패: {e}")
            break

    # 날짜순 정렬 (최신순)
    articles.sort(key=lambda x: x['date'] if x['date'] else datetime.min, reverse=True)

    print(f"\n총 {len(articles)}개의 기사를 수집했습니다.\n")

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

def analyze_sentiment(articles):
    """기사의 호재/악재를 분석합니다. (키워드 기반 간단 분석)"""

    # 호재 키워드
    positive_keywords = [
        '상승', '호재', '증가', '성장', '확대', '개선', '흑자', '수주', '계약',
        '신규', '출시', '개발', '성공', '호조', '상향', '긍정', '투자', '협력',
        '제휴', '특허', '수출', '실적', '배당', '증설', '확장', '진출'
    ]

    # 악재 키워드
    negative_keywords = [
        '하락', '악재', '감소', '축소', '부진', '적자', '취소', '지연', '실패',
        '하향', '부정', '리스크', '우려', '손실', '적자', '감사', '규제', '소송',
        '사고', '문제', '위반', '중단', '폐기', '철수', '파산', '구조조정'
    ]

    analyzed = []

    for article in articles:
        text = article['title'] + ' ' + article['content']

        # 키워드 카운트
        positive_count = sum(1 for keyword in positive_keywords if keyword in text)
        negative_count = sum(1 for keyword in negative_keywords if keyword in text)

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

        analyzed.append({
            **article,
            'sentiment': sentiment,
            'score': score,
            'positive_count': positive_count,
            'negative_count': negative_count
        })

    return analyzed

def generate_news_report(stock_name, analyzed_articles, date_str=None):
    """뉴스 분석 리포트를 마크다운으로 생성합니다."""

    if date_str is None:
        date_str = datetime.now().strftime('%Y-%m-%d')

    # 호재/악재/중립 분류
    positive_news = [a for a in analyzed_articles if a['sentiment'] == '호재']
    negative_news = [a for a in analyzed_articles if a['sentiment'] == '악재']
    neutral_news = [a for a in analyzed_articles if a['sentiment'] == '중립']

    md_content = f"""# {stock_name} 뉴스 분석 리포트

**분석 일시**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**분석 대상 날짜**: {date_str}
**수집 기간**: 최근 14일

---

## 📊 요약

| 구분 | 건수 |
|------|------|
| 전체 기사 | {len(analyzed_articles)}건 |
| 호재성 기사 | {len(positive_news)}건 |
| 악재성 기사 | {len(negative_news)}건 |
| 중립 기사 | {len(neutral_news)}건 |

---

## 🟢 호재성 뉴스 ({len(positive_news)}건)

"""

    if positive_news:
        for idx, article in enumerate(positive_news, 1):
            md_content += f"""### {idx}. {article['title']}

- **언론사**: {article['source']}
- **날짜**: {article['date_text']}
- **영향도**: {'⭐' * article['score']}

**요약**:
{article['content']}

[기사 원문 보기]({article['link']})

---

"""
    else:
        md_content += "호재성 뉴스가 없습니다.\n\n---\n\n"

    md_content += f"""## 🔴 악재성 뉴스 ({len(negative_news)}건)

"""

    if negative_news:
        for idx, article in enumerate(negative_news, 1):
            md_content += f"""### {idx}. {article['title']}

- **언론사**: {article['source']}
- **날짜**: {article['date_text']}
- **영향도**: {'⭐' * article['score']}

**요약**:
{article['content']}

[기사 원문 보기]({article['link']})

---

"""
    else:
        md_content += "악재성 뉴스가 없습니다.\n\n---\n\n"

    md_content += f"""## ⚪ 중립 뉴스 ({len(neutral_news)}건)

"""

    if neutral_news:
        for idx, article in enumerate(neutral_news[:5], 1):  # 최대 5개만 표시
            md_content += f"""### {idx}. {article['title']}

- **언론사**: {article['source']}
- **날짜**: {article['date_text']}

**요약**:
{article['content']}

[기사 원문 보기]({article['link']})

---

"""
    else:
        md_content += "중립 뉴스가 없습니다.\n\n---\n\n"

    md_content += """
## 📌 참고사항

- 이 분석은 키워드 기반 자동 분석으로 참고용으로만 사용하세요.
- 실제 투자 결정은 전문가의 조언과 종합적인 분석이 필요합니다.
- 뉴스의 영향도는 키워드 빈도를 기반으로 한 단순 지표입니다.

---

*🤖 Generated with Claude Code*
"""

    output_file = get_report_path(stock_name, date_str)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(md_content)

    print(f"\n뉴스 분석 리포트가 '{output_file}' 파일로 저장되었습니다.")

    return output_file

def main():
    """메인 함수"""
    print("=" * 80)
    print("주식 뉴스 분석 도구")
    print("=" * 80)

    # 종목명 입력
    if len(sys.argv) > 1:
        stock_name = sys.argv[1]
    else:
        stock_name = input("\n분석할 종목명을 입력하세요: ").strip()

    if not stock_name:
        print("종목명을 입력해야 합니다.")
        return

    try:
        # 1. 뉴스 크롤링
        articles = crawl_naver_news(stock_name, days=14)

        if not articles:
            print("수집된 뉴스가 없습니다.")
            return

        # 2. 감성 분석
        print("뉴스 분석 중...")
        analyzed = analyze_sentiment(articles)

        # 3. 리포트 생성
        output_file = generate_news_report(stock_name, analyzed)

        # 4. 요약 출력
        positive_count = sum(1 for a in analyzed if a['sentiment'] == '호재')
        negative_count = sum(1 for a in analyzed if a['sentiment'] == '악재')
        neutral_count = sum(1 for a in analyzed if a['sentiment'] == '중립')

        print("\n" + "=" * 80)
        print("분석 완료!")
        print("=" * 80)
        print(f"전체 기사: {len(analyzed)}건")
        print(f"호재성 기사: {positive_count}건")
        print(f"악재성 기사: {negative_count}건")
        print(f"중립 기사: {neutral_count}건")
        print("=" * 80)

    except Exception as e:
        print(f"\n오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
