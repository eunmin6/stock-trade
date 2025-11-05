#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
종목 기술적 분석 스크립트
- 3년치 주가/거래량 데이터 수집 (pykrx)
- 기술적 분석 (추세, 이동평균, 거래량, 변동성)
"""

import sys
from datetime import datetime, timedelta
from pykrx import stock
import pandas as pd
import numpy as np
from scipy import stats

def analyze_technical(stock_code, stock_name):
    """기술적 분석 수행"""

    # 3년치 데이터 수집
    end_date = datetime.now()
    start_date = end_date - timedelta(days=1095)  # 3 years

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

    # 기간별 수익률
    prices = df['종가'].values
    return_20d = (prices[-1] / prices[-20] - 1) * 100 if len(prices) >= 20 else 0
    return_60d = (prices[-1] / prices[-60] - 1) * 100 if len(prices) >= 60 else 0
    return_90d = (prices[-1] / prices[-90] - 1) * 100 if len(prices) >= 90 else 0
    return_3y = (prices[-1] / prices[0] - 1) * 100

    # 이동평균선
    ma20 = df['종가'].rolling(window=20).mean().iloc[-1] if len(df) >= 20 else None
    ma60 = df['종가'].rolling(window=60).mean().iloc[-1] if len(df) >= 60 else None

    # 골든/데드 크로스 판정
    golden_cross = False
    dead_cross = False
    if ma20 and ma60:
        if current_price > ma20 > ma60:
            golden_cross = True
        elif current_price < ma20 < ma60:
            dead_cross = True

    # 거래량 분석
    volumes = df['거래량'].values
    current_volume = volumes[-1]
    avg_volume_20d = np.mean(volumes[-20:]) if len(volumes) >= 20 else current_volume
    avg_volume_60d = np.mean(volumes[-60:]) if len(volumes) >= 60 else current_volume
    volume_change_20d = ((current_volume / avg_volume_20d) - 1) * 100 if avg_volume_20d > 0 else 0

    # 추세 분석 (60일)
    if len(prices) >= 60:
        x = np.arange(60)
        y = prices[-60:]
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
        trend_strength = r_value ** 2  # R²
        daily_change = slope
    else:
        trend_strength = 0
        daily_change = 0

    # 변동성 (20일)
    if len(prices) >= 21:
        returns = np.diff(prices[-21:]) / prices[-21:-1]
        volatility_20d = np.std(returns) * 100
    else:
        volatility_20d = 0

    # 3년 최고/최저
    high_3y = np.max(prices)
    low_3y = np.min(prices)
    position_pct = ((current_price - low_3y) / (high_3y - low_3y) * 100) if (high_3y - low_3y) > 0 else 50

    # 결과 저장 (numpy 타입을 Python 기본 타입으로 변환)
    result = {
        'stock_code': stock_code,
        'stock_name': stock_name,
        'current_price': int(current_price),
        'change': int(change),
        'change_pct': float(change_pct),
        'return_20d': float(return_20d),
        'return_60d': float(return_60d),
        'return_90d': float(return_90d),
        'return_3y': float(return_3y),
        'ma20': float(ma20) if ma20 is not None else None,
        'ma60': float(ma60) if ma60 is not None else None,
        'golden_cross': bool(golden_cross),
        'dead_cross': bool(dead_cross),
        'current_volume': int(current_volume),
        'avg_volume_20d': float(avg_volume_20d),
        'avg_volume_60d': float(avg_volume_60d),
        'volume_change_20d': float(volume_change_20d),
        'trend_strength': float(trend_strength),
        'daily_change': float(daily_change),
        'volatility_20d': float(volatility_20d),
        'high_3y': int(high_3y),
        'low_3y': int(low_3y),
        'position_pct': float(position_pct),
        'trading_days': int(len(df))
    }

    return result

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python analyze_stock_technical.py <종목명> <종목코드>")
        sys.exit(1)

    stock_name = sys.argv[1]
    stock_code = sys.argv[2]

    result = analyze_technical(stock_code, stock_name)

    if result:
        print("\n" + "="*80)
        print("기술적 분석 결과")
        print("="*80)
        print(f"\n종목명: {result['stock_name']} ({result['stock_code']})")
        print(f"현재가: {result['current_price']:,}원 ({result['change']:+,}원, {result['change_pct']:+.2f}%)")
        print(f"\n[수익률]")
        print(f"  20일: {result['return_20d']:+.2f}%")
        print(f"  60일: {result['return_60d']:+.2f}%")
        print(f"  90일: {result['return_90d']:+.2f}%")
        print(f"  3년: {result['return_3y']:+.2f}%")
        print(f"\n[이동평균선]")
        if result['ma20']:
            print(f"  MA20: {result['ma20']:,.0f}원 ({'위' if result['current_price'] > result['ma20'] else '아래'})")
        if result['ma60']:
            print(f"  MA60: {result['ma60']:,.0f}원 ({'위' if result['current_price'] > result['ma60'] else '아래'})")
        if result['golden_cross']:
            print(f"  판정: 골든크로스 (강한 상승 추세)")
        elif result['dead_cross']:
            print(f"  판정: 데드크로스 (하락 추세)")
        else:
            print(f"  판정: 중립")
        print(f"\n[거래량]")
        print(f"  현재: {result['current_volume']:,}주")
        print(f"  20일 평균: {result['avg_volume_20d']:,.0f}주")
        print(f"  20일 대비: {result['volume_change_20d']:+.1f}%")
        print(f"\n[추세 분석 (60일)]")
        print(f"  강도: R² = {result['trend_strength']:.3f}")
        print(f"  일평균 변화: {result['daily_change']:+,.0f}원")
        print(f"\n[변동성]")
        print(f"  20일: {result['volatility_20d']:.2f}%")
        print(f"\n[가격 위치 (3년)]")
        print(f"  최고가: {result['high_3y']:,}원")
        print(f"  최저가: {result['low_3y']:,}원")
        print(f"  현재 위치: {result['position_pct']:.1f}%")
        print("\n" + "="*80)

        # JSON으로도 출력 (통합 리포트 생성 시 사용)
        import json
        with open(f'report/.temp-news/technical_{stock_name}_{datetime.now().strftime("%Y-%m-%d")}.json', 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print(f"\n[OK] 기술적 분석 데이터가 JSON 파일로 저장되었습니다.")
    else:
        print("\n[ERROR] 기술적 분석 실패")
        sys.exit(1)
