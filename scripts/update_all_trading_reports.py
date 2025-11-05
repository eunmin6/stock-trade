"""
모든 날짜의 거래 리포트에 시간 정보 추가하는 스크립트

all-orders.xlsx 파일에서 날짜별 주문 데이터를 추출하고
report/tradings/*.md 파일의 거래별 손익 상세 테이블에
시작시간, 종료시간, 보유시간, 분할매수, 분할매도 정보를 추가합니다.
"""

import pandas as pd
import re
from datetime import datetime
import os

def extract_timing_from_all_orders(orders_df, target_date):
    """
    all-orders.xlsx에서 특정 날짜의 종목별 타이밍 정보 추출

    Args:
        orders_df: all-orders.xlsx DataFrame
        target_date: 'YYYY-MM-DD' 형식의 날짜

    Returns:
        dict: {종목명: {first_buy, last_sell, duration, buy_count, sell_count}}
    """
    print(f"\n=== Processing {target_date} ===")

    # 날짜 필터링 - 첫 번째 컬럼에서
    date_mask = orders_df.iloc[:, 0].astype(str).str.contains(target_date, na=False)
    date_data = orders_df[date_mask]

    if len(date_data) == 0:
        print(f"  No data found for {target_date}")
        return {}

    print(f"  Found {len(date_data)} rows")

    # 주문유형(매수/매도)과 체결시간 추출
    # all-orders.xlsx의 구조: 홀수 행에 주문 정보, 짝수 행에 상세 정보
    results = {}

    # 간단한 방법: 체결 행만 필터링
    # 상세정보가 있는 행(매매구분이 있는 행)만 사용
    valid_rows = date_data[date_data.iloc[:, 1].astype(str).str.contains('매수|매도', na=False)]

    if len(valid_rows) == 0:
        print(f"  No valid trading rows found")
        return {}

    # 종목별로 그룹화
    for stock_name in valid_rows.iloc[:, 4].unique():
        if pd.isna(stock_name) or stock_name == '종목명':
            continue

        stock_data = valid_rows[valid_rows.iloc[:, 4] == stock_name]

        # 매수/매도 구분
        buy_data = stock_data[stock_data.iloc[:, 1].astype(str).str.contains('매수', na=False)]
        sell_data = stock_data[stock_data.iloc[:, 1].astype(str).str.contains('매도', na=False)]

        # 체결시간 추출 (컬럼 9)
        def extract_time(df):
            times = []
            for val in df.iloc[:, 9]:
                time_str = str(val)
                # HH:MM:SS 패턴 찾기
                match = re.search(r'(\d{2}):(\d{2}):(\d{2})', time_str)
                if match:
                    times.append(match.group())
            return times

        buy_times = extract_time(buy_data)
        sell_times = extract_time(sell_data)

        if buy_times and sell_times:
            first_buy = min(buy_times)
            last_sell = max(sell_times)
            buy_count = len(buy_times)
            sell_count = len(sell_times)

            # 보유시간 계산
            try:
                t1 = datetime.strptime(first_buy, '%H:%M:%S')
                t2 = datetime.strptime(last_sell, '%H:%M:%S')
                duration = t2 - t1
                hours = duration.seconds // 3600
                minutes = (duration.seconds % 3600) // 60
                duration_str = f"{hours}h {minutes}m"
            except:
                duration_str = "N/A"

            results[stock_name] = {
                'first_buy': first_buy,
                'last_sell': last_sell,
                'duration': duration_str,
                'buy_count': buy_count,
                'sell_count': sell_count
            }

            print(f"  ✓ {stock_name}: {first_buy} -> {last_sell} ({duration_str})")

    return results


def update_md_file(md_path, timing_info):
    """
    md 파일의 거래별 손익 상세 테이블에 시간 정보 추가

    Args:
        md_path: md 파일 경로
        timing_info: extract_timing_from_all_orders의 결과
    """
    print(f"\n  Updating {os.path.basename(md_path)}...")

    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 기존 테이블 찾기 (## 💰 거래별 손익 상세 섹션)
    # 패턴: | 순위 | 종목명 | ... |
    table_pattern = r'(## 💰 거래별 손익 상세\n\n\|[^\n]+\n\|[-:| ]+\n)((?:\|[^\n]+\n)+)'

    match = re.search(table_pattern, content)
    if not match:
        print(f"  ⚠ Table not found in {md_path}")
        return False

    table_header = match.group(1)
    table_rows = match.group(2)

    # 헤더에 시간 컬럼이 이미 있는지 확인
    if '시작시간' in table_header:
        print(f"  ℹ Already updated, skipping")
        return False

    # 새로운 헤더 생성
    header_line = table_header.split('\n')[0]
    separator_line = table_header.split('\n')[1]

    # | 순위 | 종목명 | 거래타입 | ... 형식에서
    # | 순위 | 종목명 | 거래타입 | 시작시간 | 종료시간 | 보유시간 | 분할매수 | 분할매도 | ... 로 변경

    # 거래타입 다음에 시간 정보 추가
    new_header = header_line.replace('| 거래타입 |', '| 거래타입 | 시작시간 | 종료시간 | 보유시간 | 분할매수 | 분할매도 |')
    new_separator = separator_line.replace('|----------|', '|----------|----------|----------|----------|----------|----------|')

    new_table_header = f"{new_header}\n{new_separator}\n"

    # 각 행 업데이트
    new_rows = []
    for row in table_rows.strip().split('\n'):
        if not row.strip() or not row.startswith('|'):
            continue

        cells = [c.strip() for c in row.split('|')[1:-1]]  # 양 끝 빈 셀 제거

        if len(cells) < 2:
            new_rows.append(row)
            continue

        # 종목명 추출 (2번째 셀, 0-indexed로 1)
        stock_name = cells[1].strip()

        # timing_info에서 해당 종목 정보 찾기
        timing = timing_info.get(stock_name, {})

        if timing:
            # 거래타입(cells[2]) 다음에 시간 정보 삽입
            new_cells = cells[:3] + [
                timing.get('first_buy', 'N/A'),
                timing.get('last_sell', 'N/A'),
                timing.get('duration', 'N/A'),
                f"{timing.get('buy_count', 0)}회",
                f"{timing.get('sell_count', 0)}회"
            ] + cells[3:]
        else:
            # 정보가 없으면 N/A로 채움
            new_cells = cells[:3] + ['N/A', 'N/A', 'N/A', 'N/A', 'N/A'] + cells[3:]

        new_row = '| ' + ' | '.join(new_cells) + ' |'
        new_rows.append(new_row)

    new_table_rows = '\n'.join(new_rows) + '\n'

    # 전체 테이블 교체
    new_table = new_table_header + new_table_rows
    new_content = content.replace(match.group(0), new_table)

    # 파일 저장
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print(f"  ✓ Updated successfully")
    return True


def main():
    """메인 실행 함수"""
    print("="*80)
    print("거래 리포트 업데이트 스크립트")
    print("="*80)

    # all-orders.xlsx 로드
    orders_path = 'D:/AI/stock-trade/data/orders/all-orders.xlsx'
    print(f"\nLoading {orders_path}...")

    try:
        all_orders = pd.read_excel(orders_path)
        print(f"✓ Loaded {len(all_orders)} rows")
    except Exception as e:
        print(f"✗ Error loading file: {e}")
        return

    # 처리할 날짜 목록
    dates = [
        '2025-10-23', '2025-10-27', '2025-10-28', '2025-10-29',
        '2025-10-30', '2025-10-31', '2025-11-03', '2025-11-04', '2025-11-05'
    ]

    # 각 날짜별로 처리
    updated_count = 0

    for date in dates:
        # 타이밍 정보 추출
        timing_info = extract_timing_from_all_orders(all_orders, date)

        if not timing_info:
            print(f"  ⚠ No timing info extracted for {date}")
            continue

        # 해당 날짜의 md 파일 찾기
        md_path = f'D:/AI/stock-trade/report/tradings/{date}.md'

        if not os.path.exists(md_path):
            print(f"  ⚠ File not found: {md_path}")
            continue

        # md 파일 업데이트
        if update_md_file(md_path, timing_info):
            updated_count += 1

    print("\n" + "="*80)
    print(f"✓ 완료: {updated_count}/{len(dates)}개 파일 업데이트됨")
    print("="*80)


if __name__ == '__main__':
    main()
