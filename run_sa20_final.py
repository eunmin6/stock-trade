"""
SA20: 종목분석 - 시가총액 + 텍스트 차트 포함
"""
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from pykrx import stock
import time
import json
import re
import sys
import io
import numpy as np

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

stock_name = "아모레퍼시픽"
stock_code = "090430"

print(f"\n{'='*80}")
print(f"SA20 종목분석: {stock_name} ({stock_code})")
print(f"{'='*80}\n")

# ===== 1. 뉴스 수집 =====
print("단계 1: 뉴스 수집")

def parse_date(date_text):
    try:
        now = datetime.now()
        if '분 전' in date_text or '분전' in date_text:
            minutes = int(re.search(r'(\d+)', date_text).group(1))
            return now - timedelta(minutes=minutes)
        elif '시간 전' in date_text or '시간전' in date_text:
            hours = int(re.search(r'(\d+)', date_text).group(1))
            return now - timedelta(hours=hours)
        elif '일 전' in date_text or '일전' in date_text:
            days = int(re.search(r'(\d+)', date_text).group(1))
            return now - timedelta(days=days)
        else:
            date_match = re.search(r'(\d{4})\.(\d{1,2})\.(\d{1,2})', date_text)
            if date_match:
                year, month, day = date_match.groups()
                return datetime(int(year), int(month), int(day))
        return None
    except:
        return None

end_date = datetime.now()
start_date = end_date - timedelta(days=30)  # 1개월로 확대
base_url = "https://search.naver.com/search.naver"
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

articles = []

for page in range(1, 4):
    # 종목명과 코드를 모두 사용해서 검색 범위 확대
    params = {'where': 'news', 'query': stock_code, 'start': (page - 1) * 10 + 1, 'sort': '1'}
    try:
        response = requests.get(base_url, params=params, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        news_items = soup.select('.o2YzmBxKhEuKOM4uNxFM')

        if not news_items:
            break

        for item in news_items:
            try:
                title_link = item.select_one('a[data-heatmap-target=".tit"]')
                if not title_link:
                    continue

                link = title_link.get('href', '')
                title_span = title_link.select_one('span')
                if title_span:
                    for mark in title_span.find_all('mark'):
                        mark.unwrap()
                    title = title_span.get_text(strip=True)
                else:
                    title = title_link.get_text(strip=True)

                if not title or len(title) < 5:
                    continue

                press_link = item.select_one('a[data-heatmap-target=".prof"]')
                press = press_link.get_text(strip=True) if press_link else '출처 미상'

                body_link = item.select_one('a[data-heatmap-target=".body"]')
                if body_link:
                    body_span = body_link.select_one('span')
                    if body_span:
                        for mark in body_span.find_all('mark'):
                            mark.unwrap()
                        content = body_span.get_text(strip=True)
                    else:
                        content = body_link.get_text(strip=True)
                else:
                    content = ''

                date_text = ''
                date_elem = item.find('span', {'data-sds-comp': 'TimeLapse'})
                if date_elem:
                    date_text = date_elem.get_text(strip=True)
                else:
                    all_text = item.get_text()
                    date_patterns = [r'\d+시간 전', r'\d+일 전', r'\d+분 전', r'\d{4}\.\d{2}\.\d{2}\.']
                    for pattern in date_patterns:
                        match = re.search(pattern, all_text)
                        if match:
                            date_text = match.group().rstrip('.')
                            break

                article_date = parse_date(date_text)
                # 날짜 필터링을 완화하여 모든 뉴스 수집
                # if article_date and article_date < start_date:
                #     break

                articles.append({'title': title, 'link': link, 'press': press, 'date': date_text, 'content': content})
            except:
                continue

        time.sleep(1)
    except:
        break

print(f"  뉴스 {len(articles)}건 수집 완료\n")

# ===== 2. 기술적 분석 =====
print("단계 2: 기술적 분석 (시가총액 + 텍스트 차트)")

end_dt = datetime.now()
start_dt = end_dt - timedelta(days=1095)
end_str = end_dt.strftime('%Y%m%d')
start_str = start_dt.strftime('%Y%m%d')

df = stock.get_market_ohlcv_by_date(start_str, end_str, stock_code)

# 시가총액 (가장 최근 거래일)
latest_date = df.index[-1].strftime('%Y%m%d')
cap_df = stock.get_market_cap_by_date(latest_date, latest_date, stock_code)
if not cap_df.empty:
    market_cap = int(cap_df.iloc[0]['시가총액'])
    market_cap_uk = int(market_cap / 100000000)
else:
    # fallback: 현재가 * 상장주식수 추정
    market_cap_uk = int(current_price * 1000000 / 100000000)  # 임시 추정

current_price = int(df.iloc[-1]['종가'])
week52_high = int(df['고가'].tail(252).max())
week52_low = int(df['저가'].tail(252).min())
avg_3y_price = int(df['종가'].mean())

ma5 = int(df['종가'].tail(5).mean())
ma20 = int(df['종가'].tail(20).mean())
ma60 = int(df['종가'].tail(60).mean())
ma120 = int(df['종가'].tail(120).mean())

avg_3y_volume = int(df['거래량'].mean())
avg_1m_volume = int(df['거래량'].tail(20).mean())
volatility_3m = df['종가'].tail(60).pct_change().std() * 100

recent_6m = df.tail(120)
supports = sorted(recent_6m.nsmallest(3, '저가')['저가'].astype(int).tolist())
resistances = sorted(recent_6m.nlargest(3, '고가')['고가'].astype(int).tolist(), reverse=True)

print(f"  시가총액: {market_cap_uk:,}억원")
print(f"  현재가: {current_price:,}원\n")

# 텍스트 차트 생성
df_3m = df.tail(60)
prices = df_3m['종가'].values
dates = df_3m.index

min_price = int(prices.min() / 1000) * 1000
max_price = int(prices.max() / 1000) * 1000 + 1000

height = 12
normalized = (prices - min_price) / (max_price - min_price) * (height - 1)

chart_lines = []
for i in range(height - 1, -1, -1):
    price_label = int(min_price + (max_price - min_price) * i / (height - 1)) // 1000
    line = f"{price_label:2d} ┤"

    for j, val in enumerate(normalized):
        if abs(val - i) < 0.5:
            line += "●"
        elif val > i:
            line += "│"
        else:
            line += " "

    chart_lines.append(line)

x_axis = "   └" + "─" * len(normalized) + "┘"

date_labels = "    "
for i in range(0, len(dates), max(1, len(dates)//12)):
    date_labels += dates[i].strftime('%m/%d') + "  "

text_chart = '\n'.join(chart_lines) + '\n' + x_axis + '\n' + date_labels

print("  텍스트 차트 생성 완료\n")

# 데이터 저장
with open('news_data.json', 'w', encoding='utf-8') as f:
    json.dump({
        'stock_code': stock_code,
        'stock_name': stock_name,
        'analysis_date': datetime.now().strftime('%Y-%m-%d'),
        'news_count': len(articles),
        'news': articles
    }, f, ensure_ascii=False, indent=2)

with open('technical_data.json', 'w', encoding='utf-8') as f:
    json.dump({
        'market_cap_uk': market_cap_uk,
        'current_price': current_price,
        'week52_high': week52_high,
        'week52_low': week52_low,
        'avg_3y_price': avg_3y_price,
        'ma5': ma5,
        'ma20': ma20,
        'ma60': ma60,
        'ma120': ma120,
        'avg_3y_volume': avg_3y_volume,
        'avg_1m_volume': avg_1m_volume,
        'volatility_3m': round(volatility_3m, 2),
        'supports': supports,
        'resistances': resistances,
        'text_chart': text_chart
    }, f, ensure_ascii=False, indent=2)

print("데이터 수집 완료. 리포트 생성 진행...\n")
