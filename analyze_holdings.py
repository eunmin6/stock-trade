import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from datetime import datetime
import matplotlib.font_manager as fm
import os
import sys

# 한글 폰트 설정
def setup_korean_font():
    """한글 폰트를 설정합니다."""
    # 우선순위로 시도할 폰트 목록
    preferred_fonts = ['Malgun Gothic', 'NanumGothic', 'Gulim', 'Batang']

    # matplotlib에서 사용 가능한 폰트 목록 가져오기
    available_fonts = [f.name for f in fm.fontManager.ttflist]

    # 우선순위에 따라 사용 가능한 폰트 찾기
    selected_font = None
    for font in preferred_fonts:
        if font in available_fonts:
            selected_font = font
            print(f"한글 폰트 설정: {font}")
            break

    if selected_font is None:
        # 한글 폰트를 찾지 못한 경우 시스템 기본 폰트 사용
        selected_font = 'DejaVu Sans'
        print("경고: 한글 폰트를 찾지 못했습니다. 일부 한글이 깨질 수 있습니다.")

    # 폰트 설정 적용
    plt.rcParams['font.family'] = selected_font
    plt.rcParams['axes.unicode_minus'] = False

    # 폰트 매니저 캐시 강제 업데이트
    fm._load_fontmanager(try_read_cache=False)

    return selected_font

# 폰트 설정 실행
import warnings
warnings.filterwarnings('ignore', category=UserWarning)
korean_font = setup_korean_font()

def get_data_path(date_str=None):
    """날짜별 데이터 경로를 반환합니다."""
    if date_str is None:
        date_str = datetime.now().strftime('%Y-%m-%d')
    return os.path.join('data', date_str, 'holdings.xlsx')

def get_report_path(date_str=None, file_type='png'):
    """날짜별 리포트 경로를 반환합니다."""
    if date_str is None:
        date_str = datetime.now().strftime('%Y-%m-%d')
    report_dir = os.path.join('report', date_str)
    os.makedirs(report_dir, exist_ok=True)

    if file_type == 'png':
        return os.path.join(report_dir, 'holdings.png')
    elif file_type == 'md':
        return os.path.join(report_dir, 'holdings.md')
    else:
        return os.path.join(report_dir, f'holdings.{file_type}')

def load_holdings(date_str=None):
    """주식 보유 정보를 로드합니다."""
    file_path = get_data_path(date_str)
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"데이터 파일을 찾을 수 없습니다: {file_path}")
    df = pd.read_excel(file_path)
    return df

def group_stocks_by_name(df):
    """같은 종목을 하나로 묶어서 집계합니다. (신용/현금 구분 무시)"""
    # 원본 데이터 복사
    df_copy = df.copy()

    # '*' 제거한 기본 종목명 컬럼 추가
    df_copy['기본종목명'] = df_copy['종목명'].str.replace('*', '', regex=False)

    # 종목별로 그룹화하여 합산
    grouped = df_copy.groupby('기본종목명').agg({
        '종목코드': 'first',  # 첫 번째 종목코드 사용
        '보유수량': 'sum',     # 수량 합산
        '매입금액': 'sum',     # 매입금액 합산
        '평가금액': 'sum',     # 평가금액 합산
        '평가손익': 'sum',     # 평가손익 합산
        '현재가': 'first',     # 현재가는 동일하므로 첫 번째 값 사용
        '수수료': 'sum',       # 수수료 합산
        '세금': 'sum',         # 세금 합산
        '신용금액': 'sum',     # 신용금액 합산
        '신용이자': 'sum',     # 신용이자 합산
    }).reset_index()

    # 종목명을 기본종목명으로 변경
    grouped.rename(columns={'기본종목명': '종목명'}, inplace=True)

    # 수익률 재계산 (합산된 금액 기준)
    grouped['수익률'] = grouped['평가손익'] / grouped['매입금액']

    # 비중 재계산
    total_value = grouped['평가금액'].sum()
    grouped['보유비중'] = grouped['평가금액'] / total_value

    # 신용거래 여부 판단
    grouped['신용구분'] = grouped['신용금액'].apply(lambda x: '신용거래' if x > 0 else '현금잔고')

    return grouped

def analyze_portfolio(df):
    """포트폴리오를 분석합니다."""
    print("=" * 80)
    print("주식 포트폴리오 분석 리포트")
    print("=" * 80)
    print(f"분석 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"보유 종목 수: {len(df)}개")
    print("=" * 80)

    # 전체 투자 현황
    total_investment = df['매입금액'].sum()
    total_value = df['평가금액'].sum()
    total_profit = df['평가손익'].sum()
    total_return = (total_profit / total_investment) * 100 if total_investment > 0 else 0

    print("\n[전체 포트폴리오 현황]")
    print(f"총 매입금액: {total_investment:,}원")
    print(f"총 평가금액: {total_value:,}원")
    print(f"총 평가손익: {total_profit:,}원")
    print(f"총 수익률: {total_return:.2f}%")

    # 수익/손실 종목 분류
    profit_stocks = df[df['평가손익'] > 0]
    loss_stocks = df[df['평가손익'] < 0]
    breakeven_stocks = df[df['평가손익'] == 0]

    print("\n[수익/손실 분류]")
    print(f"수익 종목: {len(profit_stocks)}개 (총 수익: {profit_stocks['평가손익'].sum():,}원)")
    print(f"손실 종목: {len(loss_stocks)}개 (총 손실: {loss_stocks['평가손익'].sum():,}원)")
    print(f"본전 종목: {len(breakeven_stocks)}개")

    # 상위/하위 종목
    print("\n[수익률 상위 5개 종목]")
    top_5 = df.nlargest(5, '수익률')[['종목명', '평가손익', '수익률', '매입금액', '평가금액']]
    for idx, row in top_5.iterrows():
        print(f"  {row['종목명']:15s} | 수익률: {row['수익률']*100:7.2f}% | 손익: {row['평가손익']:,}원")

    print("\n[수익률 하위 5개 종목]")
    bottom_5 = df.nsmallest(5, '수익률')[['종목명', '평가손익', '수익률', '매입금액', '평가금액']]
    for idx, row in bottom_5.iterrows():
        print(f"  {row['종목명']:15s} | 수익률: {row['수익률']*100:7.2f}% | 손익: {row['평가손익']:,}원")

    # 비중 분석
    print("\n[포트폴리오 비중 상위 10개 종목]")
    top_weight = df.nlargest(10, '평가금액')[['종목명', '평가금액', '보유비중']]
    for idx, row in top_weight.iterrows():
        weight_pct = (row['평가금액'] / total_value) * 100
        print(f"  {row['종목명']:15s} | 평가금액: {row['평가금액']:,}원 | 비중: {weight_pct:.2f}%")

    # 종목별 수익/손실 상세 테이블
    print("\n[종목별 수익/손실 상세]")
    print("=" * 100)
    print(f"{'순위':<4} {'종목명':<12} {'매입금액':>15} {'평가금액':>15} {'평가손익':>15} {'수익률':>10}")
    print("=" * 100)

    # 평가손익 기준으로 정렬 (손실이 큰 순서 = 오름차순)
    df_sorted = df.sort_values('평가손익', ascending=True).reset_index(drop=True)

    for idx, row in df_sorted.iterrows():
        rank = idx + 1
        profit_loss_str = f"{row['평가손익']:,}원"
        return_pct = f"{row['수익률']*100:+.2f}%"

        print(f"{rank:<4} {row['종목명']:<12} {row['매입금액']:>14,}원 {row['평가금액']:>14,}원 {profit_loss_str:>15} {return_pct:>10}")

    print("=" * 100)

    # 신용거래 현황
    credit_stocks = df[df['신용구분'] != '현금잔고']
    if len(credit_stocks) > 0:
        print("\n[신용거래 종목]")
        total_credit = credit_stocks['신용금액'].sum()
        total_interest = credit_stocks['신용이자'].sum()
        print(f"신용거래 종목 수: {len(credit_stocks)}개")
        print(f"총 신용금액: {total_credit:,}원")
        print(f"총 신용이자: {total_interest:,}원")
        for idx, row in credit_stocks.iterrows():
            print(f"  {row['종목명']:15s} | 구분: {row['신용구분']} | 금액: {row['신용금액']:,}원 | 이자: {row['신용이자']:,}원")

    print("\n" + "=" * 80)

    return {
        'total_investment': total_investment,
        'total_value': total_value,
        'total_profit': total_profit,
        'total_return': total_return,
        'profit_stocks': len(profit_stocks),
        'loss_stocks': len(loss_stocks)
    }

def visualize_portfolio(df, summary, date_str=None):
    """포트폴리오를 시각화합니다."""
    fig = plt.figure(figsize=(20, 16))

    # 1. 전체 수익/손실 현황 (파이 차트)
    ax1 = plt.subplot(3, 3, 1)
    profit_loss_data = [
        df[df['평가손익'] > 0]['평가손익'].sum(),
        abs(df[df['평가손익'] < 0]['평가손익'].sum())
    ]
    colors = ['#4CAF50', '#F44336']
    labels = [f"수익\n{profit_loss_data[0]:,.0f}원", f"손실\n{profit_loss_data[1]:,.0f}원"]
    ax1.pie(profit_loss_data, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
    ax1.set_title('수익/손실 비율', fontsize=14, fontweight='bold')

    # 2. 포트폴리오 구성 비중 (상위 10개)
    ax2 = plt.subplot(3, 3, 2)
    top_10 = df.nlargest(10, '평가금액')
    others_value = df[~df['종목명'].isin(top_10['종목명'])]['평가금액'].sum()

    pie_data = list(top_10['평가금액']) + ([others_value] if others_value > 0 else [])
    pie_labels = list(top_10['종목명']) + (['기타'] if others_value > 0 else [])

    colors = plt.cm.Set3(range(len(pie_data)))
    ax2.pie(pie_data, labels=pie_labels, autopct='%1.1f%%', startangle=90, colors=colors)
    ax2.set_title('종목별 비중 (상위 10개)', fontsize=14, fontweight='bold')

    # 3. 수익률 상위/하위 종목 (수평 바 차트)
    ax3 = plt.subplot(3, 3, 3)
    top_5 = df.nlargest(5, '수익률')
    bottom_5 = df.nsmallest(5, '수익률')
    combined = pd.concat([top_5, bottom_5])

    colors_bar = ['#4CAF50' if x > 0 else '#F44336' for x in combined['수익률']]
    y_pos = range(len(combined))
    ax3.barh(y_pos, combined['수익률'] * 100, color=colors_bar)
    ax3.set_yticks(y_pos)
    ax3.set_yticklabels(combined['종목명'])
    ax3.set_xlabel('수익률 (%)')
    ax3.set_title('수익률 상위/하위 5개 종목', fontsize=14, fontweight='bold')
    ax3.axvline(x=0, color='black', linestyle='-', linewidth=0.5)
    ax3.grid(axis='x', alpha=0.3)

    # 4. 평가손익 (금액 기준 바 차트)
    ax4 = plt.subplot(3, 3, 4)
    df_sorted = df.sort_values('평가손익', ascending=True)
    colors_bar = ['#4CAF50' if x > 0 else '#F44336' for x in df_sorted['평가손익']]
    ax4.barh(range(len(df_sorted)), df_sorted['평가손익'], color=colors_bar)
    ax4.set_yticks(range(len(df_sorted)))
    ax4.set_yticklabels(df_sorted['종목명'], fontsize=8)
    ax4.set_xlabel('평가손익 (원)')
    ax4.set_title('전체 종목 평가손익', fontsize=14, fontweight='bold')
    ax4.axvline(x=0, color='black', linestyle='-', linewidth=0.5)
    ax4.grid(axis='x', alpha=0.3)

    # 5. 매입금액 vs 평가금액 (산점도)
    ax5 = plt.subplot(3, 3, 5)
    colors_scatter = ['#4CAF50' if x > 0 else '#F44336' for x in df['평가손익']]
    sizes = np.abs(df['수익률']) * 1000
    ax5.scatter(df['매입금액'], df['평가금액'], c=colors_scatter, s=sizes, alpha=0.6)

    # 대각선 (본전선)
    max_val = max(df['매입금액'].max(), df['평가금액'].max())
    ax5.plot([0, max_val], [0, max_val], 'k--', alpha=0.3, label='본전선')

    ax5.set_xlabel('매입금액 (원)')
    ax5.set_ylabel('평가금액 (원)')
    ax5.set_title('매입금액 vs 평가금액', fontsize=14, fontweight='bold')
    ax5.legend()
    ax5.grid(alpha=0.3)

    # 종목명 표시 (상위 5개만)
    top_5_value = df.nlargest(5, '평가금액')
    for idx, row in top_5_value.iterrows():
        ax5.annotate(row['종목명'], (row['매입금액'], row['평가금액']),
                     fontsize=8, alpha=0.7)

    # 6. 포트폴리오 요약 통계
    ax6 = plt.subplot(3, 3, 6)
    ax6.axis('off')

    summary_text = f"""
    포트폴리오 요약
    {'='*40}

    총 보유 종목 수: {len(df)}개

    총 매입금액: {summary['total_investment']:,}원
    총 평가금액: {summary['total_value']:,}원
    총 평가손익: {summary['total_profit']:,}원
    총 수익률: {summary['total_return']:.2f}%

    수익 종목: {summary['profit_stocks']}개
    손실 종목: {summary['loss_stocks']}개

    최고 수익률: {df['수익률'].max()*100:.2f}%
    ({df.loc[df['수익률'].idxmax(), '종목명']})

    최저 수익률: {df['수익률'].min()*100:.2f}%
    ({df.loc[df['수익률'].idxmin(), '종목명']})
    """

    ax6.text(0.1, 0.5, summary_text, fontsize=12, verticalalignment='center',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))

    # 7. 종목별 수익/손실 상세 테이블 (하단에 큰 영역으로 배치)
    ax7 = plt.subplot(3, 1, 3)
    ax7.axis('off')

    # 평가손익 기준으로 정렬 (손실이 큰 순서)
    df_table = df.sort_values('평가손익', ascending=True).reset_index(drop=True)

    # 테이블 데이터 준비
    table_data = []
    table_data.append(['순위', '종목명', '매입금액', '평가금액', '평가손익', '수익률'])

    for idx, row in df_table.iterrows():
        rank = idx + 1
        stock_name = row['종목명']
        buy_amount = f"{row['매입금액']:,.0f}원"
        current_amount = f"{row['평가금액']:,.0f}원"
        profit_loss = f"{row['평가손익']:,.0f}원"
        return_rate = f"{row['수익률']*100:+.2f}%"

        table_data.append([rank, stock_name, buy_amount, current_amount, profit_loss, return_rate])

    # 테이블 생성
    table = ax7.table(cellText=table_data, cellLoc='center', loc='center',
                      colWidths=[0.08, 0.15, 0.20, 0.20, 0.20, 0.12])

    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1, 2.5)

    # 헤더 스타일 지정
    for i in range(6):
        cell = table[(0, i)]
        cell.set_facecolor('#4A90E2')
        cell.set_text_props(weight='bold', color='white')

    # 데이터 행 스타일 지정
    for i in range(1, len(table_data)):
        # 손익에 따라 색상 적용
        profit_loss_value = df_table.iloc[i-1]['평가손익']
        row_color = '#FFE5E5' if profit_loss_value < 0 else '#E5F5E5'

        for j in range(6):
            cell = table[(i, j)]
            cell.set_facecolor(row_color)

    ax7.set_title('종목별 수익/손실 상세', fontsize=16, fontweight='bold', pad=20)

    plt.tight_layout()

    # 그래프 저장 (날짜별 리포트 폴더에 저장)
    output_file = get_report_path(date_str)
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"\n시각화 결과가 '{output_file}' 파일로 저장되었습니다.")

    # plt.show()  # GUI 창을 열지 않도록 주석 처리

def generate_markdown_report(df, summary, date_str=None):
    """마크다운 리포트를 생성합니다."""
    if date_str is None:
        date_str = datetime.now().strftime('%Y-%m-%d')

    md_content = f"""# 주식 포트폴리오 분석 리포트

**분석 일시**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**분석 대상 날짜**: {date_str}

---

## 📊 전체 포트폴리오 현황

| 항목 | 금액 |
|------|------|
| 총 보유 종목 수 | {len(df)}개 |
| 총 매입금액 | {summary['total_investment']:,}원 |
| 총 평가금액 | {summary['total_value']:,}원 |
| 총 평가손익 | {summary['total_profit']:,}원 |
| 총 수익률 | {summary['total_return']:.2f}% |

---

## 📈 수익/손실 분류

| 구분 | 종목 수 | 금액 |
|------|---------|------|
| 수익 종목 | {summary['profit_stocks']}개 | {df[df['평가손익'] > 0]['평가손익'].sum():,}원 |
| 손실 종목 | {summary['loss_stocks']}개 | {df[df['평가손익'] < 0]['평가손익'].sum():,}원 |

---

## 💰 종목별 수익/손실 상세

| 순위 | 종목명 | 매입금액 | 평가금액 | 평가손익 | 수익률 |
|------|--------|----------|----------|----------|--------|
"""

    # 평가손익 기준으로 정렬 (손실이 큰 순서)
    df_sorted = df.sort_values('평가손익', ascending=True).reset_index(drop=True)

    for idx, row in df_sorted.iterrows():
        rank = idx + 1
        stock_name = row['종목명']
        buy_amount = f"{row['매입금액']:,}원"
        current_amount = f"{row['평가금액']:,}원"
        profit_loss = f"{row['평가손익']:,}원"
        return_rate = f"{row['수익률']*100:+.2f}%"

        md_content += f"| {rank} | {stock_name} | {buy_amount} | {current_amount} | {profit_loss} | {return_rate} |\n"

    # 수익률 상위/하위 종목
    md_content += "\n---\n\n## 📊 수익률 분석\n\n"
    md_content += "### 🔝 수익률 상위 5개 종목\n\n"
    md_content += "| 순위 | 종목명 | 수익률 | 평가손익 |\n"
    md_content += "|------|--------|--------|----------|\n"

    top_5 = df.nlargest(5, '수익률')
    for idx, (_, row) in enumerate(top_5.iterrows(), 1):
        md_content += f"| {idx} | {row['종목명']} | {row['수익률']*100:+.2f}% | {row['평가손익']:,}원 |\n"

    md_content += "\n### 📉 수익률 하위 5개 종목\n\n"
    md_content += "| 순위 | 종목명 | 수익률 | 평가손익 |\n"
    md_content += "|------|--------|--------|----------|\n"

    bottom_5 = df.nsmallest(5, '수익률')
    for idx, (_, row) in enumerate(bottom_5.iterrows(), 1):
        md_content += f"| {idx} | {row['종목명']} | {row['수익률']*100:+.2f}% | {row['평가손익']:,}원 |\n"

    # 포트폴리오 비중
    md_content += "\n---\n\n## 🎯 포트폴리오 비중\n\n"
    md_content += "| 순위 | 종목명 | 평가금액 | 비중 |\n"
    md_content += "|------|--------|----------|------|\n"

    df_weight = df.sort_values('평가금액', ascending=False).reset_index(drop=True)
    for idx, row in df_weight.iterrows():
        rank = idx + 1
        weight_pct = (row['평가금액'] / summary['total_value']) * 100
        md_content += f"| {rank} | {row['종목명']} | {row['평가금액']:,}원 | {weight_pct:.2f}% |\n"

    # 신용거래 현황
    credit_stocks = df[df['신용구분'] != '현금잔고']
    if len(credit_stocks) > 0:
        md_content += "\n---\n\n## 💳 신용거래 현황\n\n"
        total_credit = credit_stocks['신용금액'].sum()
        total_interest = credit_stocks['신용이자'].sum()

        md_content += f"- **신용거래 종목 수**: {len(credit_stocks)}개\n"
        md_content += f"- **총 신용금액**: {total_credit:,}원\n"
        md_content += f"- **총 신용이자**: {total_interest:,}원\n\n"

        md_content += "| 종목명 | 구분 | 신용금액 | 신용이자 |\n"
        md_content += "|--------|------|----------|----------|\n"

        for _, row in credit_stocks.iterrows():
            md_content += f"| {row['종목명']} | {row['신용구분']} | {row['신용금액']:,}원 | {row['신용이자']:,}원 |\n"

    # 시각화 이미지 링크
    md_content += "\n---\n\n## 📈 시각화 차트\n\n"
    md_content += f"![Portfolio Analysis](holdings.png)\n\n"

    md_content += "\n---\n\n"
    md_content += "*🤖 Generated with Claude Code*\n"

    # 마크다운 파일 저장
    output_file = get_report_path(date_str, 'md')
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(md_content)

    print(f"마크다운 리포트가 '{output_file}' 파일로 저장되었습니다.")

def main():
    """메인 함수"""
    try:
        # 날짜 인자 처리 (선택적)
        date_str = None
        if len(sys.argv) > 1:
            date_str = sys.argv[1]
            print(f"분석 날짜: {date_str}")
        else:
            date_str = datetime.now().strftime('%Y-%m-%d')
            print(f"분석 날짜: {date_str} (오늘)")

        # 데이터 로드
        data_path = get_data_path(date_str)
        print(f"데이터 파일: {data_path}\n")

        df_raw = load_holdings(date_str)

        print(f"원본 데이터: {len(df_raw)}개 항목 (신용/현금 구분 포함)")

        # 같은 종목 그룹화 (신용/현금 합산)
        df_grouped = group_stocks_by_name(df_raw)

        print(f"그룹화 후: {len(df_grouped)}개 종목")

        # 보유 수량 1개인 정찰병 종목 제외
        scout_stocks = df_grouped[df_grouped['보유수량'] == 1]
        df = df_grouped[df_grouped['보유수량'] > 1].copy()

        if len(scout_stocks) > 0:
            print(f"정찰병 종목 제외: {len(scout_stocks)}개 ({', '.join(scout_stocks['종목명'].tolist())})")

        print(f"최종 분석 대상: {len(df)}개 종목\n")

        # 포트폴리오 분석
        summary = analyze_portfolio(df)

        # 시각화
        visualize_portfolio(df, summary, date_str)

        # 마크다운 리포트 생성
        generate_markdown_report(df, summary, date_str)

    except FileNotFoundError as e:
        print(f"오류: {str(e)}")
        print("\n사용법:")
        print("  python analyze_holdings.py              # 오늘 날짜 데이터 분석")
        print("  python analyze_holdings.py 2025-11-03   # 특정 날짜 데이터 분석")
    except Exception as e:
        print(f"오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
