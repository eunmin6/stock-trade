import re
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
import statistics

# 파일 경로 설정
report_dir = Path(__file__).parent.parent / "report" / "tradings"

# 분석할 파일 목록
files_to_analyze = [
    "2025-10-23.md",
    "2025-10-27.md",
    "2025-10-28.md",
    "2025-10-29.md",
    "2025-10-30.md",
    "2025-10-31.md",
    "2025-11-03.md",
    "2025-11-04.md",
    "2025-11-05.md"
]

class Trade:
    def __init__(self, stock_name, trade_type, start_time, end_time, duration,
                 split_buy, split_sell, profit, profit_rate):
        self.stock_name = stock_name
        self.trade_type = trade_type
        self.start_time = start_time
        self.end_time = end_time
        self.duration = duration
        self.split_buy = split_buy
        self.split_sell = split_sell
        self.profit = profit
        self.profit_rate = profit_rate
        self.is_win = profit > 0

    def get_start_hour(self):
        """시작 시간대 반환 (9시, 10시 등)"""
        return int(self.start_time.split(':')[0])

    def get_duration_minutes(self):
        """보유 시간을 분 단위로 반환"""
        match = re.match(r'(\d+)h (\d+)m', self.duration)
        if match:
            hours = int(match.group(1))
            minutes = int(match.group(2))
            return hours * 60 + minutes
        return 0

def parse_trade_line(line):
    """테이블 행에서 거래 정보 추출"""
    parts = [p.strip() for p in line.split('|')]
    if len(parts) < 15:
        return None

    try:
        # 순위, 종목명, 거래타입, 시작시간, 종료시간, 보유시간, 분할매수, 분할매도, ...
        stock_name = parts[2]
        trade_type = parts[3]
        start_time = parts[4]
        end_time = parts[5]
        duration = parts[6]
        split_buy = int(parts[7].replace('회', ''))
        split_sell = int(parts[8].replace('회', ''))

        # 손익금액 파싱
        profit_str = parts[13].replace('원', '').replace(',', '')
        if profit_str == 'nan':
            return None
        profit = int(profit_str)

        # 수익률 파싱
        profit_rate_str = parts[14].replace('%', '')
        if profit_rate_str in ['nan', '+nan', '-nan']:
            return None
        profit_rate = float(profit_rate_str)

        # 데이트레이딩만 분석
        if trade_type != '데이트레이딩':
            return None

        # 시작시간, 종료시간이 유효한지 확인
        if start_time == 'nan' or end_time == 'nan':
            return None

        return Trade(stock_name, trade_type, start_time, end_time, duration,
                    split_buy, split_sell, profit, profit_rate)
    except (ValueError, IndexError):
        return None

def analyze_trades():
    """모든 거래 데이터 수집 및 분석"""
    all_trades = []

    # 모든 파일에서 거래 데이터 수집
    for filename in files_to_analyze:
        file_path = report_dir / filename
        if not file_path.exists():
            continue

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # '거래별 손익 상세' 섹션 찾기
        match = re.search(r'## 💰 거래별 손익 상세\n\n.+?\n\|[-|]+\|\n((?:\|.+\n)+)', content)
        if not match:
            continue

        table_rows = match.group(1).strip().split('\n')
        for row in table_rows:
            trade = parse_trade_line(row)
            if trade:
                all_trades.append(trade)

    return all_trades

def analyze_by_start_hour(trades):
    """시작 시간대별 분석"""
    hour_stats = defaultdict(lambda: {'count': 0, 'wins': 0, 'total_profit': 0, 'profits': []})

    for trade in trades:
        hour = trade.get_start_hour()
        stats = hour_stats[hour]
        stats['count'] += 1
        if trade.is_win:
            stats['wins'] += 1
        stats['total_profit'] += trade.profit
        stats['profits'].append(trade.profit)

    # 결과 정리
    results = []
    for hour in sorted(hour_stats.keys()):
        stats = hour_stats[hour]
        win_rate = (stats['wins'] / stats['count'] * 100) if stats['count'] > 0 else 0
        avg_profit = stats['total_profit'] / stats['count'] if stats['count'] > 0 else 0
        results.append({
            'hour': hour,
            'count': stats['count'],
            'win_rate': win_rate,
            'total_profit': stats['total_profit'],
            'avg_profit': avg_profit
        })

    return results

def analyze_by_duration(trades):
    """보유 시간별 분석 (30분 단위)"""
    duration_stats = defaultdict(lambda: {'count': 0, 'wins': 0, 'total_profit': 0})

    for trade in trades:
        minutes = trade.get_duration_minutes()
        # 30분 단위로 그룹화
        duration_group = (minutes // 30) * 30
        stats = duration_stats[duration_group]
        stats['count'] += 1
        if trade.is_win:
            stats['wins'] += 1
        stats['total_profit'] += trade.profit

    # 결과 정리
    results = []
    for duration in sorted(duration_stats.keys()):
        stats = duration_stats[duration]
        win_rate = (stats['wins'] / stats['count'] * 100) if stats['count'] > 0 else 0
        avg_profit = stats['total_profit'] / stats['count'] if stats['count'] > 0 else 0
        results.append({
            'duration': duration,
            'count': stats['count'],
            'win_rate': win_rate,
            'total_profit': stats['total_profit'],
            'avg_profit': avg_profit
        })

    return results

def analyze_by_split_count(trades):
    """분할 매수/매도 횟수별 분석"""
    # 분할 매수 횟수별
    buy_stats = defaultdict(lambda: {'count': 0, 'wins': 0, 'total_profit': 0})
    # 분할 매도 횟수별
    sell_stats = defaultdict(lambda: {'count': 0, 'wins': 0, 'total_profit': 0})

    for trade in trades:
        # 분할 매수 분석
        buy_group = trade.split_buy
        if buy_group > 20:
            buy_group = 20  # 20회 이상은 하나로 묶음
        stats = buy_stats[buy_group]
        stats['count'] += 1
        if trade.is_win:
            stats['wins'] += 1
        stats['total_profit'] += trade.profit

        # 분할 매도 분석
        sell_group = trade.split_sell
        if sell_group > 20:
            sell_group = 20  # 20회 이상은 하나로 묶음
        stats = sell_stats[sell_group]
        stats['count'] += 1
        if trade.is_win:
            stats['wins'] += 1
        stats['total_profit'] += trade.profit

    # 결과 정리
    buy_results = []
    for count in sorted(buy_stats.keys()):
        stats = buy_stats[count]
        win_rate = (stats['wins'] / stats['count'] * 100) if stats['count'] > 0 else 0
        avg_profit = stats['total_profit'] / stats['count'] if stats['count'] > 0 else 0
        buy_results.append({
            'count': count,
            'trades': stats['count'],
            'win_rate': win_rate,
            'total_profit': stats['total_profit'],
            'avg_profit': avg_profit
        })

    sell_results = []
    for count in sorted(sell_stats.keys()):
        stats = sell_stats[count]
        win_rate = (stats['wins'] / stats['count'] * 100) if stats['count'] > 0 else 0
        avg_profit = stats['total_profit'] / stats['count'] if stats['count'] > 0 else 0
        sell_results.append({
            'count': count,
            'trades': stats['count'],
            'win_rate': win_rate,
            'total_profit': stats['total_profit'],
            'avg_profit': avg_profit
        })

    return buy_results, sell_results

def generate_markdown_report(trades, hour_analysis, duration_analysis, buy_analysis, sell_analysis):
    """마크다운 리포트 생성"""
    total_trades = len(trades)
    total_wins = sum(1 for t in trades if t.is_win)
    total_profit = sum(t.profit for t in trades)
    overall_win_rate = (total_wins / total_trades * 100) if total_trades > 0 else 0
    avg_profit = total_profit / total_trades if total_trades > 0 else 0

    report = f"""# 데이트레이딩 패턴 분석 리포트

**분석 일시**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**분석 기간**: 2025-10-23 ~ 2025-11-05
**총 거래 건수**: {total_trades}건 (데이트레이딩만)

---

## 📊 전체 성과 요약

| 항목 | 값 |
|------|------|
| 총 거래 건수 | {total_trades}건 |
| 승리 거래 | {total_wins}건 |
| 패배 거래 | {total_trades - total_wins}건 |
| 전체 승률 | {overall_win_rate:.1f}% |
| 총 손익 | {total_profit:,}원 |
| 평균 손익 | {avg_profit:,.0f}원/거래 |

---

## 🕐 진입 시간대별 분석

### 시간대별 성과

| 시간대 | 거래 건수 | 승률 | 총 손익 | 평균 손익 | 평가 |
|--------|----------|------|---------|-----------|------|
"""

    # 시간대별 데이터 추가
    for item in hour_analysis:
        hour = item['hour']
        count = item['count']
        win_rate = item['win_rate']
        total_profit = item['total_profit']
        avg_profit = item['avg_profit']

        # 평가 기준
        if win_rate >= 60 and avg_profit > 0:
            grade = "🌟 최고"
        elif win_rate >= 50 and avg_profit > 0:
            grade = "✅ 좋음"
        elif win_rate >= 40 or avg_profit > -50000:
            grade = "⚠️ 보통"
        else:
            grade = "❌ 나쁨"

        report += f"| {hour}시 | {count}건 | {win_rate:.1f}% | {total_profit:,}원 | {avg_profit:,.0f}원 | {grade} |\n"

    # 시간대별 인사이트
    best_hour = max(hour_analysis, key=lambda x: x['avg_profit'])
    worst_hour = min(hour_analysis, key=lambda x: x['avg_profit'])

    report += f"""
### 💡 시간대별 인사이트

**🌟 최고의 진입 시간대: {best_hour['hour']}시**
- 승률: {best_hour['win_rate']:.1f}%
- 평균 손익: {best_hour['avg_profit']:,.0f}원
- 거래 건수: {best_hour['count']}건

**❌ 최악의 진입 시간대: {worst_hour['hour']}시**
- 승률: {worst_hour['win_rate']:.1f}%
- 평균 손익: {worst_hour['avg_profit']:,.0f}원
- 거래 건수: {worst_hour['count']}건

**전략 제안**:
"""

    # 좋은 시간대와 나쁜 시간대 구분
    good_hours = [h for h in hour_analysis if h['win_rate'] >= 50 and h['avg_profit'] > 0]
    bad_hours = [h for h in hour_analysis if h['win_rate'] < 40 or h['avg_profit'] < 0]

    if good_hours:
        hours_list = ', '.join([f"{h['hour']}시" for h in good_hours])
        report += f"- ✅ **추천 진입 시간**: {hours_list}\n"

    if bad_hours:
        hours_list = ', '.join([f"{h['hour']}시" for h in bad_hours])
        report += f"- ❌ **회피 시간**: {hours_list}\n"

    report += """
---

## ⏱️ 보유 시간별 분석

### 보유 시간별 성과 (30분 단위)

| 보유 시간 | 거래 건수 | 승률 | 총 손익 | 평균 손익 | 평가 |
|----------|----------|------|---------|-----------|------|
"""

    # 보유 시간별 데이터 추가
    for item in duration_analysis:
        duration = item['duration']
        count = item['count']
        win_rate = item['win_rate']
        total_profit = item['total_profit']
        avg_profit = item['avg_profit']

        # 시간 표시 변환
        hours = duration // 60
        minutes = duration % 60
        if hours > 0:
            duration_str = f"{hours}h {minutes}m"
        else:
            duration_str = f"{minutes}m"

        # 평가 기준
        if win_rate >= 60 and avg_profit > 0:
            grade = "🌟 최고"
        elif win_rate >= 50 and avg_profit > 0:
            grade = "✅ 좋음"
        elif win_rate >= 40 or avg_profit > -50000:
            grade = "⚠️ 보통"
        else:
            grade = "❌ 나쁨"

        report += f"| {duration_str} | {count}건 | {win_rate:.1f}% | {total_profit:,}원 | {avg_profit:,.0f}원 | {grade} |\n"

    # 보유 시간별 인사이트
    best_duration = max(duration_analysis, key=lambda x: x['avg_profit'])
    worst_duration = min(duration_analysis, key=lambda x: x['avg_profit'])

    best_hours = best_duration['duration'] // 60
    best_minutes = best_duration['duration'] % 60
    worst_hours = worst_duration['duration'] // 60
    worst_minutes = worst_duration['duration'] % 60

    report += f"""
### 💡 보유 시간별 인사이트

**🌟 최적 보유 시간: {best_hours}h {best_minutes}m**
- 승률: {best_duration['win_rate']:.1f}%
- 평균 손익: {best_duration['avg_profit']:,.0f}원
- 거래 건수: {best_duration['count']}건

**❌ 최악 보유 시간: {worst_hours}h {worst_minutes}m**
- 승률: {worst_duration['win_rate']:.1f}%
- 평균 손익: {worst_duration['avg_profit']:,.0f}원
- 거래 건수: {worst_duration['count']}건

**전략 제안**:
"""

    # 좋은 보유 시간대와 나쁜 보유 시간대 구분
    good_durations = [d for d in duration_analysis if d['win_rate'] >= 50 and d['avg_profit'] > 0]
    bad_durations = [d for d in duration_analysis if d['win_rate'] < 40 or d['avg_profit'] < -20000]

    if good_durations:
        duration_ranges = []
        for d in good_durations:
            h = d['duration'] // 60
            m = d['duration'] % 60
            if h > 0:
                duration_ranges.append(f"{h}h {m}m")
            else:
                duration_ranges.append(f"{m}m")
        report += f"- ✅ **추천 보유 시간**: {', '.join(duration_ranges)}\n"

    if bad_durations:
        duration_ranges = []
        for d in bad_durations:
            h = d['duration'] // 60
            m = d['duration'] % 60
            if h > 0:
                duration_ranges.append(f"{h}h {m}m")
            else:
                duration_ranges.append(f"{m}m")
        report += f"- ❌ **주의 보유 시간**: {', '.join(duration_ranges)}\n"

    # 단기 vs 장기 비교
    short_term = [d for d in duration_analysis if d['duration'] <= 60]  # 1시간 이하
    long_term = [d for d in duration_analysis if d['duration'] > 180]  # 3시간 이상

    if short_term:
        short_avg_profit = sum(d['avg_profit'] * d['count'] for d in short_term) / sum(d['count'] for d in short_term)
        short_win_rate = sum(d['win_rate'] * d['count'] for d in short_term) / sum(d['count'] for d in short_term)
        report += f"\n- 📌 **단기 보유 (1시간 이하)**: 평균 {short_avg_profit:,.0f}원, 승률 {short_win_rate:.1f}%\n"

    if long_term:
        long_avg_profit = sum(d['avg_profit'] * d['count'] for d in long_term) / sum(d['count'] for d in long_term)
        long_win_rate = sum(d['win_rate'] * d['count'] for d in long_term) / sum(d['count'] for d in long_term)
        report += f"- 📌 **장기 보유 (3시간 이상)**: 평균 {long_avg_profit:,.0f}원, 승률 {long_win_rate:.1f}%\n"

    report += """
---

## 🔄 분할 매수 횟수별 분석

### 분할 매수 횟수별 성과

| 매수 횟수 | 거래 건수 | 승률 | 총 손익 | 평균 손익 | 평가 |
|----------|----------|------|---------|-----------|------|
"""

    # 분할 매수 데이터 추가
    for item in buy_analysis:
        count = item['count']
        trades = item['trades']
        win_rate = item['win_rate']
        total_profit = item['total_profit']
        avg_profit = item['avg_profit']

        count_str = f"{count}회" if count < 20 else "20회+"

        # 평가 기준
        if win_rate >= 60 and avg_profit > 0:
            grade = "🌟 최고"
        elif win_rate >= 50 and avg_profit > 0:
            grade = "✅ 좋음"
        elif win_rate >= 40 or avg_profit > -50000:
            grade = "⚠️ 보통"
        else:
            grade = "❌ 나쁨"

        report += f"| {count_str} | {trades}건 | {win_rate:.1f}% | {total_profit:,}원 | {avg_profit:,.0f}원 | {grade} |\n"

    # 분할 매수 인사이트
    best_buy = max(buy_analysis, key=lambda x: x['avg_profit'])
    worst_buy = min(buy_analysis, key=lambda x: x['avg_profit'])

    report += f"""
### 💡 분할 매수 인사이트

**🌟 최적 분할 매수 횟수: {best_buy['count']}회**
- 승률: {best_buy['win_rate']:.1f}%
- 평균 손익: {best_buy['avg_profit']:,.0f}원
- 거래 건수: {best_buy['trades']}건

**❌ 최악 분할 매수 횟수: {worst_buy['count']}회**
- 승률: {worst_buy['win_rate']:.1f}%
- 평균 손익: {worst_buy['avg_profit']:,.0f}원
- 거래 건수: {worst_buy['trades']}건

**전략 제안**:
"""

    # 좋은 매수 횟수와 나쁜 매수 횟수 구분
    good_buys = [b for b in buy_analysis if b['win_rate'] >= 50 and b['avg_profit'] > 0]
    bad_buys = [b for b in buy_analysis if b['win_rate'] < 40 or b['avg_profit'] < -20000]

    if good_buys:
        buy_list = ', '.join([f"{b['count']}회" for b in good_buys])
        report += f"- ✅ **추천 분할 매수**: {buy_list}\n"

    if bad_buys:
        buy_list = ', '.join([f"{b['count']}회" for b in bad_buys])
        report += f"- ❌ **회피 분할 매수**: {buy_list}\n"

    # 분할 매수 패턴 분석
    few_buys = [b for b in buy_analysis if b['count'] <= 3]
    many_buys = [b for b in buy_analysis if b['count'] >= 10]

    if few_buys:
        few_avg = sum(b['avg_profit'] * b['trades'] for b in few_buys) / sum(b['trades'] for b in few_buys)
        few_wr = sum(b['win_rate'] * b['trades'] for b in few_buys) / sum(b['trades'] for b in few_buys)
        report += f"\n- 📌 **소량 분할 (1-3회)**: 평균 {few_avg:,.0f}원, 승률 {few_wr:.1f}%\n"

    if many_buys:
        many_avg = sum(b['avg_profit'] * b['trades'] for b in many_buys) / sum(b['trades'] for b in many_buys)
        many_wr = sum(b['win_rate'] * b['trades'] for b in many_buys) / sum(b['trades'] for b in many_buys)
        report += f"- 📌 **다량 분할 (10회 이상)**: 평균 {many_avg:,.0f}원, 승률 {many_wr:.1f}%\n"

    report += """
---

## 🔄 분할 매도 횟수별 분석

### 분할 매도 횟수별 성과

| 매도 횟수 | 거래 건수 | 승률 | 총 손익 | 평균 손익 | 평가 |
|----------|----------|------|---------|-----------|------|
"""

    # 분할 매도 데이터 추가
    for item in sell_analysis:
        count = item['count']
        trades = item['trades']
        win_rate = item['win_rate']
        total_profit = item['total_profit']
        avg_profit = item['avg_profit']

        count_str = f"{count}회" if count < 20 else "20회+"

        # 평가 기준
        if win_rate >= 60 and avg_profit > 0:
            grade = "🌟 최고"
        elif win_rate >= 50 and avg_profit > 0:
            grade = "✅ 좋음"
        elif win_rate >= 40 or avg_profit > -50000:
            grade = "⚠️ 보통"
        else:
            grade = "❌ 나쁨"

        report += f"| {count_str} | {trades}건 | {win_rate:.1f}% | {total_profit:,}원 | {avg_profit:,.0f}원 | {grade} |\n"

    # 분할 매도 인사이트
    best_sell = max(sell_analysis, key=lambda x: x['avg_profit'])
    worst_sell = min(sell_analysis, key=lambda x: x['avg_profit'])

    report += f"""
### 💡 분할 매도 인사이트

**🌟 최적 분할 매도 횟수: {best_sell['count']}회**
- 승률: {best_sell['win_rate']:.1f}%
- 평균 손익: {best_sell['avg_profit']:,.0f}원
- 거래 건수: {best_sell['trades']}건

**❌ 최악 분할 매도 횟수: {worst_sell['count']}회**
- 승률: {worst_sell['win_rate']:.1f}%
- 평균 손익: {worst_sell['avg_profit']:,.0f}원
- 거래 건수: {worst_sell['trades']}건

**전략 제안**:
"""

    # 좋은 매도 횟수와 나쁜 매도 횟수 구분
    good_sells = [s for s in sell_analysis if s['win_rate'] >= 50 and s['avg_profit'] > 0]
    bad_sells = [s for s in sell_analysis if s['win_rate'] < 40 or s['avg_profit'] < -20000]

    if good_sells:
        sell_list = ', '.join([f"{s['count']}회" for s in good_sells])
        report += f"- ✅ **추천 분할 매도**: {sell_list}\n"

    if bad_sells:
        sell_list = ', '.join([f"{s['count']}회" for s in bad_sells])
        report += f"- ❌ **회피 분할 매도**: {sell_list}\n"

    # 분할 매도 패턴 분석
    few_sells = [s for s in sell_analysis if s['count'] <= 3]
    many_sells = [s for s in sell_analysis if s['count'] >= 10]

    if few_sells:
        few_avg = sum(s['avg_profit'] * s['trades'] for s in few_sells) / sum(s['trades'] for s in few_sells)
        few_wr = sum(s['win_rate'] * s['trades'] for s in few_sells) / sum(s['trades'] for s in few_sells)
        report += f"\n- 📌 **일괄 매도 (1-3회)**: 평균 {few_avg:,.0f}원, 승률 {few_wr:.1f}%\n"

    if many_sells:
        many_avg = sum(s['avg_profit'] * s['trades'] for s in many_sells) / sum(s['trades'] for s in many_sells)
        many_wr = sum(s['win_rate'] * s['trades'] for s in many_sells) / sum(s['trades'] for s in many_sells)
        report += f"- 📌 **다량 분할 (10회 이상)**: 평균 {many_avg:,.0f}원, 승률 {many_wr:.1f}%\n"

    report += """
---

## 🎯 종합 전략 제안

### 💎 최적 트레이딩 조합
"""

    # 최적 조합 추천
    top_hours = sorted([h for h in hour_analysis if h['count'] >= 3], key=lambda x: x['avg_profit'], reverse=True)[:3]
    top_durations = sorted([d for d in duration_analysis if d['count'] >= 3], key=lambda x: x['avg_profit'], reverse=True)[:3]
    top_buys = sorted([b for b in buy_analysis if b['trades'] >= 3], key=lambda x: x['avg_profit'], reverse=True)[:3]
    top_sells = sorted([s for s in sell_analysis if s['trades'] >= 3], key=lambda x: x['avg_profit'], reverse=True)[:3]

    report += "\n**🌟 가장 수익성 높은 패턴**:\n\n"

    if top_hours:
        hours_str = ', '.join([f"{h['hour']}시" for h in top_hours])
        report += f"1. **진입 시간**: {hours_str}\n"

    if top_durations:
        dur_list = []
        for d in top_durations:
            h = d['duration'] // 60
            m = d['duration'] % 60
            if h > 0:
                dur_list.append(f"{h}h {m}m")
            else:
                dur_list.append(f"{m}m")
        report += f"2. **보유 시간**: {', '.join(dur_list)}\n"

    if top_buys:
        buys_str = ', '.join([f"{b['count']}회" for b in top_buys])
        report += f"3. **분할 매수**: {buys_str}\n"

    if top_sells:
        sells_str = ', '.join([f"{s['count']}회" for s in top_sells])
        report += f"4. **분할 매도**: {sells_str}\n"

    # 피해야 할 패턴
    bottom_hours = sorted([h for h in hour_analysis if h['count'] >= 3], key=lambda x: x['avg_profit'])[:2]
    bottom_durations = sorted([d for d in duration_analysis if d['count'] >= 3], key=lambda x: x['avg_profit'])[:2]

    report += "\n**❌ 피해야 할 패턴**:\n\n"

    if bottom_hours:
        hours_str = ', '.join([f"{h['hour']}시" for h in bottom_hours])
        report += f"1. **진입 회피 시간**: {hours_str}\n"

    if bottom_durations:
        dur_list = []
        for d in bottom_durations:
            h = d['duration'] // 60
            m = d['duration'] % 60
            if h > 0:
                dur_list.append(f"{h}h {m}m")
            else:
                dur_list.append(f"{m}m")
        report += f"2. **주의 보유 시간**: {', '.join(dur_list)}\n"

    report += """
### 📋 실전 적용 체크리스트

거래 전 다음 사항을 확인하세요:

#### ✅ 진입 전 체크
"""

    if good_hours:
        hours_list = ', '.join([f"{h['hour']}시" for h in good_hours])
        report += f"- [ ] 현재 시간이 추천 시간대인가? ({hours_list})\n"

    if bad_hours:
        hours_list = ', '.join([f"{h['hour']}시" for h in bad_hours])
        report += f"- [ ] 회피 시간대가 아닌가? ({hours_list})\n"

    report += """- [ ] 시총 1조~3조 종목인가?
- [ ] 거래대금 1,000억~3,000억인가?
- [ ] 급등 테마가 명확한가?

#### ✅ 거래 중 체크
"""

    if good_durations:
        report += f"- [ ] 목표 보유 시간을 설정했는가?\n"

    report += """- [ ] 손절 라인 -2%를 설정했는가?
- [ ] 분할 매수 계획을 세웠는가?
- [ ] 익절 목표(+3%, +5%)를 설정했는가?

#### ✅ 청산 전 체크
- [ ] 손익 목표에 도달했는가?
- [ ] 보유 시간이 적정한가?
- [ ] 장 마감 30분 전인가?

---

## 📈 상관관계 요약

### 핵심 발견 사항

"""

    # 상관관계 요약
    report += f"""
1. **진입 시간과 수익의 관계**
   - 최고 시간대: {best_hour['hour']}시 (평균 {best_hour['avg_profit']:,.0f}원)
   - 최악 시간대: {worst_hour['hour']}시 (평균 {worst_hour['avg_profit']:,.0f}원)
   - 차이: {best_hour['avg_profit'] - worst_hour['avg_profit']:,.0f}원

2. **보유 시간과 수익의 관계**
   - 최적 보유: {best_hours}h {best_minutes}m (평균 {best_duration['avg_profit']:,.0f}원)
   - 최악 보유: {worst_hours}h {worst_minutes}m (평균 {worst_duration['avg_profit']:,.0f}원)
   - 차이: {best_duration['avg_profit'] - worst_duration['avg_profit']:,.0f}원

3. **분할 매수와 수익의 관계**
   - 최적 매수: {best_buy['count']}회 (평균 {best_buy['avg_profit']:,.0f}원)
   - 최악 매수: {worst_buy['count']}회 (평균 {worst_buy['avg_profit']:,.0f}원)
   - 차이: {best_buy['avg_profit'] - worst_buy['avg_profit']:,.0f}원

4. **분할 매도와 수익의 관계**
   - 최적 매도: {best_sell['count']}회 (평균 {best_sell['avg_profit']:,.0f}원)
   - 최악 매도: {worst_sell['count']}회 (평균 {worst_sell['avg_profit']:,.0f}원)
   - 차이: {best_sell['avg_profit'] - worst_sell['avg_profit']:,.0f}원

### 🎓 결론 및 개선 방향

"""

    # 개선 방향 제시
    if best_hour['avg_profit'] > avg_profit * 2:
        report += f"1. **진입 시간 최적화가 매우 중요**: {best_hour['hour']}시 진입이 평균보다 {(best_hour['avg_profit'] / avg_profit - 1) * 100:.0f}% 더 높은 수익\n"

    if best_duration['avg_profit'] > avg_profit * 2:
        report += f"2. **보유 시간 관리가 핵심**: 적정 보유 시간 준수 시 평균보다 {(best_duration['avg_profit'] / avg_profit - 1) * 100:.0f}% 더 높은 수익\n"

    report += f"""
3. **분할 매매 전략 개선 필요**: 최적 분할 매수/매도 횟수를 따를 경우 큰 수익 차이 발생

4. **규칙 준수의 중요성**: 최적 패턴을 따르는 거래와 그렇지 않은 거래의 수익 차이가 큼

### 💰 예상 개선 효과

현재 평균 손익: {avg_profit:,.0f}원/거래

**최적 패턴 적용 시 예상**:
"""

    # 개선 시뮬레이션
    potential_profit = (best_hour['avg_profit'] + best_duration['avg_profit'] + best_buy['avg_profit'] + best_sell['avg_profit']) / 4
    improvement = potential_profit - avg_profit
    improvement_rate = (improvement / abs(avg_profit) * 100) if avg_profit != 0 else 0

    report += f"""- 예상 평균 손익: {potential_profit:,.0f}원/거래
- 예상 개선 폭: {improvement:,.0f}원/거래 ({improvement_rate:+.0f}%)
- 일 10회 거래 시 예상 일일 개선: {improvement * 10:,.0f}원
- 월 20일 거래 시 예상 월간 개선: {improvement * 10 * 20:,.0f}원

---

*🤖 Generated with Claude Code*
*분석 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""

    return report

def main():
    print("데이트레이딩 패턴 분석 시작...\n")

    # 거래 데이터 수집
    trades = analyze_trades()
    print(f"총 {len(trades)}건의 데이트레이딩 거래 수집 완료\n")

    # 각종 분석 수행
    print("시간대별 분석 중...")
    hour_analysis = analyze_by_start_hour(trades)

    print("보유 시간별 분석 중...")
    duration_analysis = analyze_by_duration(trades)

    print("분할 매수/매도 횟수별 분석 중...")
    buy_analysis, sell_analysis = analyze_by_split_count(trades)

    # 리포트 생성
    print("\n마크다운 리포트 생성 중...")
    report = generate_markdown_report(trades, hour_analysis, duration_analysis, buy_analysis, sell_analysis)

    # 파일 저장
    output_path = Path(__file__).parent.parent / "report" / "데이트레이딩_패턴_분석.md"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"\n분석 완료! 리포트 저장 위치: {output_path}")
    print("\n주요 발견:")
    print(f"- 총 거래: {len(trades)}건")
    print(f"- 전체 승률: {sum(1 for t in trades if t.is_win) / len(trades) * 100:.1f}%")
    print(f"- 평균 손익: {sum(t.profit for t in trades) / len(trades):,.0f}원")

if __name__ == "__main__":
    main()
