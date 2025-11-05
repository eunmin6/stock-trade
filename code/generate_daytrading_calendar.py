#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
데이트레이딩 월별 달력 생성 스크립트
- 평일(월~금)만 표시
- 만원 단위로 손익 표시
- 수익/손실 색상 구분
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
import calendar

def load_trading_results():
    """tradings 폴더에서 모든 거래 결과를 로드합니다."""
    report_dir = Path('report/tradings')
    results = {}

    # 모든 날짜별 md 파일 읽기
    for md_file in report_dir.glob('????-??-??.md'):
        date_str = md_file.stem

        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # 거래 타입별 수익 현황에서 데이트레이딩 정보 추출
            if '데이트레이딩' in content:
                # "| 데이트레이딩 | 3건 | -573,883원 |" 형식 파싱
                for line in content.split('\n'):
                    if '데이트레이딩' in line and '|' in line:
                        parts = [p.strip() for p in line.split('|')]
                        if len(parts) >= 4 and parts[1] == '데이트레이딩':
                            count_str = parts[2].replace('건', '').strip()
                            profit_str = parts[3].replace('원', '').replace(',', '').strip()

                            try:
                                count = int(count_str)
                                profit = int(profit_str)

                                results[date_str] = {
                                    'count': count,
                                    'profit': profit
                                }
                            except ValueError:
                                continue
                            break
        except Exception as e:
            print(f"Warning: {md_file} 파일 읽기 실패: {e}")
            continue

    return results

def generate_monthly_calendar(year, month, trading_results):
    """월별 달력을 생성합니다 (평일만)."""
    cal = calendar.monthcalendar(year, month)

    # 달력 헤더
    header = "| 월 | 화 | 수 | 목 | 금 |\n"
    separator = "|:--:|:--:|:--:|:--:|:--:|\n"

    rows = []
    for week in cal:
        row = []
        # 월(0), 화(1), 수(2), 목(3), 금(4)만 표시 (토(5), 일(6) 제외)
        for day_idx in range(5):  # 월~금만
            day = week[day_idx]
            if day == 0:
                row.append(" ")
            else:
                date_str = f"{year:04d}-{month:02d}-{day:02d}"

                if date_str in trading_results:
                    result = trading_results[date_str]
                    profit = result['profit']
                    count = result['count']

                    # 만원 단위로 표시
                    profit_10k = profit / 10000

                    # 수익/손실에 따라 이모지 선택
                    if profit > 0:
                        emoji = "🟢"
                        sign = "+"
                    elif profit < 0:
                        emoji = "🔴"
                        sign = ""
                    else:
                        emoji = "⚪"
                        sign = ""

                    # 만원 단위로 표시 (소수점 1자리)
                    cell = f"{day}<br/>{emoji}{sign}{profit_10k:.1f}만"
                else:
                    cell = f"{day}"

                row.append(cell)

        rows.append("| " + " | ".join(row) + " |")

    return header + separator + "\n".join(rows)

def calculate_monthly_stats(year, month, trading_results):
    """월별 통계를 계산합니다."""
    total_profit = 0
    total_count = 0
    trading_days = 0
    win_days = 0

    for date_str, result in trading_results.items():
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d')
            if date.year == year and date.month == month:
                trading_days += 1
                total_profit += result['profit']
                total_count += result['count']
                if result['profit'] > 0:
                    win_days += 1
        except:
            continue

    avg_profit = total_profit / trading_days if trading_days > 0 else 0
    win_rate = (win_days / trading_days * 100) if trading_days > 0 else 0

    return {
        'trading_days': trading_days,
        'total_profit': total_profit,
        'avg_profit': avg_profit,
        'win_rate': win_rate,
        'total_count': total_count,
        'win_days': win_days,
        'lose_days': trading_days - win_days
    }

def load_daily_trades(date_str):
    """특정 날짜의 거래별 상세 내역을 로드합니다."""
    md_file = Path(f'report/tradings/{date_str}.md')

    if not md_file.exists():
        return []

    trades = []

    try:
        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # "## 💰 거래별 손익 상세" 섹션 찾기
        if '## 💰 거래별 손익 상세' in content:
            lines = content.split('\n')
            in_table = False

            for line in lines:
                if '## 💰 거래별 손익 상세' in line:
                    in_table = True
                    continue

                if in_table:
                    # 테이블 끝 확인
                    if line.startswith('##') or line.startswith('---'):
                        break

                    # 데이터 행 파싱 (| 1 | 종목명 | 데이트레이딩 | ... |)
                    if line.startswith('|') and '데이트레이딩' in line:
                        parts = [p.strip() for p in line.split('|')]
                        if len(parts) >= 7:
                            try:
                                rank = parts[1]
                                stock = parts[2]
                                trade_type = parts[3]
                                profit_str = parts[6].replace('원', '').replace(',', '').strip()
                                return_str = parts[7].replace('%', '').strip()

                                profit = int(profit_str)
                                return_rate = float(return_str)

                                trades.append({
                                    'rank': rank,
                                    'stock': stock,
                                    'profit': profit,
                                    'return_rate': return_rate
                                })
                            except:
                                continue
    except Exception as e:
        print(f"Warning: {date_str} 거래 상세 로드 실패: {e}")

    return trades

def generate_daily_details(year, month, trading_results):
    """일별 상세 내역을 생성합니다."""
    details = []

    # 날짜순 정렬
    sorted_dates = sorted([d for d in trading_results.keys() if d.startswith(f"{year:04d}-{month:02d}")])

    for date_str in sorted_dates:
        result = trading_results[date_str]
        date = datetime.strptime(date_str, '%Y-%m-%d')
        weekday_kr = ['월', '화', '수', '목', '금', '토', '일'][date.weekday()]

        profit = result['profit']
        count = result['count']

        # 수익/손실 표시
        if profit > 0:
            emoji = "🟢"
            profit_sign = "+"
        elif profit < 0:
            emoji = "🔴"
            profit_sign = ""
        else:
            emoji = "⚪"
            profit_sign = ""

        # 거래별 상세 로드
        daily_trades = load_daily_trades(date_str)

        # 거래 테이블 생성
        trade_table = ""
        if daily_trades:
            trade_table = "\n| 순위 | 종목명 | 손익금액 | 수익률 |\n"
            trade_table += "|:----:|--------|----------:|--------:|\n"

            for trade in daily_trades:
                stock = trade['stock']
                trade_profit = trade['profit']
                return_rate = trade['return_rate']

                # 손익에 따라 파스텔 색상 적용
                # 큰 손실: 파스텔 블루 (#B3D9FF)
                # 큰 수익: 파스텔 레드 (#FFB3B3)
                if trade_profit < -100000:  # 10만원 이상 손실
                    color_start = '<span style="background-color: #B3D9FF; padding: 2px 4px; border-radius: 3px;">'
                    color_end = '</span>'
                elif trade_profit > 100000:  # 10만원 이상 수익
                    color_start = '<span style="background-color: #FFB3B3; padding: 2px 4px; border-radius: 3px;">'
                    color_end = '</span>'
                else:
                    color_start = ''
                    color_end = ''

                trade_sign = '+' if trade_profit > 0 else ''
                profit_display = f"{color_start}{trade_sign}{trade_profit:,}원{color_end}"

                # 수익률도 부호 추가
                return_sign = '+' if return_rate > 0 else ''
                return_display = f"{color_start}{return_sign}{return_rate:.2f}%{color_end}"

                trade_table += f"| {trade['rank']} | {stock} | {profit_display} | {return_display} |\n"

        detail = f"""#### {date_str} ({weekday_kr}) {emoji}
- 거래 건수: {count}건
- 총 손익: {profit_sign}{profit:,}원 ({profit_sign}{profit/10000:.1f}만원)
- [전체 리포트 보기](./{date_str}.md)
{trade_table}
"""
        details.append(detail)

    return "\n".join(details)

def generate_report():
    """데이트레이딩 월별 리포트를 생성합니다."""
    print("=" * 80)
    print("데이트레이딩 월별 달력 생성")
    print("=" * 80)

    # 거래 결과 로드
    trading_results = load_trading_results()
    print(f"\n총 {len(trading_results)}일의 데이트레이딩 데이터 로드 완료\n")

    if not trading_results:
        print("데이트레이딩 데이터가 없습니다.")
        return

    # 년월별로 그룹화
    year_months = set()
    for date_str in trading_results.keys():
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d')
            year_months.add((date.year, date.month))
        except:
            continue

    # 리포트 생성
    for year, month in sorted(year_months):
        print(f"[{year}년 {month}월] 달력 생성 중...")

        # 월별 달력
        calendar_md = generate_monthly_calendar(year, month, trading_results)

        # 월별 통계
        stats = calculate_monthly_stats(year, month, trading_results)

        # 일별 상세
        daily_details = generate_daily_details(year, month, trading_results)

        # 마크다운 생성
        md_content = f"""# 데이트레이딩 월별 성과

## {year}년 {month}월

{calendar_md}

---

## 📊 월간 통계

| 항목 | 값 |
|------|------|
| 총 거래일수 | {stats['trading_days']}일 |
| 총 거래 건수 | {stats['total_count']}건 |
| 총 손익 | {stats['total_profit']:,}원 ({stats['total_profit']/10000:.1f}만원) |
| 평균 손익 | {stats['avg_profit']:,.0f}원/일 ({stats['avg_profit']/10000:.1f}만원/일) |
| 승률 | {stats['win_rate']:.1f}% ({stats['win_days']}승 {stats['lose_days']}패) |

---

## 📅 일별 상세

{daily_details}

---

*🤖 Generated with Claude Code*
*Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""

        # 파일 저장
        output_file = f"report/tradings/데이트레이딩_{year:04d}-{month:02d}.md"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(md_content)

        print(f"  → {output_file} 생성 완료")

    print(f"\n{'='*80}")
    print("데이트레이딩 달력 생성 완료!")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    generate_report()
