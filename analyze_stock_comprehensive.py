#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
지투지바이오 종합 분석 스크립트
- 1년치 주가/거래량 데이터 수집 (pykrx)
- 기술적 분석 (추세, 이동평균, 거래량)
- 뉴스 분석 데이터 통합
- 종합 투자 의견 생성
"""

import sys
from datetime import datetime, timedelta
from pykrx import stock
import pandas as pd
import numpy as np
from scipy import stats

def get_stock_code(stock_name):
    """종목명으로 종목코드 찾기"""
    # 지투지바이오 종목코드
    return "456160"

def analyze_technical(stock_code, stock_name):
    """기술적 분석 수행"""

    # 1년치 데이터 수집
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)

    print(f"\n{'='*80}")
    print(f"[기술적 분석] {stock_name} ({stock_code})")
    print(f"{'='*80}\n")
    print(f"분석 기간: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")

    # 주가 데이터
    try:
        df = stock.get_market_ohlcv_by_date(
            start_date.strftime("%Y%m%d"),
            end_date.strftime("%Y%m%d"),
            stock_code
        )
    except Exception as e:
        print(f"[ERROR] 데이터 수집 실패: {e}")
        return None

    if df.empty:
        print("[ERROR] 데이터가 없습니다.")
        return None

    print(f"[OK] 총 {len(df)}개 거래일 데이터 수집 완료\n")

    # 현재가 정보
    current_price = df['종가'].iloc[-1]
    prev_price = df['종가'].iloc[-2] if len(df) > 1 else current_price
    change = current_price - prev_price
    change_pct = (change / prev_price * 100) if prev_price != 0 else 0

    print(f"[현재가] {current_price:,}원 ({change:+,}원, {change_pct:+.2f}%)")

    # 기간별 수익률
    prices = df['종가'].values
    if len(prices) >= 20:
        return_20d = (prices[-1] / prices[-20] - 1) * 100
        print(f"[수익률] 최근 20일: {return_20d:+.2f}%")

    if len(prices) >= 60:
        return_60d = (prices[-1] / prices[-60] - 1) * 100
        print(f"[수익률] 최근 60일: {return_60d:+.2f}%")

    if len(prices) >= 90:
        return_90d = (prices[-1] / prices[-90] - 1) * 100
        print(f"[수익률] 최근 90일: {return_90d:+.2f}%")

    # 상장 이후 수익률 (8월 상장)
    days_since_ipo = len(prices)
    return_since_ipo = (prices[-1] / prices[0] - 1) * 100
    print(f"[수익률] 상장 이후 ({days_since_ipo}일): {return_since_ipo:+.2f}%")
    print()

    # 이동평균선
    ma20 = df['종가'].rolling(window=20).mean().iloc[-1] if len(df) >= 20 else None
    ma60 = df['종가'].rolling(window=60).mean().iloc[-1] if len(df) >= 60 else None

    print("[이동평균선 분석]")
    if ma20:
        print(f"  - MA20: {ma20:,.0f}원 ({'위' if current_price > ma20 else '아래'})")
    if ma60:
        print(f"  - MA60: {ma60:,.0f}원 ({'위' if current_price > ma60 else '아래'})")

    # 골든/데드 크로스
    if ma20 and ma60:
        if current_price > ma20 > ma60:
            print("  [+] 골든크로스 (상승 추세)")
        elif current_price < ma20 < ma60:
            print("  [-] 데드크로스 (하락 추세)")
        else:
            print("  [=] 중립 (추세 불명확)")
    print()

    # 거래량 분석
    volumes = df['거래량'].values
    current_volume = volumes[-1]
    avg_volume_20 = np.mean(volumes[-20:]) if len(volumes) >= 20 else current_volume
    avg_volume_60 = np.mean(volumes[-60:]) if len(volumes) >= 60 else current_volume

    volume_change_20 = ((current_volume / avg_volume_20) - 1) * 100 if avg_volume_20 != 0 else 0

    print("[거래량 분석]")
    print(f"  - 현재 거래량: {current_volume:,}주")
    print(f"  - 20일 평균: {avg_volume_20:,.0f}주")
    print(f"  - 60일 평균: {avg_volume_60:,.0f}주")
    print(f"  - 20일 평균 대비: {volume_change_20:+.1f}%")

    if volume_change_20 > 50:
        print("  [+] 거래량 급증 (관심 증가)")
    elif volume_change_20 < -30:
        print("  [-] 거래량 감소 (관심 감소)")
    else:
        print("  [=] 정상 거래량")
    print()

    # 추세 분석 (선형 회귀)
    if len(prices) >= 60:
        x = np.arange(len(prices[-60:]))
        y = prices[-60:]
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)

        r_squared = r_value ** 2
        trend_direction = "상승" if slope > 0 else "하락"
        trend_strength = "강함" if r_squared > 0.5 else "보통" if r_squared > 0.3 else "약함"

        print(f"[60일 추세 분석]")
        print(f"  - 추세 방향: {trend_direction}")
        print(f"  - 추세 강도: {trend_strength} (R^2 = {r_squared:.3f})")
        print(f"  - 일평균 변화: {slope:+,.0f}원")
    print()

    # 변동성 분석
    volatility_20 = df['종가'].pct_change().tail(20).std() * 100 if len(df) >= 20 else 0
    volatility_60 = df['종가'].pct_change().tail(60).std() * 100 if len(df) >= 60 else 0

    print(f"[변동성 분석]")
    print(f"  - 20일 변동성: {volatility_20:.2f}%")
    print(f"  - 60일 변동성: {volatility_60:.2f}%")

    if volatility_20 > 5:
        print("  [-] 높은 변동성 (고위험)")
    elif volatility_20 > 3:
        print("  [=] 보통 변동성")
    else:
        print("  [+] 낮은 변동성 (안정적)")
    print()

    # 가격 밴드 (52주 최고/최저)
    high_52w = df['고가'].max()
    low_52w = df['저가'].min()
    current_position = ((current_price - low_52w) / (high_52w - low_52w) * 100) if (high_52w - low_52w) != 0 else 50

    print(f"[가격 밴드 - 상장 이후]")
    print(f"  - 최고가: {high_52w:,}원")
    print(f"  - 최저가: {low_52w:,}원")
    print(f"  - 현재 위치: {current_position:.1f}% (최저 대비)")

    if current_position > 80:
        print("  [-] 고점 근처 (조정 가능성)")
    elif current_position < 20:
        print("  [+] 저점 근처 (반등 가능성)")
    else:
        print("  [=] 중간 수준")
    print()

    # 종합 점수 계산
    score = 0
    reasons = []

    # 추세 점수
    if len(prices) >= 60:
        if slope > 0 and r_squared > 0.3:
            score += 2
            reasons.append("상승 추세 지속")
        elif slope > 0:
            score += 1
            reasons.append("약한 상승 추세")
        elif slope < 0 and r_squared > 0.3:
            score -= 2
            reasons.append("하락 추세 지속")
        else:
            score -= 1
            reasons.append("약한 하락 추세")

    # 이동평균 점수
    if ma20 and ma60:
        if current_price > ma20 > ma60:
            score += 2
            reasons.append("골든크로스 형성")
        elif current_price > ma20:
            score += 1
            reasons.append("단기 이평선 위")
        elif current_price < ma20 < ma60:
            score -= 2
            reasons.append("데드크로스 형성")
        else:
            score -= 1
            reasons.append("단기 이평선 아래")

    # 거래량 점수
    if volume_change_20 > 50:
        score += 1
        reasons.append("거래량 급증")
    elif volume_change_20 < -30:
        score -= 1
        reasons.append("거래량 급감")

    # 최종 의견
    print("="*80)
    print("[기술적 분석 종합]")
    print("="*80)
    print(f"\n종합 점수: {score}/5")
    print("\n주요 근거:")
    for i, reason in enumerate(reasons, 1):
        print(f"  {i}. {reason}")

    if score >= 3:
        technical_opinion = "BUY"
        print(f"\n[+] 기술적 의견: **{technical_opinion}** - 강한 상승 추세")
    elif score >= 1:
        technical_opinion = "HOLD"
        print(f"\n[=] 기술적 의견: **{technical_opinion}** - 보통, 관망 필요")
    else:
        technical_opinion = "SELL"
        print(f"\n[-] 기술적 의견: **{technical_opinion}** - 약세 또는 조정 필요")

    print("\n" + "="*80 + "\n")

    return {
        'current_price': current_price,
        'change_pct': change_pct,
        'return_20d': return_20d if len(prices) >= 20 else None,
        'return_60d': return_60d if len(prices) >= 60 else None,
        'return_since_ipo': return_since_ipo,
        'ma20': ma20,
        'ma60': ma60,
        'volume_change_20': volume_change_20,
        'volatility_20': volatility_20,
        'high_52w': high_52w,
        'low_52w': low_52w,
        'score': score,
        'technical_opinion': technical_opinion,
        'reasons': reasons
    }

if __name__ == "__main__":
    stock_name = "지투지바이오"
    stock_code = get_stock_code(stock_name)

    result = analyze_technical(stock_code, stock_name)

    if result:
        print("\n[OK] 분석 완료!")
        print(f"\n기술적 의견: {result['technical_opinion']}")
        print(f"현재가: {result['current_price']:,}원")
        print(f"상장 이후 수익률: {result['return_since_ipo']:+.2f}%")
