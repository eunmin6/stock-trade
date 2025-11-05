import re
from pathlib import Path
from collections import defaultdict

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

class BigWinner:
    def __init__(self, stock_name, trade_type, start_time, end_time, duration,
                 split_buy, split_sell, market_cap, trade_volume, profit, profit_rate, date):
        self.stock_name = stock_name
        self.trade_type = trade_type
        self.start_time = start_time
        self.end_time = end_time
        self.duration = duration
        self.split_buy = split_buy
        self.split_sell = split_sell
        self.market_cap = market_cap  # 억 단위
        self.trade_volume = trade_volume  # 억 단위
        self.profit = profit
        self.profit_rate = profit_rate
        self.date = date

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

    def get_market_cap_group(self):
        """시총 구간 반환"""
        cap = self.market_cap
        if cap < 5000:
            return "5천억 미만"
        elif cap < 10000:
            return "5천억~1조"
        elif cap < 30000:
            return "1조~3조"
        elif cap < 100000:
            return "3조~10조"
        else:
            return "10조 이상"

    def get_trade_volume_group(self):
        """거래대금 구간 반환"""
        vol = self.trade_volume
        if vol < 1000:
            return "1천억 미만"
        elif vol < 3000:
            return "1천억~3천억"
        elif vol < 5000:
            return "3천억~5천억"
        else:
            return "5천억 이상"

def parse_trade_line(line, date):
    """테이블 행에서 거래 정보 추출"""
    parts = [p.strip() for p in line.split('|')]
    if len(parts) < 15:
        return None

    try:
        stock_name = parts[2]
        trade_type = parts[3]
        start_time = parts[4]
        end_time = parts[5]
        duration = parts[6]
        split_buy = int(parts[7].replace('회', ''))
        split_sell = int(parts[8].replace('회', ''))

        # 시총과 거래대금
        market_cap_str = parts[9].replace(',', '')
        trade_volume_str = parts[10].replace(',', '')

        if market_cap_str == 'nan':
            market_cap = 0
        else:
            market_cap = int(market_cap_str)

        if trade_volume_str == 'nan':
            trade_volume = 0
        else:
            trade_volume = int(trade_volume_str)

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

        # 10만원 이상 수익만
        if profit < 100000:
            return None

        # 시작시간, 종료시간이 유효한지 확인
        if start_time == 'nan' or end_time == 'nan':
            return None

        return BigWinner(stock_name, trade_type, start_time, end_time, duration,
                        split_buy, split_sell, market_cap, trade_volume,
                        profit, profit_rate, date)
    except (ValueError, IndexError) as e:
        return None

def get_industry(stock_name):
    """종목명으로 업종 추정"""
    # 간단한 키워드 기반 업종 분류
    if any(k in stock_name for k in ['제약', '바이오', '파마', '약품', '셀']):
        return "제약/바이오"
    elif any(k in stock_name for k in ['전자', '반도체', '디스플레이', 'IT', '테크']):
        return "IT/전자"
    elif any(k in stock_name for k in ['로봇', '로보', '자동화', '기계']):
        return "로봇/기계"
    elif any(k in stock_name for k in ['에너지', '전기', '태양광', '배터리']):
        return "에너지"
    elif any(k in stock_name for k in ['화학', '케미']):
        return "화학"
    elif any(k in stock_name for k in ['화장품', '뷰티']):
        return "화장품"
    elif any(k in stock_name for k in ['자동차', '오토', '모빌리티']):
        return "자동차"
    elif any(k in stock_name for k in ['건설', '건축', '건자재']):
        return "건설/건자재"
    elif any(k in stock_name for k in ['미디어', '엔터', '게임', '콘텐츠']):
        return "미디어/엔터"
    elif any(k in stock_name for k in ['금융', '증권', '은행', '보험']):
        return "금융"
    else:
        return "기타"

def analyze_big_winners():
    """10만원 이상 수익 거래 수집"""
    big_winners = []

    for filename in files_to_analyze:
        file_path = report_dir / filename
        if not file_path.exists():
            continue

        # 날짜 추출
        date = filename.replace('.md', '')

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # '거래별 손익 상세' 섹션 찾기
        match = re.search(r'## 💰 거래별 손익 상세\n\n.+?\n\|[-|]+\|\n((?:\|.+\n)+)', content)
        if not match:
            continue

        table_rows = match.group(1).strip().split('\n')
        for row in table_rows:
            winner = parse_trade_line(row, date)
            if winner:
                big_winners.append(winner)

    return big_winners

def generate_analysis_section(winners):
    """대박 거래 분석 섹션 생성"""

    total_winners = len(winners)
    total_profit = sum(w.profit for w in winners)
    avg_profit = total_profit / total_winners if total_winners > 0 else 0

    section = f"""
---

## 🎯 대박 거래 패턴 분석 (10만원 이상 수익)

**분석 대상**: {total_winners}건의 큰 수익 거래
**총 수익**: {total_profit:,}원
**평균 수익**: {avg_profit:,.0f}원/거래

---

### 📋 대박 거래 목록

| 날짜 | 종목명 | 진입시간 | 보유시간 | 분할매수 | 분할매도 | 시총 | 거래대금 | 손익금액 | 수익률 |
|------|--------|----------|----------|----------|----------|------|----------|----------|--------|
"""

    # 수익 순으로 정렬
    sorted_winners = sorted(winners, key=lambda x: x.profit, reverse=True)

    for w in sorted_winners:
        cap_str = f"{w.market_cap:,}억" if w.market_cap > 0 else "N/A"
        vol_str = f"{w.trade_volume:,}억" if w.trade_volume > 0 else "N/A"
        section += f"| {w.date} | {w.stock_name} | {w.start_time} | {w.duration} | {w.split_buy}회 | {w.split_sell}회 | {cap_str} | {vol_str} | {w.profit:,}원 | {w.profit_rate:+.2f}% |\n"

    section += "\n---\n\n### 🕐 시간 상관성 분석\n\n"

    # 시간대별 분석
    hour_stats = defaultdict(lambda: {'count': 0, 'total_profit': 0, 'profits': []})

    for w in winners:
        hour = w.get_start_hour()
        hour_stats[hour]['count'] += 1
        hour_stats[hour]['total_profit'] += w.profit
        hour_stats[hour]['profits'].append(w.profit)

    section += "#### 진입 시간대별 대박 거래\n\n"
    section += "| 시간대 | 거래 건수 | 총 수익 | 평균 수익 | 비율 |\n"
    section += "|--------|----------|---------|-----------|------|\n"

    for hour in sorted(hour_stats.keys()):
        stats = hour_stats[hour]
        ratio = (stats['count'] / total_winners * 100) if total_winners > 0 else 0
        avg = stats['total_profit'] / stats['count']
        section += f"| {hour}시 | {stats['count']}건 | {stats['total_profit']:,}원 | {avg:,.0f}원 | {ratio:.1f}% |\n"

    # 가장 좋은 시간대
    best_hour = max(hour_stats.items(), key=lambda x: x[1]['total_profit'])
    section += f"\n**💡 인사이트**: {best_hour[0]}시 진입이 가장 많은 대박 거래 발생 ({best_hour[1]['count']}건, {best_hour[1]['total_profit']:,}원)\n"

    # 보유 시간 분석
    section += "\n#### 보유 시간별 대박 거래\n\n"

    duration_groups = defaultdict(lambda: {'count': 0, 'total_profit': 0})

    for w in winners:
        minutes = w.get_duration_minutes()
        # 30분 단위로 그룹화
        group = (minutes // 30) * 30
        duration_groups[group]['count'] += 1
        duration_groups[group]['total_profit'] += w.profit

    section += "| 보유 시간 | 거래 건수 | 총 수익 | 평균 수익 | 비율 |\n"
    section += "|----------|----------|---------|-----------|------|\n"

    for duration in sorted(duration_groups.keys()):
        stats = duration_groups[duration]
        ratio = (stats['count'] / total_winners * 100) if total_winners > 0 else 0
        avg = stats['total_profit'] / stats['count']

        hours = duration // 60
        minutes = duration % 60
        if hours > 0:
            duration_str = f"{hours}h {minutes}m"
        else:
            duration_str = f"{minutes}m"

        section += f"| {duration_str} | {stats['count']}건 | {stats['total_profit']:,}원 | {avg:,.0f}원 | {ratio:.1f}% |\n"

    # 가장 좋은 보유시간
    best_duration = max(duration_groups.items(), key=lambda x: x[1]['total_profit'])
    best_dur_hours = best_duration[0] // 60
    best_dur_minutes = best_duration[0] % 60
    section += f"\n**💡 인사이트**: {best_dur_hours}h {best_dur_minutes}m 보유가 가장 많은 대박 수익 ({best_duration[1]['count']}건, {best_duration[1]['total_profit']:,}원)\n"

    section += "\n---\n\n### 💰 시총/거래대금 상관성 분석\n\n"

    # 시총 구간별 분석
    cap_stats = defaultdict(lambda: {'count': 0, 'total_profit': 0})

    for w in winners:
        if w.market_cap > 0:
            group = w.get_market_cap_group()
            cap_stats[group]['count'] += 1
            cap_stats[group]['total_profit'] += w.profit

    section += "#### 시가총액 구간별 대박 거래\n\n"
    section += "| 시총 구간 | 거래 건수 | 총 수익 | 평균 수익 | 비율 |\n"
    section += "|----------|----------|---------|-----------|------|\n"

    # 구간 순서
    cap_order = ["5천억 미만", "5천억~1조", "1조~3조", "3조~10조", "10조 이상"]

    for group in cap_order:
        if group in cap_stats:
            stats = cap_stats[group]
            ratio = (stats['count'] / total_winners * 100) if total_winners > 0 else 0
            avg = stats['total_profit'] / stats['count']
            section += f"| {group} | {stats['count']}건 | {stats['total_profit']:,}원 | {avg:,.0f}원 | {ratio:.1f}% |\n"

    # 가장 좋은 시총 구간
    if cap_stats:
        best_cap = max(cap_stats.items(), key=lambda x: x[1]['total_profit'])
        section += f"\n**💡 인사이트**: {best_cap[0]} 구간이 가장 많은 대박 거래 ({best_cap[1]['count']}건, {best_cap[1]['total_profit']:,}원)\n"

    # 거래대금 구간별 분석
    vol_stats = defaultdict(lambda: {'count': 0, 'total_profit': 0})

    for w in winners:
        if w.trade_volume > 0:
            group = w.get_trade_volume_group()
            vol_stats[group]['count'] += 1
            vol_stats[group]['total_profit'] += w.profit

    section += "\n#### 거래대금 구간별 대박 거래\n\n"
    section += "| 거래대금 구간 | 거래 건수 | 총 수익 | 평균 수익 | 비율 |\n"
    section += "|-------------|----------|---------|-----------|------|\n"

    # 구간 순서
    vol_order = ["1천억 미만", "1천억~3천억", "3천억~5천억", "5천억 이상"]

    for group in vol_order:
        if group in vol_stats:
            stats = vol_stats[group]
            ratio = (stats['count'] / total_winners * 100) if total_winners > 0 else 0
            avg = stats['total_profit'] / stats['count']
            section += f"| {group} | {stats['count']}건 | {stats['total_profit']:,}원 | {avg:,.0f}원 | {ratio:.1f}% |\n"

    # 가장 좋은 거래대금 구간
    if vol_stats:
        best_vol = max(vol_stats.items(), key=lambda x: x[1]['total_profit'])
        section += f"\n**💡 인사이트**: {best_vol[0]} 거래대금 구간이 가장 많은 대박 수익 ({best_vol[1]['count']}건, {best_vol[1]['total_profit']:,}원)\n"

    section += "\n---\n\n### 🏭 업종 상관성 분석\n\n"

    # 업종별 분석
    industry_stats = defaultdict(lambda: {'count': 0, 'total_profit': 0, 'stocks': set()})

    for w in winners:
        industry = get_industry(w.stock_name)
        industry_stats[industry]['count'] += 1
        industry_stats[industry]['total_profit'] += w.profit
        industry_stats[industry]['stocks'].add(w.stock_name)

    section += "#### 업종별 대박 거래\n\n"
    section += "| 업종 | 거래 건수 | 종목 수 | 총 수익 | 평균 수익 | 비율 |\n"
    section += "|------|----------|---------|---------|-----------|------|\n"

    # 수익 순으로 정렬
    sorted_industries = sorted(industry_stats.items(), key=lambda x: x[1]['total_profit'], reverse=True)

    for industry, stats in sorted_industries:
        ratio = (stats['count'] / total_winners * 100) if total_winners > 0 else 0
        avg = stats['total_profit'] / stats['count']
        stock_count = len(stats['stocks'])
        section += f"| {industry} | {stats['count']}건 | {stock_count}개 | {stats['total_profit']:,}원 | {avg:,.0f}원 | {ratio:.1f}% |\n"

    # 대박 종목 리스트
    section += "\n#### 대박 종목 상세\n\n"

    for industry, stats in sorted_industries:
        if stats['count'] > 0:
            stocks_list = ', '.join(sorted(stats['stocks']))
            section += f"**{industry}**: {stocks_list}\n\n"

    # 가장 좋은 업종
    if sorted_industries:
        best_industry = sorted_industries[0]
        section += f"**💡 인사이트**: {best_industry[0]} 업종이 가장 많은 대박 거래 발생 ({best_industry[1]['count']}건, {best_industry[1]['total_profit']:,}원)\n"

    section += "\n---\n\n### 🎯 대박 거래 공통 패턴\n\n"

    # 공통 패턴 추출
    section += "#### 📌 핵심 성공 요인\n\n"

    # 1. 시간 패턴
    primary_hours = [h for h, s in hour_stats.items() if s['count'] >= max(1, total_winners * 0.2)]
    if primary_hours:
        hours_str = ', '.join([f"{h}시" for h in sorted(primary_hours)])
        section += f"1. **최적 진입 시간**: {hours_str}\n"

    # 2. 시총 패턴
    if cap_stats:
        primary_caps = [c for c, s in cap_stats.items() if s['count'] >= max(1, total_winners * 0.2)]
        if primary_caps:
            section += f"2. **유리한 시총 구간**: {', '.join(primary_caps)}\n"

    # 3. 거래대금 패턴
    if vol_stats:
        primary_vols = [v for v, s in vol_stats.items() if s['count'] >= max(1, total_winners * 0.2)]
        if primary_vols:
            section += f"3. **유리한 거래대금 구간**: {', '.join(primary_vols)}\n"

    # 4. 업종 패턴
    top_industries = [ind for ind, _ in sorted_industries[:3]]
    if top_industries:
        section += f"4. **핵심 업종**: {', '.join(top_industries)}\n"

    # 5. 분할 매수/매도 패턴
    avg_split_buy = sum(w.split_buy for w in winners) / total_winners
    avg_split_sell = sum(w.split_sell for w in winners) / total_winners
    section += f"5. **평균 분할 매수**: {avg_split_buy:.1f}회\n"
    section += f"6. **평균 분할 매도**: {avg_split_sell:.1f}회\n"

    # 6. 보유 시간 패턴
    avg_duration = sum(w.get_duration_minutes() for w in winners) / total_winners
    avg_hours = int(avg_duration // 60)
    avg_minutes = int(avg_duration % 60)
    section += f"7. **평균 보유 시간**: {avg_hours}h {avg_minutes}m\n"

    section += "\n#### 🎓 대박 거래 재현 전략\n\n"
    section += "위 패턴을 따를 경우 10만원 이상 대박 거래 확률 증가:\n\n"

    section += "**체크리스트**:\n"

    if primary_hours:
        hours_str = ', '.join([f"{h}시" for h in sorted(primary_hours)])
        section += f"- [ ] 진입 시간이 {hours_str} 중 하나인가?\n"

    if primary_caps:
        section += f"- [ ] 시총이 {', '.join(primary_caps)} 구간인가?\n"

    if primary_vols:
        section += f"- [ ] 거래대금이 {', '.join(primary_vols)} 구간인가?\n"

    if top_industries:
        section += f"- [ ] 업종이 {', '.join(top_industries)} 중 하나인가?\n"

    section += f"- [ ] 분할 매수를 {avg_split_buy:.0f}회 정도로 계획했는가?\n"
    section += f"- [ ] 분할 매도를 {avg_split_sell:.0f}회 정도로 계획했는가?\n"
    section += f"- [ ] 목표 보유 시간을 {avg_hours}~{avg_hours+1}시간으로 설정했는가?\n"

    section += "\n**실행 규칙**:\n"
    section += f"- 위 체크리스트 5개 이상 만족 시 공격적 진입\n"
    section += f"- 3-4개 만족 시 보수적 진입 (소량)\n"
    section += f"- 2개 이하 만족 시 진입 회피\n"

    section += "\n---\n\n"

    return section

def main():
    print("대박 거래 패턴 분석 시작...\n")

    # 대박 거래 수집
    winners = analyze_big_winners()
    print(f"10만원 이상 수익 거래: {len(winners)}건 발견\n")

    if len(winners) == 0:
        print("10만원 이상 수익 거래가 없습니다.")
        return

    # 분석 섹션 생성
    print("대박 거래 패턴 분석 중...")
    analysis_section = generate_analysis_section(winners)

    # 기존 파일 읽기
    report_path = Path(__file__).parent.parent / "report" / "데이트레이딩_패턴_분석.md"
    with open(report_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 기존 대박 거래 분석 섹션 제거 (있다면)
    if "## 🎯 대박 거래 패턴 분석" in content:
        # 해당 섹션부터 끝까지 제거
        content = content.split("## 🎯 대박 거래 패턴 분석")[0].rstrip()

    # Generated with Claude Code 부분 제거
    if "*🤖 Generated with Claude Code*" in content:
        content = content.split("*🤖 Generated with Claude Code*")[0].rstrip()

    # 새 섹션 추가
    updated_content = content + analysis_section

    # 파일 저장
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(updated_content)

    print(f"\n분석 완료! 대박 거래 분석 섹션 추가됨")
    print(f"- 대박 거래 건수: {len(winners)}건")
    print(f"- 총 수익: {sum(w.profit for w in winners):,}원")
    print(f"- 평균 수익: {sum(w.profit for w in winners) / len(winners):,.0f}원")

if __name__ == "__main__":
    main()
