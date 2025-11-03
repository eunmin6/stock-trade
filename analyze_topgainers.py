import sys
import os
import re
from datetime import datetime
from bs4 import BeautifulSoup
from fetch_stock_prices import get_stock_info

def parse_topgainers_html(html_file):
    """topgainers.html 파일을 파싱하여 급등종목 리스트를 추출합니다."""

    with open(html_file, 'r', encoding='utf-8') as f:
        html_content = f.read()

    soup = BeautifulSoup(html_content, 'html.parser')

    # 날짜 정보 추출
    date_td = soup.find('td', string=re.compile(r'\d{4}년 \d{1,2}월 \d{1,2}일'))
    if date_td:
        date_text = date_td.text.strip()
        match = re.search(r'(\d{4})년 (\d{1,2})월 (\d{1,2})일', date_text)
        if match:
            year, month, day = match.groups()
            date_str = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
    else:
        # 파일 경로에서 날짜 추출
        date_str = None

    # 테이블에서 종목 정보 추출
    stocks = []
    table = soup.find('table', class_='tbl')

    if table:
        rows = table.find_all('tr')[1:]  # 헤더 제외

        for row in rows:
            cols = row.find_all('td')
            if len(cols) < 3:
                continue

            # 종목명, 코드, 현재가, 상승률 추출
            first_col = cols[0]
            link = first_col.find('a')
            if not link:
                continue

            # 전체 텍스트 추출 (링크 + <br> 태그 이후 내용)
            col_text = first_col.get_text(separator='|||').strip()
            text_parts = [part.strip() for part in col_text.split('|||') if part.strip() and part.strip() not in ['(', ')']]

            if len(text_parts) < 4:
                continue

            # 종목명과 코드
            stock_name = text_parts[0]
            stock_code = text_parts[1].strip('()')

            # 현재가
            price_text = text_parts[2].replace(',', '').replace('원', '')
            try:
                price = int(float(price_text))
            except:
                continue

            # 상승률 (퍼센트 부분)
            change_rate_text = text_parts[3].strip('()').replace('%', '').replace('+', '')
            try:
                change_rate = float(change_rate_text)
            except:
                continue

            # 상한가 일수
            limit_days = cols[1].text.strip()
            is_limit = bool(limit_days)

            # 급등 사유
            reason = cols[2].text.strip()

            stocks.append({
                'name': stock_name,
                'code': stock_code,
                'price': price,
                'change_rate': change_rate,
                'limit_days': limit_days,
                'is_limit': is_limit,
                'reason': reason
            })

    return stocks, date_str

def get_trading_values(stocks, date_str):
    """종목 리스트의 거래대금을 조회합니다."""

    print(f"\n거래대금 조회 중... (날짜: {date_str})")
    trading_values = {}

    for stock in stocks:
        stock_code = stock['code']
        stock_name = stock['name']

        try:
            info = get_stock_info(stock_code, date_str)

            if info is not None and not info.empty:
                trading_value = info['거래대금'].iloc[0]
                trading_value_eok = trading_value / 100_000_000
                trading_values[stock_code] = trading_value_eok
                print(f"  {stock_name:20s} ({stock_code}): {trading_value_eok:>10.0f}억원")
            else:
                trading_values[stock_code] = 0
                print(f"  {stock_name:20s} ({stock_code}): 데이터 없음")
        except Exception as e:
            trading_values[stock_code] = 0
            print(f"  {stock_name:20s} ({stock_code}): 오류 - {e}")

    return trading_values

def simplify_reason(reason):
    """급등 사유를 간결하게 정리합니다 (60자 제한)."""
    # 공백 정리
    reason = re.sub(r'\s+', ' ', reason).strip()

    # 60자 이상이면 자르기
    if len(reason) > 60:
        return reason[:57] + '...'
    return reason

def analyze_themes(stocks):
    """급등 사유를 분석하여 주요 테마를 추출합니다 (키워드 기반)."""

    print("\n  테마 분석 중 (키워드 기반)...")

    themes = {}

    for stock in stocks:
        reason = stock['reason']

        if '엔비디아' in reason or 'AI' in reason or '인공지능' in reason or '지능형로봇' in reason or '로봇' in reason:
            themes.setdefault('AI/로봇', []).append(stock['name'])

        if '유리 기판' in reason or '글래스 기판' in reason:
            themes.setdefault('유리기판', []).append(stock['name'])

        if '반도체' in reason or 'HBM' in reason:
            themes.setdefault('반도체', []).append(stock['name'])

        if '태양광' in reason or '전력' in reason or '전선' in reason:
            themes.setdefault('전력/에너지', []).append(stock['name'])

        if '스마트팩토리' in reason or '자동화' in reason:
            themes.setdefault('스마트팩토리', []).append(stock['name'])

        if '2차전지' in reason or 'ESS' in reason or '배터리' in reason:
            themes.setdefault('2차전지', []).append(stock['name'])

        if '5G' in reason or '통신' in reason:
            themes.setdefault('5G/통신', []).append(stock['name'])

        if '방위산업' in reason or '국방' in reason:
            themes.setdefault('방위산업', []).append(stock['name'])

    sorted_themes = sorted(themes.items(), key=lambda x: len(x[1]), reverse=True)
    print(f"  테마 분석 완료: {len(sorted_themes)}개 테마 발견")
    return sorted_themes

def generate_topgainers_md(stocks, trading_values, date_str, output_file):
    """급등종목 마크다운 리포트를 생성합니다."""

    # 거래대금 500억원 이상 필터링
    MIN_TRADING_VALUE = 500

    # 상한가 종목 (거래대금 500억원 이상)
    limit_stocks = [s for s in stocks if s['is_limit'] and trading_values.get(s['code'], 0) >= MIN_TRADING_VALUE]

    # 급등종목 (상한가 제외, 거래대금 500억원 이상)
    surge_stocks = [s for s in stocks if not s['is_limit'] and trading_values.get(s['code'], 0) >= MIN_TRADING_VALUE]

    # 테마 분석
    all_filtered_stocks = limit_stocks + surge_stocks
    themes = analyze_themes(all_filtered_stocks)

    # 날짜 파싱
    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    date_display = date_obj.strftime('%Y년 %m월 %d일')

    # 평균 상승률 계산
    avg_change_rate = sum(s['change_rate'] for s in stocks) / len(stocks) if stocks else 0

    md_content = f"""# 오늘의 급등종목 분석 리포트

**분석 일시**: {date_display} 17시 07분
**분석 대상 날짜**: {date_str}
**출처**: 인포스탁 - 증시요약

---

## 🎯 주요 급등 테마 분석

"""

    # 동적 테마 생성
    for idx, (theme_name, theme_stocks) in enumerate(themes[:5], 1):
        md_content += f"""### {idx}. {theme_name}
- **관련 종목 수**: {len(theme_stocks)}개
- **주요 종목**: {', '.join(theme_stocks[:10])}{'...' if len(theme_stocks) > 10 else ''}

"""

    md_content += f"""---

## 📊 시장 분석

### 전체 시장 동향
- **분석 대상**: 급등종목 {len(stocks)}개
- **평균 상승률**: {avg_change_rate:.2f}%
- **최고 상승률**: {max(stocks, key=lambda x: x['change_rate'])['name']} ({max(stocks, key=lambda x: x['change_rate'])['change_rate']:.2f}%)

### 주요 테마
"""

    for theme_name, theme_stocks in themes[:3]:
        md_content += f"- **{theme_name}**: {len(theme_stocks)}개 종목\n"

    md_content += f"""
---

## 📊 요약

- **전체 급등종목**: {len(stocks)}개
- **상한가 종목**: {len([s for s in stocks if s['is_limit']])}개 (거래대금 500억원 이상: {len(limit_stocks)}개)
- **급등종목 (상한가 제외, 거래대금 500억원 이상)**: {len(surge_stocks)}개
- **평균 상승률**: {avg_change_rate:.2f}%
- **최고 상승률**: {max(stocks, key=lambda x: x['change_rate'])['name']} ({max(stocks, key=lambda x: x['change_rate'])['change_rate']:.2f}%)

---

## 🔥 상한가 종목 ({len(limit_stocks)}개, 거래대금 500억원 이상)

| 순위 | 종목명 | 종목코드 | 현재가 | 상승률 | 거래대금 | 상한가 일수 | 급등 사유 |
|------|--------|----------|--------|--------|----------|------------|-----------|
"""

    for idx, stock in enumerate(limit_stocks, 1):
        trading_val = trading_values.get(stock['code'], 0)
        reason = simplify_reason(stock['reason'])
        limit_days = stock['limit_days'] if stock['limit_days'] else '-'

        md_content += f"| {idx} | {stock['name']} | {stock['code']} | {stock['price']:,}원 | +{stock['change_rate']:.2f}% | {trading_val:,.0f}억원 | {limit_days}일 | {reason} |\n"

    md_content += f"""
---

## 📈 급등종목 TOP (상한가 제외, 거래대금 500억원 이상)

| 순위 | 종목명 | 종목코드 | 현재가 | 상승률 | 거래대금 | 급등 사유 |
|------|--------|----------|--------|--------|----------|-----------|
"""

    for idx, stock in enumerate(surge_stocks, 1):
        trading_val = trading_values.get(stock['code'], 0)
        reason = simplify_reason(stock['reason'])

        md_content += f"| {idx} | {stock['name']} | {stock['code']} | {stock['price']:,}원 | +{stock['change_rate']:.2f}% | {trading_val:,.0f}억원 | {reason} |\n"

    md_content += """
---

## 📌 참고사항

- 이 분석은 장 마감 시점 기준입니다.
- 급등 사유는 인포스탁 증시요약 자료를 기반으로 작성되었습니다.
- 거래대금 500억원 미만 종목은 제외되었습니다.
- 실제 투자 결정은 전문가의 조언과 종합적인 분석이 필요합니다.
- 단기 급등은 변동성이 크므로 신중한 접근이 필요합니다.

---

*🤖 Generated with Claude Code*
"""

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(md_content)

    print(f"\n급등종목 리포트가 '{output_file}' 파일로 저장되었습니다.")

def main():
    """메인 함수"""

    if len(sys.argv) < 2:
        print("사용법: python analyze_topgainers.py YYYY-MM-DD")
        print("예시: python analyze_topgainers.py 2025-11-03")
        return

    date_str = sys.argv[1]

    # HTML 파일 경로
    html_file = os.path.join('data', date_str, 'topgainers.html')

    if not os.path.exists(html_file):
        print(f"오류: '{html_file}' 파일을 찾을 수 없습니다.")
        return

    print(f"=== 급등종목 분석 시작 ===")
    print(f"날짜: {date_str}")
    print(f"입력: {html_file}")

    # 1. HTML 파싱
    print("\n1. HTML 파일 파싱 중...")
    stocks, parsed_date = parse_topgainers_html(html_file)

    if parsed_date:
        date_str = parsed_date

    print(f"   총 {len(stocks)}개 종목 발견")

    # 2. 거래대금 조회
    print("\n2. 거래대금 조회 중...")
    trading_values = get_trading_values(stocks, date_str)

    # 3. 마크다운 리포트 생성
    print("\n3. 마크다운 리포트 생성 중...")
    output_dir = os.path.join('report', date_str)
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, 'topgainers.md')

    generate_topgainers_md(stocks, trading_values, date_str, output_file)

    print("\n=== 완료 ===")

if __name__ == "__main__":
    main()
