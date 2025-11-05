"""
period-orders.xlsx 파일 파싱 스크립트

데이터 구조:
- 1개 주문 = 2행(row) × 11열(column)
- Row 0: [날짜, ?, ?, 종목코드, ?, ?, ?, ?, ?, ?, ?]
- Row 1: [날짜, 종목명, ?, ?, 체결수량, 체결단가, ?, ?, ?, 체결시간, ?]

추출 정보:
- 날짜: (1, 0)
- 종목명: (1, 1)
- 종목코드: (0, 3)
- 체결수량: (1, 4)
- 체결단가: (1, 5)
- 체결시간: (1, 9)
"""

import pandas as pd
import json
from datetime import datetime
import re


def parse_period_orders(excel_path):
    """
    period-orders.xlsx 파일을 파싱하여 JSON 형식으로 변환

    Args:
        excel_path: 엑셀 파일 경로

    Returns:
        dict: 파싱된 주문 데이터
    """
    print(f"Loading {excel_path}...")

    # 엑셀 파일 로드
    df = pd.read_excel(excel_path, header=None)

    print(f"Total rows: {len(df)}")
    print(f"Processing in pairs (2 rows = 1 order)...")

    orders = []
    parsed_count = 0
    skipped_count = 0

    # 2행씩 묶어서 처리
    for i in range(0, len(df), 2):
        if i + 1 >= len(df):
            print(f"Warning: Odd number of rows at index {i}, skipping last row")
            break

        row0 = df.iloc[i]
        row1 = df.iloc[i + 1]

        try:
            # 데이터 추출
            date_raw = row1.iloc[0]
            stock_name = row1.iloc[1]
            stock_code = row0.iloc[3]
            quantity = row1.iloc[4]
            price = row1.iloc[5]
            time_raw = row1.iloc[9]

            # 데이터 검증 및 변환
            # 1. 날짜 변환
            if pd.isna(date_raw):
                skipped_count += 1
                continue

            date_str = str(date_raw)
            if ' ' in date_str:
                date = date_str.split(' ')[0]
            else:
                date = date_str

            # 2. 종목명 검증
            if pd.isna(stock_name) or stock_name == '종목명':
                skipped_count += 1
                continue

            # 3. 종목코드 검증
            if pd.isna(stock_code):
                skipped_count += 1
                continue
            stock_code = str(stock_code).strip()

            # 4. 수량/가격 변환
            if pd.isna(quantity) or pd.isna(price):
                skipped_count += 1
                continue

            quantity = int(quantity)
            price = int(price)
            amount = quantity * price

            # 5. 시간 추출 (HH:MM:SS 패턴)
            time_str = str(time_raw)
            time_match = re.search(r'(\d{2}:\d{2}:\d{2})', time_str)
            if time_match:
                time = time_match.group(1)
            else:
                # 시간 정보가 없으면 스킵 (미체결 주문일 가능성)
                skipped_count += 1
                continue

            # 주문 데이터 생성
            order = {
                'date': date,
                'stock_code': stock_code,
                'stock_name': stock_name,
                'quantity': quantity,
                'price': price,
                'time': time,
                'amount': amount
            }

            orders.append(order)
            parsed_count += 1

        except Exception as e:
            print(f"Error parsing rows {i}-{i+1}: {e}")
            skipped_count += 1
            continue

    print(f"\n✓ Parsed {parsed_count} orders")
    print(f"✗ Skipped {skipped_count} rows")

    # 결과 생성
    result = {
        'file': excel_path.split('/')[-1],
        'parsed_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'total_orders': parsed_count,
        'orders': orders
    }

    return result


def save_to_json(data, output_path):
    """JSON 파일로 저장"""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n✓ Saved to {output_path}")


def group_by_date(orders_data):
    """날짜별로 주문 그룹화"""
    from collections import defaultdict

    grouped = defaultdict(list)

    for order in orders_data['orders']:
        date = order['date']
        grouped[date].append(order)

    print(f"\n📅 Dates found: {len(grouped)}")
    for date, orders in sorted(grouped.items()):
        print(f"  {date}: {len(orders)} orders")

    return grouped


def main():
    """메인 실행 함수"""
    print("="*80)
    print("period-orders.xlsx 파싱 스크립트")
    print("="*80)

    # 파일 경로
    input_path = 'D:/AI/stock-trade/data/orders/period-orders.xlsx'
    output_path = 'D:/AI/stock-trade/data/orders/period-orders.json'

    # 파싱
    result = parse_period_orders(input_path)

    # JSON 저장
    save_to_json(result, output_path)

    # 날짜별 그룹화
    grouped = group_by_date(result)

    # 날짜별 파일로 저장 (선택사항)
    for date, orders in grouped.items():
        date_output = f'D:/AI/stock-trade/data/orders/{date}.json'
        date_data = {
            'date': date,
            'total_orders': len(orders),
            'orders': orders
        }
        save_to_json(date_data, date_output)

    print("\n" + "="*80)
    print("✓ 완료!")
    print("="*80)


if __name__ == '__main__':
    main()
