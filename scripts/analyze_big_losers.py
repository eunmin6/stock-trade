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

class BigLoser:
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

        # -10만원 이하 손실만 (profit < -100000)
        if profit >= -100000:
            return None

        # 시작시간, 종료시간이 유효한지 확인
        if start_time == 'nan' or end_time == 'nan':
            return None

        return BigLoser(stock_name, trade_type, start_time, end_time, duration,
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

def analyze_big_losers():
    """10만원 이상 손실 거래 수집"""
    big_losers = []

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
            loser = parse_trade_line(row, date)
            if loser:
                big_losers.append(loser)

    return big_losers

def generate_analysis_section(losers):
    """대손 거래 분석 섹션 생성"""

    total_losers = len(losers)
    total_loss = sum(l.profit for l in losers)
    avg_loss = total_loss / total_losers if total_losers > 0 else 0

    section = f"""
---

## ⚠️ 대손 거래 패턴 분석 (10만원 이상 손실)

**분석 대상**: {total_losers}건의 큰 손실 거래
**총 손실**: {total_loss:,}원
**평균 손실**: {avg_loss:,.0f}원/거래

---

### 📋 대손 거래 목록

| 날짜 | 종목명 | 진입시간 | 보유시간 | 분할매수 | 분할매도 | 시총 | 거래대금 | 손익금액 | 수익률 |
|------|--------|----------|----------|----------|----------|------|----------|----------|--------|
"""

    # 손실 순으로 정렬 (가장 큰 손실부터)
    sorted_losers = sorted(losers, key=lambda x: x.profit)

    for l in sorted_losers:
        cap_str = f"{l.market_cap:,}억" if l.market_cap > 0 else "N/A"
        vol_str = f"{l.trade_volume:,}억" if l.trade_volume > 0 else "N/A"
        section += f"| {l.date} | {l.stock_name} | {l.start_time} | {l.duration} | {l.split_buy}회 | {l.split_sell}회 | {cap_str} | {vol_str} | {l.profit:,}원 | {l.profit_rate:.2f}% |\n"

    section += "\n---\n\n### 🕐 시간 상관성 분석\n\n"

    # 시간대별 분석
    hour_stats = defaultdict(lambda: {'count': 0, 'total_loss': 0, 'losses': []})

    for l in losers:
        hour = l.get_start_hour()
        hour_stats[hour]['count'] += 1
        hour_stats[hour]['total_loss'] += l.profit
        hour_stats[hour]['losses'].append(l.profit)

    section += "#### 진입 시간대별 대손 거래\n\n"
    section += "| 시간대 | 거래 건수 | 총 손실 | 평균 손실 | 비율 |\n"
    section += "|--------|----------|---------|-----------|------|\n"

    for hour in sorted(hour_stats.keys()):
        stats = hour_stats[hour]
        ratio = (stats['count'] / total_losers * 100) if total_losers > 0 else 0
        avg = stats['total_loss'] / stats['count']
        section += f"| {hour}시 | {stats['count']}건 | {stats['total_loss']:,}원 | {avg:,.0f}원 | {ratio:.1f}% |\n"

    # 가장 위험한 시간대
    worst_hour = min(hour_stats.items(), key=lambda x: x[1]['total_loss'])
    section += f"\n**⚠️ 경고**: {worst_hour[0]}시 진입이 가장 많은 대손 거래 발생 ({worst_hour[1]['count']}건, {worst_hour[1]['total_loss']:,}원)\n"

    # 보유 시간 분석
    section += "\n#### 보유 시간별 대손 거래\n\n"

    duration_groups = defaultdict(lambda: {'count': 0, 'total_loss': 0})

    for l in losers:
        minutes = l.get_duration_minutes()
        # 30분 단위로 그룹화
        group = (minutes // 30) * 30
        duration_groups[group]['count'] += 1
        duration_groups[group]['total_loss'] += l.profit

    section += "| 보유 시간 | 거래 건수 | 총 손실 | 평균 손실 | 비율 |\n"
    section += "|----------|----------|---------|-----------|------|\n"

    for duration in sorted(duration_groups.keys()):
        stats = duration_groups[duration]
        ratio = (stats['count'] / total_losers * 100) if total_losers > 0 else 0
        avg = stats['total_loss'] / stats['count']

        hours = duration // 60
        minutes = duration % 60
        if hours > 0:
            duration_str = f"{hours}h {minutes}m"
        else:
            duration_str = f"{minutes}m"

        section += f"| {duration_str} | {stats['count']}건 | {stats['total_loss']:,}원 | {avg:,.0f}원 | {ratio:.1f}% |\n"

    # 가장 위험한 보유시간
    worst_duration = min(duration_groups.items(), key=lambda x: x[1]['total_loss'])
    worst_dur_hours = worst_duration[0] // 60
    worst_dur_minutes = worst_duration[0] % 60
    section += f"\n**⚠️ 경고**: {worst_dur_hours}h {worst_dur_minutes}m 보유가 가장 많은 대손 발생 ({worst_duration[1]['count']}건, {worst_duration[1]['total_loss']:,}원)\n"

    section += "\n---\n\n### 💰 시총/거래대금 상관성 분석\n\n"

    # 시총 구간별 분석
    cap_stats = defaultdict(lambda: {'count': 0, 'total_loss': 0})

    for l in losers:
        if l.market_cap > 0:
            group = l.get_market_cap_group()
            cap_stats[group]['count'] += 1
            cap_stats[group]['total_loss'] += l.profit

    section += "#### 시가총액 구간별 대손 거래\n\n"
    section += "| 시총 구간 | 거래 건수 | 총 손실 | 평균 손실 | 비율 |\n"
    section += "|----------|----------|---------|-----------|------|\n"

    # 구간 순서
    cap_order = ["5천억 미만", "5천억~1조", "1조~3조", "3조~10조", "10조 이상"]

    for group in cap_order:
        if group in cap_stats:
            stats = cap_stats[group]
            ratio = (stats['count'] / total_losers * 100) if total_losers > 0 else 0
            avg = stats['total_loss'] / stats['count']
            section += f"| {group} | {stats['count']}건 | {stats['total_loss']:,}원 | {avg:,.0f}원 | {ratio:.1f}% |\n"

    # 가장 위험한 시총 구간
    if cap_stats:
        worst_cap = min(cap_stats.items(), key=lambda x: x[1]['total_loss'])
        section += f"\n**⚠️ 경고**: {worst_cap[0]} 구간이 가장 많은 대손 거래 ({worst_cap[1]['count']}건, {worst_cap[1]['total_loss']:,}원)\n"

    # 거래대금 구간별 분석
    vol_stats = defaultdict(lambda: {'count': 0, 'total_loss': 0})

    for l in losers:
        if l.trade_volume > 0:
            group = l.get_trade_volume_group()
            vol_stats[group]['count'] += 1
            vol_stats[group]['total_loss'] += l.profit

    section += "\n#### 거래대금 구간별 대손 거래\n\n"
    section += "| 거래대금 구간 | 거래 건수 | 총 손실 | 평균 손실 | 비율 |\n"
    section += "|-------------|----------|---------|-----------|------|\n"

    # 구간 순서
    vol_order = ["1천억 미만", "1천억~3천억", "3천억~5천억", "5천억 이상"]

    for group in vol_order:
        if group in vol_stats:
            stats = vol_stats[group]
            ratio = (stats['count'] / total_losers * 100) if total_losers > 0 else 0
            avg = stats['total_loss'] / stats['count']
            section += f"| {group} | {stats['count']}건 | {stats['total_loss']:,}원 | {avg:,.0f}원 | {ratio:.1f}% |\n"

    # 가장 위험한 거래대금 구간
    if vol_stats:
        worst_vol = min(vol_stats.items(), key=lambda x: x[1]['total_loss'])
        section += f"\n**⚠️ 경고**: {worst_vol[0]} 거래대금 구간이 가장 많은 대손 발생 ({worst_vol[1]['count']}건, {worst_vol[1]['total_loss']:,}원)\n"

    section += "\n---\n\n### 🏭 업종 상관성 분석\n\n"

    # 업종별 분석
    industry_stats = defaultdict(lambda: {'count': 0, 'total_loss': 0, 'stocks': set()})

    for l in losers:
        industry = get_industry(l.stock_name)
        industry_stats[industry]['count'] += 1
        industry_stats[industry]['total_loss'] += l.profit
        industry_stats[industry]['stocks'].add(l.stock_name)

    section += "#### 업종별 대손 거래\n\n"
    section += "| 업종 | 거래 건수 | 종목 수 | 총 손실 | 평균 손실 | 비율 |\n"
    section += "|------|----------|---------|---------|-----------|------|\n"

    # 손실 순으로 정렬 (가장 큰 손실부터)
    sorted_industries = sorted(industry_stats.items(), key=lambda x: x[1]['total_loss'])

    for industry, stats in sorted_industries:
        ratio = (stats['count'] / total_losers * 100) if total_losers > 0 else 0
        avg = stats['total_loss'] / stats['count']
        stock_count = len(stats['stocks'])
        section += f"| {industry} | {stats['count']}건 | {stock_count}개 | {stats['total_loss']:,}원 | {avg:,.0f}원 | {ratio:.1f}% |\n"

    # 대손 종목 리스트
    section += "\n#### 대손 종목 상세\n\n"

    for industry, stats in sorted_industries:
        if stats['count'] > 0:
            stocks_list = ', '.join(sorted(stats['stocks']))
            section += f"**{industry}**: {stocks_list}\n\n"

    # 가장 위험한 업종
    if sorted_industries:
        worst_industry = sorted_industries[0]
        section += f"**⚠️ 경고**: {worst_industry[0]} 업종이 가장 많은 대손 거래 발생 ({worst_industry[1]['count']}건, {worst_industry[1]['total_loss']:,}원)\n"

    section += "\n---\n\n### 🎯 대손 거래 공통 패턴\n\n"

    # 공통 패턴 추출
    section += "#### 📌 핵심 실패 요인\n\n"

    # 1. 시간 패턴
    danger_hours = [h for h, s in hour_stats.items() if s['count'] >= max(1, total_losers * 0.2)]
    if danger_hours:
        hours_str = ', '.join([f"{h}시" for h in sorted(danger_hours)])
        section += f"1. **위험 진입 시간**: {hours_str}\n"

    # 2. 시총 패턴
    if cap_stats:
        danger_caps = [c for c, s in cap_stats.items() if s['count'] >= max(1, total_losers * 0.2)]
        if danger_caps:
            section += f"2. **위험한 시총 구간**: {', '.join(danger_caps)}\n"

    # 3. 거래대금 패턴
    if vol_stats:
        danger_vols = [v for v, s in vol_stats.items() if s['count'] >= max(1, total_losers * 0.2)]
        if danger_vols:
            section += f"3. **위험한 거래대금 구간**: {', '.join(danger_vols)}\n"

    # 4. 업종 패턴
    top_danger_industries = [ind for ind, _ in sorted_industries[:3]]
    if top_danger_industries:
        section += f"4. **위험 업종**: {', '.join(top_danger_industries)}\n"

    # 5. 분할 매수/매도 패턴
    avg_split_buy = sum(l.split_buy for l in losers) / total_losers
    avg_split_sell = sum(l.split_sell for l in losers) / total_losers
    section += f"5. **평균 분할 매수**: {avg_split_buy:.1f}회\n"
    section += f"6. **평균 분할 매도**: {avg_split_sell:.1f}회\n"

    # 6. 보유 시간 패턴
    avg_duration = sum(l.get_duration_minutes() for l in losers) / total_losers
    avg_hours = int(avg_duration // 60)
    avg_minutes = int(avg_duration % 60)
    section += f"7. **평균 보유 시간**: {avg_hours}h {avg_minutes}m\n"

    section += "\n#### 🛑 대손 거래 회피 전략\n\n"
    section += "다음 패턴이 나타나면 거래를 회피하거나 극도로 주의:\n\n"

    section += "**위험 신호 체크리스트**:\n"

    if danger_hours:
        hours_str = ', '.join([f"{h}시" for h in sorted(danger_hours)])
        section += f"- [ ] 진입 시간이 {hours_str} 중 하나가 아닌가? ⚠️\n"

    if danger_caps:
        section += f"- [ ] 시총이 {', '.join(danger_caps)} 구간이 아닌가? ⚠️\n"

    if danger_vols:
        section += f"- [ ] 거래대금이 {', '.join(danger_vols)} 구간이 아닌가? ⚠️\n"

    if top_danger_industries:
        section += f"- [ ] 업종이 {', '.join(top_danger_industries)} 중 하나가 아닌가? ⚠️\n"

    section += f"- [ ] 과도한 분할 매수 ({avg_split_buy:.0f}회 이상)를 계획하지 않았는가? ⚠️\n"
    section += f"- [ ] 보유 시간이 {avg_hours}시간대가 되지 않도록 계획했는가? ⚠️\n"

    section += "\n**실행 규칙**:\n"
    section += f"- 위 위험 신호 3개 이상 감지 시 **거래 중단**\n"
    section += f"- 2개 감지 시 **손절 라인 -1%로 축소** (더 빠른 손절)\n"
    section += f"- 1개 이하 시 일반 전략 수행 (손절 -2%)\n"

    # 대박 거래와 대손 거래 비교
    section += "\n---\n\n### 📊 대박 vs 대손 비교 분석\n\n"
    section += "#### 핵심 차이점\n\n"
    section += "| 구분 | 대박 거래 (10만원+) | 대손 거래 (10만원-) | 차이점 |\n"
    section += "|------|---------------------|---------------------|--------|\n"

    # 이전 분석에서 대박 거래 데이터를 가져오기 위해 임시로 하드코딩
    # (실제로는 대박 거래 분석 결과를 파일이나 변수로 공유해야 함)
    section += f"| **평균 손익** | +236,350원 | {avg_loss:,.0f}원 | {236350 - avg_loss:,.0f}원 |\n"
    section += f"| **진입 시간** | 9-11시 (100%) | {', '.join([f'{h}시' for h in sorted(danger_hours)])} | 초반 vs 다양 |\n"
    section += f"| **보유 시간** | 2h 43m | {avg_hours}h {avg_minutes}m | "

    if avg_duration < 163:  # 2h 43m = 163분
        section += "대손이 더 짧음 |\n"
    else:
        section += "대손이 더 김 |\n"

    section += f"| **분할 매수** | 17.2회 | {avg_split_buy:.1f}회 | "
    if avg_split_buy > 17.2:
        section += "대손이 더 많음 |\n"
    else:
        section += "대박이 더 많음 |\n"

    section += f"| **시총 구간** | 1조~3조 (50%) | {worst_cap[0]} | "
    if "5천억 미만" in worst_cap[0]:
        section += "대손은 소형주 |\n"
    else:
        section += "다름 |\n"

    section += f"| **거래대금** | 1천억~3천억 (75%) | {worst_vol[0]} | "
    if worst_vol[0] == "1천억 미만":
        section += "대손은 유동성 부족 |\n"
    elif worst_vol[0] == "3천억~5천억":
        section += "대손은 중간 변동성 |\n"
    else:
        section += "다름 |\n"

    section += "\n#### 💡 핵심 인사이트\n\n"

    # 시간 비교
    if danger_hours and sorted(danger_hours)[0] >= 10:
        section += "1. **대박은 아침(9-11시), 대손은 늦은 시간(10시 이후)에 집중**\n"

    # 시총 비교
    if worst_cap[0] == "5천억 미만":
        section += "2. **대박은 중형주(1-3조), 대손은 초소형주(5천억 미만)에 집중**\n"

    # 거래대금 비교
    if worst_vol[0] in ["1천억 미만", "3천억~5천억"]:
        section += "3. **대박은 적정 유동성(1-3천억), 대손은 유동성 부족 또는 과다 변동성**\n"

    section += "4. **적절한 분할 매매가 중요 - 과도한 분할은 손실 확대 가능성**\n"

    section += "\n#### 🎓 종합 전략 제안\n\n"
    section += "**DO (대박 패턴 따르기)**:\n"
    section += "- ✅ 9-11시 초반 진입\n"
    section += "- ✅ 시총 1-3조 종목 선택\n"
    section += "- ✅ 거래대금 1-3천억 확인\n"
    section += "- ✅ 보유 시간 1.5h 또는 3.5h+\n"
    section += "- ✅ 분할 매매 12-17회 적정 수준\n\n"

    section += "**DON'T (대손 패턴 회피하기)**:\n"

    if danger_hours:
        hours_str = ', '.join([f"{h}시" for h in sorted(danger_hours)])
        section += f"- ❌ {hours_str} 진입 회피\n"

    if worst_cap[0]:
        section += f"- ❌ {worst_cap[0]} 시총 종목 회피\n"

    if worst_vol[0]:
        section += f"- ❌ {worst_vol[0]} 거래대금 종목 회피\n"

    if top_danger_industries:
        section += f"- ❌ {', '.join(top_danger_industries[:2])} 업종 신중\n"

    section += f"- ❌ {avg_hours}h {avg_minutes}m 보유 시간대 회피\n"
    section += f"- ❌ 과도한 분할 매매 ({avg_split_buy:.0f}회 이상) 금지\n"

    section += "\n---\n\n"

    return section

def main():
    print("대손 거래 패턴 분석 시작...\n")

    # 대손 거래 수집
    losers = analyze_big_losers()
    print(f"10만원 이상 손실 거래: {len(losers)}건 발견\n")

    if len(losers) == 0:
        print("10만원 이상 손실 거래가 없습니다.")
        return

    # 분석 섹션 생성
    print("대손 거래 패턴 분석 중...")
    analysis_section = generate_analysis_section(losers)

    # 기존 파일 읽기
    report_path = Path(__file__).parent.parent / "report" / "데이트레이딩_패턴_분석.md"
    with open(report_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 기존 대손 거래 분석 섹션 제거 (있다면)
    if "## ⚠️ 대손 거래 패턴 분석" in content:
        # 해당 섹션부터 끝까지 제거
        content = content.split("## ⚠️ 대손 거래 패턴 분석")[0].rstrip()

    # 새 섹션 추가
    updated_content = content + analysis_section

    # 파일 저장
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(updated_content)

    print(f"\n분석 완료! 대손 거래 분석 섹션 추가됨")
    print(f"- 대손 거래 건수: {len(losers)}건")
    print(f"- 총 손실: {sum(l.profit for l in losers):,}원")
    print(f"- 평균 손실: {sum(l.profit for l in losers) / len(losers):,.0f}원")

if __name__ == "__main__":
    main()
