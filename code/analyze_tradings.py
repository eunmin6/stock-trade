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
    preferred_fonts = ['Malgun Gothic', 'NanumGothic', 'Gulim', 'Batang']
    available_fonts = [f.name for f in fm.fontManager.ttflist]

    selected_font = None
    for font in preferred_fonts:
        if font in available_fonts:
            selected_font = font
            print(f"한글 폰트 설정: {font}")
            break

    if selected_font is None:
        selected_font = 'DejaVu Sans'
        print("경고: 한글 폰트를 찾지 못했습니다. 일부 한글이 깨질 수 있습니다.")

    plt.rcParams['font.family'] = selected_font
    plt.rcParams['axes.unicode_minus'] = False
    fm._load_fontmanager(try_read_cache=False)

    return selected_font

import warnings
warnings.filterwarnings('ignore', category=UserWarning)
korean_font = setup_korean_font()

def get_data_path(date_str=None):
    """날짜별 데이터 경로를 반환합니다."""
    if date_str is None:
        date_str = datetime.now().strftime('%Y-%m-%d')
    return os.path.join('data', date_str, 'tradings.xlsx')

def get_report_path(date_str=None, file_type='png'):
    """날짜별 리포트 경로를 반환합니다."""
    if date_str is None:
        date_str = datetime.now().strftime('%Y-%m-%d')

    # 새 구조: report/tradings/ 또는 report/tradings/img/
    if file_type == 'png':
        report_dir = os.path.join('report', 'tradings', 'img')
        os.makedirs(report_dir, exist_ok=True)
        return os.path.join(report_dir, f'{date_str}.png')
    elif file_type == 'md':
        report_dir = os.path.join('report', 'tradings')
        os.makedirs(report_dir, exist_ok=True)
        return os.path.join(report_dir, f'{date_str}.md')
    else:
        report_dir = os.path.join('report', 'tradings')
        os.makedirs(report_dir, exist_ok=True)
        return os.path.join(report_dir, f'{date_str}.{file_type}')

def load_tradings(date_str=None):
    """매도 거래 정보를 로드합니다."""
    file_path = get_data_path(date_str)
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"데이터 파일을 찾을 수 없습니다: {file_path}")

    # 첫 2행이 헤더이므로 skiprows=2로 읽기
    df = pd.read_excel(file_path, header=None, skiprows=2)

    # 컬럼명 정리 (금일매수/금일매도 구조 반영)
    df.columns = ['종목코드', '종목명',
                  '금일매수_평균가', '금일매수_수량', '금일매수_매입금액',
                  '금일매도_평균가', '금일매도_수량', '금일매도_매도금액',
                  '수수료및세금', '손익금액', '수익률',
                  '대출일', '신용구분', '이전매입가']

    # 데이터 타입 변환
    numeric_columns = ['종목코드',
                      '금일매수_평균가', '금일매수_수량', '금일매수_매입금액',
                      '금일매도_평균가', '금일매도_수량', '금일매도_매도금액',
                      '수수료및세금', '손익금액', '수익률']

    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # NaN 제거
    df = df.dropna(subset=['종목명'])

    # 거래 타입 분류 추가
    df['거래타입'] = df.apply(classify_trade_type, axis=1)

    return df

def classify_trade_type(row):
    """거래 유형을 분류합니다."""
    buy_qty = row['금일매수_수량'] if pd.notna(row['금일매수_수량']) else 0
    sell_qty = row['금일매도_수량'] if pd.notna(row['금일매도_수량']) else 0

    if buy_qty == sell_qty and buy_qty > 0:
        return '데이트레이딩'  # 당일 매수 당일 매도
    elif buy_qty < sell_qty:
        return '스윙투자'  # 이전에 매수한 것을 오늘 매도
    elif buy_qty > sell_qty and sell_qty > 0:
        return '일부매도'
    elif buy_qty > 0 and sell_qty == 0:
        return '매수만'
    elif sell_qty > 0 and buy_qty == 0:
        return '매도만'
    else:
        return '기타'

def group_tradings_by_name(df):
    """같은 종목을 하나로 묶어서 집계합니다. (신용/현금 구분 무시)"""
    df_copy = df.copy()
    df_copy['기본종목명'] = df_copy['종목명'].str.replace('*', '', regex=False)

    grouped = df_copy.groupby('기본종목명').agg({
        '종목코드': 'first',
        '금일매수_수량': 'sum',
        '금일매수_매입금액': 'sum',
        '금일매도_수량': 'sum',
        '금일매도_매도금액': 'sum',
        '수수료및세금': 'sum',
        '손익금액': 'sum',
    }).reset_index()

    grouped.rename(columns={'기본종목명': '종목명'}, inplace=True)

    # 수익률 재계산
    grouped['수익률'] = grouped['손익금액'] / grouped['금일매수_매입금액']

    # 평균 매수가, 매도가 재계산
    grouped['금일매수_평균가'] = grouped['금일매수_매입금액'] / grouped['금일매수_수량']
    grouped['금일매도_평균가'] = grouped['금일매도_매도금액'] / grouped['금일매도_수량']

    # 신용거래 여부
    credit_stocks = df_copy[df_copy['신용구분'].notna()]['기본종목명'].unique()
    grouped['신용구분'] = grouped['종목명'].apply(lambda x: '신용거래' if x in credit_stocks else '현금')

    return grouped

def analyze_tradings(df):
    """매도 거래를 분석합니다."""
    print("=" * 80)
    print("매도 거래 분석 리포트")
    print("=" * 80)
    print(f"분석 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"총 거래 건수: {len(df)}건")
    print("=" * 80)

    # 거래 타입별 통계 (매수만 제외)
    print("\n[거래 타입별 수익 현황]")
    for trade_type in df['거래타입'].unique():
        if trade_type == '매수만':
            continue
        count = len(df[df['거래타입'] == trade_type])
        profit = df[df['거래타입'] == trade_type]['손익금액'].sum()
        print(f"{trade_type:20s}: {count:2d}건 | 손익: {profit:>12,.0f}원")

    # 전체 거래 현황
    total_buy_amount = df['금일매수_매입금액'].sum()
    total_sell_amount = df['금일매도_매도금액'].sum()
    total_profit = df['손익금액'].sum()
    total_return = (total_profit / total_buy_amount) * 100 if total_buy_amount > 0 else 0

    print("\n[전체 거래 현황]")
    print(f"총 매입금액: {total_buy_amount:,.0f}원")
    print(f"총 매도금액: {total_sell_amount:,.0f}원")
    print(f"총 손익금액: {total_profit:,.0f}원")
    print(f"평균 수익률: {total_return:.2f}%")

    # 수익/손실 거래 분류
    profit_trades = df[df['손익금액'] > 0]
    loss_trades = df[df['손익금액'] < 0]

    print("\n[수익/손실 분류]")
    print(f"수익 거래: {len(profit_trades)}건 (총 수익: {profit_trades['손익금액'].sum():,.0f}원)")
    print(f"손실 거래: {len(loss_trades)}건 (총 손실: {loss_trades['손익금액'].sum():,.0f}원)")

    # 수익률 상위/하위
    print("\n[수익률 상위 5개 거래]")
    top_5 = df.nlargest(5, '수익률')[['종목명', '손익금액', '수익률', '거래타입', '금일매수_매입금액', '금일매도_매도금액']]
    for idx, row in top_5.iterrows():
        print(f"  {row['종목명']:15s} | {row['거래타입']:18s} | 수익률: {row['수익률']*100:7.2f}% | 손익: {row['손익금액']:,.0f}원")

    print("\n[수익률 하위 5개 거래]")
    bottom_5 = df.nsmallest(5, '수익률')[['종목명', '손익금액', '수익률', '거래타입', '금일매수_매입금액', '금일매도_매도금액']]
    for idx, row in bottom_5.iterrows():
        print(f"  {row['종목명']:15s} | {row['거래타입']:18s} | 수익률: {row['수익률']*100:7.2f}% | 손익: {row['손익금액']:,.0f}원")

    # 거래별 상세 테이블
    print("\n[거래별 손익 상세]")
    print("=" * 130)
    print(f"{'순위':<4} {'종목명':<12} {'거래타입':<18} {'매입금액':>15} {'매도금액':>15} {'손익금액':>15} {'수익률':>10} {'수수료/세금':>12}")
    print("=" * 130)

    df_sorted = df.sort_values('손익금액', ascending=True).reset_index(drop=True)
    for idx, row in df_sorted.iterrows():
        rank = idx + 1
        profit_loss_str = f"{row['손익금액']:,.0f}원"
        return_pct = f"{row['수익률']*100:+.2f}%"
        fee_str = f"{row['수수료및세금']:,.0f}원"
        trade_type = row['거래타입']

        print(f"{rank:<4} {row['종목명']:<12} {trade_type:<18} {row['금일매수_매입금액']:>14,.0f}원 {row['금일매도_매도금액']:>14,.0f}원 {profit_loss_str:>15} {return_pct:>10} {fee_str:>12}")

    print("=" * 130)

    # 신용거래 현황
    credit_trades = df[df['신용구분'] == '신용거래']
    if len(credit_trades) > 0:
        print("\n[신용거래 내역]")
        print(f"신용거래 건수: {len(credit_trades)}건")
        for _, row in credit_trades.iterrows():
            print(f"  {row['종목명']:15s} | 손익: {row['손익금액']:,.0f}원 | 수익률: {row['수익률']*100:+.2f}%")

    print("\n" + "=" * 80)

    return {
        'total_buy_amount': total_buy_amount,
        'total_sell_amount': total_sell_amount,
        'total_profit': total_profit,
        'total_return': total_return,
        'profit_trades': len(profit_trades),
        'loss_trades': len(loss_trades)
    }

def visualize_tradings(df, summary, date_str=None):
    """매도 거래를 시각화합니다."""
    fig = plt.figure(figsize=(20, 16))

    # 1. 수익/손실 비율 (파이 차트)
    ax1 = plt.subplot(3, 3, 1)
    profit_loss_data = [
        df[df['손익금액'] > 0]['손익금액'].sum(),
        abs(df[df['손익금액'] < 0]['손익금액'].sum())
    ]
    colors = ['#4CAF50', '#F44336']
    labels = [f"수익\n{profit_loss_data[0]:,.0f}원", f"손실\n{profit_loss_data[1]:,.0f}원"]
    ax1.pie(profit_loss_data, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
    ax1.set_title('수익/손실 비율', fontsize=14, fontweight='bold')

    # 2. 종목별 손익 (파이 차트)
    ax2 = plt.subplot(3, 3, 2)
    df_abs_profit = df.copy()
    df_abs_profit['절대손익'] = df_abs_profit['손익금액'].abs()
    top_trades = df_abs_profit.nlargest(5, '절대손익')

    colors_pie = ['#4CAF50' if x > 0 else '#F44336' for x in top_trades['손익금액']]
    ax2.pie(top_trades['절대손익'], labels=top_trades['종목명'], colors=colors_pie,
            autopct='%1.1f%%', startangle=90)
    ax2.set_title('거래 비중 (상위 5개)', fontsize=14, fontweight='bold')

    # 3. 수익률 분포 (바 차트)
    ax3 = plt.subplot(3, 3, 3)
    df_sorted_return = df.sort_values('수익률', ascending=True)
    colors_bar = ['#4CAF50' if x > 0 else '#F44336' for x in df_sorted_return['수익률']]
    ax3.barh(range(len(df_sorted_return)), df_sorted_return['수익률'] * 100, color=colors_bar)
    ax3.set_yticks(range(len(df_sorted_return)))
    ax3.set_yticklabels(df_sorted_return['종목명'], fontsize=10)
    ax3.set_xlabel('수익률 (%)')
    ax3.set_title('종목별 수익률', fontsize=14, fontweight='bold')
    ax3.axvline(x=0, color='black', linestyle='-', linewidth=0.5)
    ax3.grid(axis='x', alpha=0.3)

    # 4. 손익금액 (바 차트)
    ax4 = plt.subplot(3, 3, 4)
    df_sorted_profit = df.sort_values('손익금액', ascending=True)
    colors_bar2 = ['#4CAF50' if x > 0 else '#F44336' for x in df_sorted_profit['손익금액']]
    ax4.barh(range(len(df_sorted_profit)), df_sorted_profit['손익금액'], color=colors_bar2)
    ax4.set_yticks(range(len(df_sorted_profit)))
    ax4.set_yticklabels(df_sorted_profit['종목명'], fontsize=10)
    ax4.set_xlabel('손익금액 (원)')
    ax4.set_title('종목별 손익금액', fontsize=14, fontweight='bold')
    ax4.axvline(x=0, color='black', linestyle='-', linewidth=0.5)
    ax4.grid(axis='x', alpha=0.3)

    # 5. 매입금액 vs 매도금액 (산점도)
    ax5 = plt.subplot(3, 3, 5)
    colors_scatter = ['#4CAF50' if x > 0 else '#F44336' for x in df['손익금액']]
    sizes = np.abs(df['수익률']) * 3000

    # NaN 값 제외
    df_plot = df.dropna(subset=['금일매수_매입금액', '금일매도_매도금액'])
    if len(df_plot) > 0:
        ax5.scatter(df_plot['금일매수_매입금액'], df_plot['금일매도_매도금액'],
                   c=['#4CAF50' if x > 0 else '#F44336' for x in df_plot['손익금액']],
                   s=[np.abs(x) * 3000 for x in df_plot['수익률']], alpha=0.6)

        max_val = max(df_plot['금일매수_매입금액'].max(), df_plot['금일매도_매도금액'].max())
        ax5.plot([0, max_val], [0, max_val], 'k--', alpha=0.3, label='손익분기선')

        for idx, row in df_plot.iterrows():
            ax5.annotate(row['종목명'], (row['금일매수_매입금액'], row['금일매도_매도금액']),
                        fontsize=8, alpha=0.7)

    ax5.set_xlabel('매입금액 (원)')
    ax5.set_ylabel('매도금액 (원)')
    ax5.set_title('매입금액 vs 매도금액', fontsize=14, fontweight='bold')
    ax5.legend()
    ax5.grid(alpha=0.3)

    # 6. 거래 요약 통계
    ax6 = plt.subplot(3, 3, 6)
    ax6.axis('off')

    summary_text = f"""
    거래 요약
    {'='*40}

    총 거래 건수: {len(df)}건

    총 매입금액: {summary['total_buy_amount']:,.0f}원
    총 매도금액: {summary['total_sell_amount']:,.0f}원
    총 손익금액: {summary['total_profit']:,.0f}원
    평균 수익률: {summary['total_return']:.2f}%

    수익 거래: {summary['profit_trades']}건
    손실 거래: {summary['loss_trades']}건

    최고 수익률: {df['수익률'].max()*100:.2f}%
    ({df.loc[df['수익률'].idxmax(), '종목명']})

    최저 수익률: {df['수익률'].min()*100:.2f}%
    ({df.loc[df['수익률'].idxmin(), '종목명']})
    """

    ax6.text(0.1, 0.5, summary_text, fontsize=12, verticalalignment='center',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))

    # 7. 거래별 손익 상세 테이블
    ax7 = plt.subplot(3, 1, 3)
    ax7.axis('off')

    df_table = df.sort_values('손익금액', ascending=True).reset_index(drop=True)

    table_data = []
    table_data.append(['순위', '종목명', '거래타입', '매입금액', '매도금액', '손익금액', '수익률'])

    for idx, row in df_table.iterrows():
        rank = idx + 1
        stock_name = row['종목명']
        trade_type = row['거래타입']
        buy_amount = f"{row['금일매수_매입금액']:,.0f}원" if pd.notna(row['금일매수_매입금액']) else "N/A"
        sell_amount = f"{row['금일매도_매도금액']:,.0f}원" if pd.notna(row['금일매도_매도금액']) else "N/A"
        profit = f"{row['손익금액']:,.0f}원" if pd.notna(row['손익금액']) else "N/A"
        return_rate = f"{row['수익률']*100:+.2f}%" if pd.notna(row['수익률']) else "N/A"

        table_data.append([rank, stock_name, trade_type, buy_amount, sell_amount, profit, return_rate])

    table = ax7.table(cellText=table_data, cellLoc='center', loc='center',
                      colWidths=[0.06, 0.12, 0.16, 0.16, 0.16, 0.16, 0.10])

    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 2.5)

    for i in range(7):
        cell = table[(0, i)]
        cell.set_facecolor('#4A90E2')
        cell.set_text_props(weight='bold', color='white')

    for i in range(1, len(table_data)):
        profit_value = df_table.iloc[i-1]['손익금액']
        row_color = '#FFE5E5' if pd.notna(profit_value) and profit_value < 0 else '#E5F5E5'

        for j in range(7):
            cell = table[(i, j)]
            cell.set_facecolor(row_color)

    ax7.set_title('거래별 손익 상세', fontsize=16, fontweight='bold', pad=20)

    plt.tight_layout()

    output_file = get_report_path(date_str, 'png')
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"\n시각화 결과가 '{output_file}' 파일로 저장되었습니다.")

def generate_markdown_report(df, summary, date_str=None):
    """마크다운 리포트를 생성합니다."""
    if date_str is None:
        date_str = datetime.now().strftime('%Y-%m-%d')

    # 거래 타입별 통계 (매수만 제외)
    trade_type_stats = ""
    for trade_type in df['거래타입'].unique():
        if trade_type == '매수만':
            continue
        count = len(df[df['거래타입'] == trade_type])
        profit = df[df['거래타입'] == trade_type]['손익금액'].sum()
        trade_type_stats += f"| {trade_type} | {count}건 | {profit:,.0f}원 |\n"

    md_content = f"""# 매도 거래 분석 리포트

**분석 일시**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**분석 대상 날짜**: {date_str}

---

## 📊 전체 거래 현황

| 항목 | 금액 |
|------|------|
| 총 거래 건수 | {len(df)}건 |
| 총 매입금액 | {summary['total_buy_amount']:,.0f}원 |
| 총 매도금액 | {summary['total_sell_amount']:,.0f}원 |
| 총 손익금액 | {summary['total_profit']:,.0f}원 |
| 평균 수익률 | {summary['total_return']:.2f}% |

---

## 🔄 거래 타입별 수익 현황

| 거래 타입 | 건수 | 손익금액 |
|-----------|------|----------|
{trade_type_stats}

---

## 📈 수익/손실 분류

| 구분 | 거래 건수 | 금액 |
|------|----------|------|
| 수익 거래 | {summary['profit_trades']}건 | {df[df['손익금액'] > 0]['손익금액'].sum():,.0f}원 |
| 손실 거래 | {summary['loss_trades']}건 | {df[df['손익금액'] < 0]['손익금액'].sum():,.0f}원 |

---

## 💰 거래별 손익 상세

| 순위 | 종목명 | 거래타입 | 매입금액 | 매도금액 | 손익금액 | 수익률 |
|------|--------|----------|----------|----------|----------|--------|
"""

    df_sorted = df.sort_values('손익금액', ascending=True).reset_index(drop=True)

    for idx, row in df_sorted.iterrows():
        rank = idx + 1
        stock_name = row['종목명']
        trade_type = row['거래타입']
        buy_amount = f"{row['금일매수_매입금액']:,.0f}원"
        sell_amount = f"{row['금일매도_매도금액']:,.0f}원"
        profit = f"{row['손익금액']:,.0f}원"
        return_rate = f"{row['수익률']*100:+.2f}%"

        md_content += f"| {rank} | {stock_name} | {trade_type} | {buy_amount} | {sell_amount} | {profit} | {return_rate} |\n"

    # 수익률 분석
    md_content += "\n---\n\n## 📊 수익률 분석\n\n"
    md_content += "### 🔝 수익률 상위 5개 거래\n\n"
    md_content += "| 순위 | 종목명 | 거래타입 | 수익률 | 손익금액 |\n"
    md_content += "|------|--------|----------|--------|----------|\n"

    top_5 = df.nlargest(min(5, len(df)), '수익률')
    for idx, (_, row) in enumerate(top_5.iterrows(), 1):
        md_content += f"| {idx} | {row['종목명']} | {row['거래타입']} | {row['수익률']*100:+.2f}% | {row['손익금액']:,.0f}원 |\n"

    md_content += "\n### 📉 수익률 하위 5개 거래\n\n"
    md_content += "| 순위 | 종목명 | 거래타입 | 수익률 | 손익금액 |\n"
    md_content += "|------|--------|----------|--------|----------|\n"

    bottom_5 = df.nsmallest(min(5, len(df)), '수익률')
    for idx, (_, row) in enumerate(bottom_5.iterrows(), 1):
        md_content += f"| {idx} | {row['종목명']} | {row['거래타입']} | {row['수익률']*100:+.2f}% | {row['손익금액']:,.0f}원 |\n"

    # 신용거래 내역
    credit_trades = df[df['신용구분'] == '신용거래']
    if len(credit_trades) > 0:
        md_content += "\n---\n\n## 💳 신용거래 내역\n\n"
        md_content += f"- **신용거래 건수**: {len(credit_trades)}건\n\n"

        md_content += "| 종목명 | 손익금액 | 수익률 |\n"
        md_content += "|--------|----------|--------|\n"

        for _, row in credit_trades.iterrows():
            md_content += f"| {row['종목명']} | {row['손익금액']:,.0f}원 | {row['수익률']*100:+.2f}% |\n"

    md_content += "\n---\n\n## 📈 시각화 차트\n\n"
    # 새 구조에 맞게 이미지 경로 수정
    md_content += f"![Trading Analysis](img/{date_str}.png)\n\n"

    md_content += "\n---\n\n"
    md_content += "*🤖 Generated with Claude Code*\n"

    output_file = get_report_path(date_str, 'md')
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(md_content)

    print(f"마크다운 리포트가 '{output_file}' 파일로 저장되었습니다.")

def main():
    """메인 함수"""
    try:
        date_str = None
        if len(sys.argv) > 1:
            date_str = sys.argv[1]
            print(f"분석 날짜: {date_str}")
        else:
            date_str = datetime.now().strftime('%Y-%m-%d')
            print(f"분석 날짜: {date_str} (오늘)")

        data_path = get_data_path(date_str)
        print(f"데이터 파일: {data_path}\n")

        df_raw = load_tradings(date_str)
        print(f"원본 데이터: {len(df_raw)}건의 거래 (신용/현금 구분 포함)")

        df = group_tradings_by_name(df_raw)
        print(f"그룹화 후: {len(df)}개 종목\n")

        # 분석과 리포트는 원본 데이터 사용 (거래타입 정보 포함)
        summary = analyze_tradings(df_raw)
        visualize_tradings(df_raw, summary, date_str)
        generate_markdown_report(df_raw, summary, date_str)

    except FileNotFoundError as e:
        print(f"오류: {str(e)}")
        print("\n사용법:")
        print("  python analyze_tradings.py              # 오늘 날짜 데이터 분석")
        print("  python analyze_tradings.py 2025-11-03   # 특정 날짜 데이터 분석")
    except Exception as e:
        print(f"오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
