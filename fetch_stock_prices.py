import sys
import os
from datetime import datetime
from pykrx import stock
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re

def get_stock_code(stock_name):
    """종목명으로 종목코드를 찾습니다."""
    try:
        # 전체 상장 종목 조회
        tickers = stock.get_market_ticker_list(market="ALL")

        for ticker in tickers:
            name = stock.get_market_ticker_name(ticker)
            if stock_name in name or name in stock_name:
                return ticker, name

        return None, None
    except Exception as e:
        print(f"종목코드 조회 실패: {e}")
        return None, None

def get_realtime_price_naver(stock_code):
    """네이버 금융에서 실시간 현재가를 가져옵니다."""
    try:
        url = f'https://finance.naver.com/item/main.nhn?code={stock_code}'
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # 현재가
        price_elem = soup.select_one('.no_today .blind')
        current_price = int(price_elem.text.replace(',', '')) if price_elem else None

        # 전일대비
        change_elem = soup.select_one('.no_exday .blind')
        change = change_elem.text if change_elem else None

        # 등락률
        rate_elem = soup.select_one('.no_exday + em .blind')
        change_rate = rate_elem.text if rate_elem else None

        # 시가, 고가, 저가
        today_list = soup.select('.new_totalinfo dl dd')

        open_price = None
        high_price = None
        low_price = None
        volume = None

        for item in today_list:
            label = item.select_one('em.txt_dsc')
            if label:
                label_text = label.text.strip()
                value_elem = item.select_one('.blind')

                if '시가' in label_text and value_elem:
                    open_price = int(value_elem.text.replace(',', ''))
                elif '고가' in label_text and value_elem:
                    high_price = int(value_elem.text.replace(',', ''))
                elif '저가' in label_text and value_elem:
                    low_price = int(value_elem.text.replace(',', ''))
                elif '거래량' in label_text and value_elem:
                    volume_text = value_elem.text.replace(',', '')
                    volume = int(volume_text) if volume_text.isdigit() else None

        # 시가총액 (네이버에서 제공)
        market_cap = None
        cap_elem = soup.select_one('em#_market_sum')
        if cap_elem:
            cap_text = cap_elem.text.replace(',', '').strip()
            market_cap = int(cap_text) * 100000000 if cap_text.isdigit() else None

        return {
            '종가': current_price,
            '시가': open_price,
            '고가': high_price,
            '저가': low_price,
            '거래량': volume,
            '전일대비': change,
            '등락률': change_rate,
            '시가총액': market_cap,
            'source': 'naver_realtime'
        }

    except Exception as e:
        print(f"네이버 금융 실시간 조회 실패: {e}")
        return None

def get_stock_info(stock_code, date_str=None):
    """특정 종목의 상세 정보를 가져옵니다."""

    if date_str is None:
        date_str = datetime.now().strftime('%Y%m%d')
    else:
        # YYYY-MM-DD 형식을 YYYYMMDD로 변환
        date_str = date_str.replace('-', '')

    try:
        # 1. 기본 시세 정보 (시가, 고가, 저가, 종가, 거래량)
        ohlcv = stock.get_market_ohlcv(date_str, date_str, stock_code)

        if ohlcv.empty:
            return None

        # 2. 시가총액 정보
        cap = stock.get_market_cap(date_str, date_str, stock_code)

        # 3. 거래 대금 및 거래량
        fundamental = stock.get_market_fundamental(date_str, date_str, stock_code)

        # 데이터 병합
        result = pd.concat([ohlcv, cap, fundamental], axis=1)

        # 중복 컬럼 제거
        result = result.loc[:, ~result.columns.duplicated()]

        return result

    except Exception as e:
        print(f"주가 정보 조회 실패: {e}")
        return None

def get_investor_trading(stock_code, date_str=None):
    """투자자별 거래 정보를 가져옵니다 (기관, 외국인 등)."""

    if date_str is None:
        date_str = datetime.now().strftime('%Y%m%d')
    else:
        date_str = date_str.replace('-', '')

    try:
        # 시작일과 종료일을 같게 설정 (당일만)
        trading = stock.get_market_trading_value_by_date(date_str, date_str, stock_code)

        if trading.empty:
            return None

        return trading

    except Exception as e:
        print(f"투자자별 거래 정보 조회 실패: {e}")
        return None

def format_number(num):
    """숫자를 읽기 쉬운 형식으로 변환합니다."""
    if pd.isna(num):
        return '-'

    if num >= 1_000_000_000_000:  # 조
        return f"{num/1_000_000_000_000:.2f}조"
    elif num >= 100_000_000:  # 억
        return f"{num/100_000_000:.2f}억"
    elif num >= 10_000:  # 만
        return f"{num/10_000:.2f}만"
    else:
        return f"{num:,.0f}"

def generate_stock_report(stock_name, date_str=None):
    """주가 정보 리포트를 생성합니다."""

    if date_str is None:
        date_str = datetime.now().strftime('%Y-%m-%d')

    print(f"\n{'='*80}")
    print(f"주가 정보 조회")
    print(f"{'='*80}")
    print(f"조회 종목: {stock_name}")
    print(f"조회 날짜: {date_str}")

    # 1. 종목코드 찾기
    print(f"\n종목코드 조회 중...")
    stock_code, stock_name_full = get_stock_code(stock_name)

    if not stock_code:
        print(f"'{stock_name}' 종목을 찾을 수 없습니다.")
        return None

    print(f"종목명: {stock_name_full} ({stock_code})")

    # 2. 당일 데이터인지 확인
    is_today = (date_str == datetime.now().strftime('%Y-%m-%d'))
    use_realtime = False

    # 2-1. 주가 정보 가져오기 (pykrx 시도)
    print(f"\n주가 정보 조회 중...")
    info = get_stock_info(stock_code, date_str)

    # 실제 조회된 날짜 확인
    actual_date = None
    if info is not None and not info.empty:
        actual_date = info.index[0].strftime('%Y-%m-%d')
        if actual_date != date_str:
            print(f"⚠️  요청 날짜: {date_str}, 실제 조회된 날짜: {actual_date}")
            print(f"⚠️  {date_str}의 데이터가 없어 가장 최근 거래일 데이터를 조회했습니다.")

    # 2-2. pykrx 데이터가 없으면 (당일 또는 휴장일) 네이버 실시간 데이터 사용
    if (info is None or info.empty) and is_today:
        print(f"pykrx 데이터 없음. 네이버 금융 실시간 데이터 조회 중...")
        realtime_data = get_realtime_price_naver(stock_code)

        if realtime_data:
            use_realtime = True
            print("네이버 금융 실시간 데이터 조회 성공!")
        else:
            print(f"{date_str} 날짜의 주가 정보가 없습니다. (휴장일이거나 데이터 없음)")
            return None
    elif info is None or info.empty:
        print(f"{date_str} 날짜의 주가 정보가 없습니다. (휴장일이거나 데이터 없음)")
        return None

    # 3. 투자자별 거래 정보 (pykrx만 제공)
    trading = None
    if not use_realtime:
        print(f"투자자별 거래 정보 조회 중...")
        trading = get_investor_trading(stock_code, date_str)

    # 4. 리포트 생성
    if use_realtime:
        # 네이버 실시간 데이터 사용
        row = realtime_data
        change_rate_text = row.get('등락률', '0%').replace('%', '').replace('+', '').replace(',', '')
        try:
            change_rate = float(change_rate_text)
        except:
            change_rate = 0
    else:
        # pykrx 데이터 사용
        row = info.iloc[0]
        # pykrx가 제공하는 등락률 사용 (전일 종가 대비)
        # OHLCV 데이터의 6번째 컬럼(인덱스 5)이 등락률
        if len(info.columns) >= 6:
            change_rate = row.iloc[5]  # 6번째 컬럼 = 등락률
        else:
            # 등락률 컬럼이 없으면 시가 대비로 계산 (fallback)
            if '종가' in info.columns and '시가' in info.columns:
                change_rate = ((row['종가'] - row['시가']) / row['시가'] * 100) if row['시가'] > 0 else 0
            else:
                change_rate = 0

    # 데이터 소스 표시
    data_source = "네이버 금융 실시간" if use_realtime else "한국거래소(KRX)"

    # 실제 데이터 날짜 표시
    date_info = f"**조회일시**: {date_str}"
    if actual_date and actual_date != date_str:
        date_info += f"\n**실제 데이터 날짜**: {actual_date} (요청 날짜의 데이터 없음)"

    report = f"""
# {stock_name_full} 주가 정보

**종목코드**: {stock_code}
{date_info}
**데이터 소스**: {data_source}

---

## 📊 시세 정보

| 구분 | 가격 |
|------|------|
| 시가 | {row.get('시가', 0):,}원 |
| 고가 | {row.get('고가', 0):,}원 |
| 저가 | {row.get('저가', 0):,}원 |
| 종가 | {row.get('종가', 0):,}원 |
| 등락률 | {change_rate:+.2f}% |

---

## 📈 거래 정보

| 구분 | 수치 |
|------|------|
| 거래량 | {format_number(row.get('거래량', 0))}주 |
"""

    # 거래대금은 pykrx만 제공
    if not use_realtime:
        report += f"| 거래대금 | {format_number(row.get('거래대금', 0))}원 |\n"

    report += "\n---\n\n## 💰 시가총액 정보\n\n| 구분 | 수치 |\n|------|------|\n"
    report += f"| 시가총액 | {format_number(row.get('시가총액', 0))}원 |\n"

    # 상장주식수는 pykrx만 제공
    if not use_realtime:
        report += f"| 상장주식수 | {format_number(row.get('상장주식수', 0))}주 |\n"

    report += "\n---\n"

    # 투자지표는 pykrx만 제공
    if not use_realtime:
        report += f"""
## 📊 투자지표

| 구분 | 수치 |
|------|------|
| PER (주가수익비율) | {row.get('PER', 0):.2f} |
| PBR (주가순자산비율) | {row.get('PBR', 0):.2f} |
| EPS (주당순이익) | {row.get('EPS', 0):,.0f}원 |
| BPS (주당순자산) | {row.get('BPS', 0):,.0f}원 |
| DIV (배당수익률) | {row.get('DIV', 0):.2f}% |
| DPS (주당배당금) | {row.get('DPS', 0):,.0f}원 |

---
"""

    # 투자자별 거래 정보 추가
    if trading is not None and not trading.empty:
        trading_row = trading.iloc[0]

        report += """
## 👥 투자자별 거래 정보 (순매수)

| 투자자 | 금액 |
|--------|------|
"""

        if '기관' in trading.columns:
            report += f"| 기관 | {format_number(trading_row.get('기관', 0))}원 |\n"
        if '외국인' in trading.columns:
            report += f"| 외국인 | {format_number(trading_row.get('외국인', 0))}원 |\n"
        if '개인' in trading.columns:
            report += f"| 개인 | {format_number(trading_row.get('개인', 0))}원 |\n"

        report += "\n---\n"

    # 참고사항
    if use_realtime:
        report += """
## 📌 참고사항

- 이 정보는 네이버 금융에서 제공하는 실시간 데이터입니다.
- 실시간 데이터는 시세 지연이 있을 수 있습니다 (약 20분).
- PER, PBR 등 상세 투자지표는 장 마감 후 조회 시 제공됩니다.
- 실제 투자 결정 시 전문가와 상담하세요.

---

*🤖 Generated with Claude Code*
"""
    else:
        report += """
## 📌 참고사항

- 이 정보는 한국거래소(KRX) 공식 데이터를 기반으로 합니다.
- PER, PBR 등의 투자지표는 참고용이며, 실제 투자 결정 시 전문가와 상담하세요.
- 거래량 및 거래대금은 해당 날짜 기준입니다.

---

*🤖 Generated with Claude Code*
"""

    # 리포트 저장
    output_file = get_report_path(stock_name_full, date_str)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"\n주가 정보 리포트가 '{output_file}' 파일로 저장되었습니다.")

    # 콘솔 출력
    print("\n" + "="*80)
    print("주가 정보 요약")
    print("="*80)
    print(f"종목명: {stock_name_full} ({stock_code})")
    print(f"데이터 소스: {data_source}")
    print(f"종가: {row.get('종가', 0):,}원 ({change_rate:+.2f}%)")
    print(f"거래량: {format_number(row.get('거래량', 0))}주")
    print(f"시가총액: {format_number(row.get('시가총액', 0))}원")
    if not use_realtime:
        print(f"PER: {row.get('PER', 0):.2f} / PBR: {row.get('PBR', 0):.2f}")
    print("="*80)

    return output_file

def get_report_path(stock_name, date_str=None):
    """리포트 경로를 반환합니다."""
    if date_str is None:
        date_str = datetime.now().strftime('%Y-%m-%d')

    # stock 폴더 생성
    report_dir = os.path.join('report', date_str, 'stock')
    os.makedirs(report_dir, exist_ok=True)

    # 파일명에서 사용할 수 없는 문자 제거
    safe_stock_name = re.sub(r'[\/*?:"<>|]', '', stock_name)

    return os.path.join(report_dir, f'stock_{safe_stock_name}.md')

def main():
    """메인 함수"""
    print("="*80)
    print("주가 정보 조회 도구 (pykrx)")
    print("="*80)

    # 종목명 입력
    if len(sys.argv) > 1:
        stock_name = sys.argv[1]
    else:
        stock_name = input("\n조회할 종목명을 입력하세요: ").strip()

    if not stock_name:
        print("종목명을 입력해야 합니다.")
        return

    # 날짜 입력 (선택)
    if len(sys.argv) > 2:
        date_str = sys.argv[2]
    else:
        date_input = input("조회 날짜 (YYYY-MM-DD, 엔터시 오늘): ").strip()
        date_str = date_input if date_input else None

    try:
        generate_stock_report(stock_name, date_str)
    except Exception as e:
        print(f"\n오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
