import sys
import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from fetch_stock_prices import get_stock_code
from pykrx import stock
from scipy import stats

# UTF-8 출력 설정
if sys.platform == 'win32':
    os.system('chcp 65001 > nul')

def analyze_stock_trend(stock_name_or_code, period_days=365):
    """
    종목의 추세를 분석합니다.

    Args:
        stock_name_or_code: 종목명 또는 종목코드
        period_days: 분석 기간 (일)
    """

    # 종목코드 확인
    if len(stock_name_or_code) == 6 and stock_name_or_code.isdigit():
        stock_code = stock_name_or_code
        stock_name = stock_name_or_code
    else:
        stock_code, stock_name = get_stock_code(stock_name_or_code)
        if not stock_code:
            print(f"오류: '{stock_name_or_code}' 종목을 찾을 수 없습니다.")
            return None

    # 날짜 설정 (오늘부터 1년 전까지)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=period_days)

    print(f"\n{'='*60}")
    print(f"[분석] {stock_name} ({stock_code}) - {period_days}일 추세 분석")
    print(f"{'='*60}\n")

    # 데이터 조회
    print("데이터 조회 중...")
    start_str = start_date.strftime('%Y%m%d')
    end_str = end_date.strftime('%Y%m%d')

    try:
        df = stock.get_market_ohlcv_by_date(start_str, end_str, stock_code)

        if df is None or df.empty:
            print("오류: 주가 데이터를 가져올 수 없습니다.")
            return None

        # 데이터 정리
        df = df.sort_index()

        print(f"[O] {len(df)}일간의 데이터 수집 완료\n")

        # 기본 통계
        current_price = df['종가'].iloc[-1]
        min_price = df['저가'].min()
        max_price = df['고가'].max()
        avg_price = df['종가'].mean()

        min_date = df['저가'].idxmin()
        max_date = df['고가'].idxmax()

        # 상승률 계산
        gain_from_min = ((current_price - min_price) / min_price) * 100
        gain_from_avg = ((current_price - avg_price) / avg_price) * 100

        # 3개월 전 가격
        three_months_ago = end_date - timedelta(days=90)
        three_months_df = df[df.index >= three_months_ago.strftime('%Y-%m-%d')]
        if not three_months_df.empty:
            price_3m_ago = three_months_df['종가'].iloc[0]
            gain_from_3m = ((current_price - price_3m_ago) / price_3m_ago) * 100
        else:
            price_3m_ago = None
            gain_from_3m = None

        # 기간 정보
        print(f"[날짜] 분석 기간: {df.index[0]} ~ {df.index[-1]}")
        print(f"[분석] 데이터 일수: {len(df)}일\n")

        print(f"[가격] 가격 정보")
        print(f"{'─'*60}")
        print(f"  현재가:        {current_price:>10,.0f}원")
        print(f"  1년 최저가:    {min_price:>10,.0f}원 ({min_date})")
        print(f"  1년 최고가:    {max_price:>10,.0f}원 ({max_date})")
        print(f"  1년 평균가:    {avg_price:>10,.0f}원\n")

        print(f"[상승] 상승률 분석")
        print(f"{'─'*60}")
        print(f"  1년 최저가 대비:  {gain_from_min:>8.2f}%")
        print(f"  1년 평균가 대비:  {gain_from_avg:>8.2f}%")
        if gain_from_3m is not None:
            print(f"  3개월 전 대비:    {gain_from_3m:>8.2f}%")
        print()

        # 추세 분석 (선형 회귀)
        x = np.arange(len(df))
        y = df['종가'].values

        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)

        # 추세 방향
        if slope > 0:
            trend_direction = "상승 추세"
            trend_emoji = "[상승]"
        else:
            trend_direction = "하락 추세"
            trend_emoji = "[하락]"

        # R-squared 값 (추세의 강도)
        r_squared = r_value ** 2

        print(f"[분석] 추세 분석")
        print(f"{'─'*60}")
        print(f"  추세 방향:       {trend_emoji} {trend_direction}")
        print(f"  추세 기울기:     {slope:>8.4f}")
        print(f"  추세 강도(R²):   {r_squared:>8.4f} ", end="")

        if r_squared > 0.7:
            print("(강한 추세)")
        elif r_squared > 0.4:
            print("(중간 추세)")
        else:
            print("(약한 추세)")

        # 우상향 패턴 판정
        is_uptrend = slope > 0 and r_squared > 0.3
        print(f"  우상향 패턴:     {'[O] 예' if is_uptrend else '[X] 아니오'}")
        print()

        # 이동평균선 분석
        df['MA20'] = df['종가'].rolling(window=20).mean()
        df['MA60'] = df['종가'].rolling(window=60).mean()
        df['MA200'] = df['종가'].rolling(window=200).mean()

        current_ma20 = df['MA20'].iloc[-1] if not pd.isna(df['MA20'].iloc[-1]) else None
        current_ma60 = df['MA60'].iloc[-1] if not pd.isna(df['MA60'].iloc[-1]) else None
        current_ma200 = df['MA200'].iloc[-1] if not pd.isna(df['MA200'].iloc[-1]) else None

        print(f"[하락] 이동평균선 분석")
        print(f"{'─'*60}")
        if current_ma20:
            ma20_trend = "상승" if current_price > current_ma20 else "하락"
            print(f"  20일 이동평균:   {current_ma20:>10,.0f}원 ({ma20_trend})")

        if current_ma60:
            ma60_trend = "상승" if current_price > current_ma60 else "하락"
            print(f"  60일 이동평균:   {current_ma60:>10,.0f}원 ({ma60_trend})")

        if current_ma200:
            ma200_trend = "상승" if current_price > current_ma200 else "하락"
            print(f"  200일 이동평균:  {current_ma200:>10,.0f}원 ({ma200_trend})")

        # 골든크로스/데드크로스 확인
        if current_ma20 and current_ma60:
            if current_ma20 > current_ma60:
                print(f"  단기/중기:       [O] 골든크로스 (강세)")
            else:
                print(f"  단기/중기:       [X] 데드크로스 (약세)")
        print()

        # 변동성 분석
        returns = df['종가'].pct_change()
        volatility = returns.std() * 100

        print(f"[주의]  변동성 분석")
        print(f"{'─'*60}")
        print(f"  일별 변동성:     {volatility:>8.2f}%", end=" ")

        if volatility > 3.0:
            print("(매우 높음)")
        elif volatility > 2.0:
            print("(높음)")
        elif volatility > 1.0:
            print("(보통)")
        else:
            print("(낮음)")

        # 상승/하락 일수
        up_days = (returns > 0).sum()
        down_days = (returns < 0).sum()
        total_days = len(returns) - 1  # pct_change는 첫날 NaN

        print(f"  상승 일수:       {up_days:>4}일 ({up_days/total_days*100:.1f}%)")
        print(f"  하락 일수:       {down_days:>4}일 ({down_days/total_days*100:.1f}%)")
        print()

        # 최근 모멘텀 (최근 20일)
        recent_df = df.tail(20)
        recent_return = ((recent_df['종가'].iloc[-1] - recent_df['종가'].iloc[0]) / recent_df['종가'].iloc[0]) * 100

        print(f"[HOT] 최근 모멘텀 (20일)")
        print(f"{'─'*60}")
        print(f"  최근 20일 수익률: {recent_return:>8.2f}%")

        if recent_return > 10:
            print(f"  평가:            [급등] 강한 상승 모멘텀")
        elif recent_return > 5:
            print(f"  평가:            [상승] 상승 모멘텀")
        elif recent_return > -5:
            print(f"  평가:            [보합]  보합")
        elif recent_return > -10:
            print(f"  평가:            [하락] 하락 모멘텀")
        else:
            print(f"  평가:            [급락] 강한 하락 모멘텀")

        print(f"\n{'='*60}\n")

        # 결과 딕셔너리 반환
        result = {
            'stock_name': stock_name,
            'stock_code': stock_code,
            'current_price': current_price,
            'min_price': min_price,
            'max_price': max_price,
            'avg_price': avg_price,
            'gain_from_min': gain_from_min,
            'gain_from_avg': gain_from_avg,
            'gain_from_3m': gain_from_3m,
            'slope': slope,
            'r_squared': r_squared,
            'is_uptrend': is_uptrend,
            'volatility': volatility,
            'recent_return': recent_return
        }

        return result

    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """메인 함수"""

    if len(sys.argv) < 2:
        print("사용법: python analyze_stock_trend.py 종목명")
        print("예시: python analyze_stock_trend.py 필옵틱스")
        print("예시: python analyze_stock_trend.py 161580")
        return

    stock_name = sys.argv[1]

    # 분석 실행
    result = analyze_stock_trend(stock_name)

    if result:
        print("분석 완료!")

if __name__ == "__main__":
    main()
