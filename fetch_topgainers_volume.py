import sys
from fetch_stock_prices import get_stock_info, get_realtime_price_naver
from datetime import datetime

# topgainers 종목 리스트
stock_list = [
    # 상한가 종목
    ('핀텔', '291810'),
    ('LS티라유텍', '322180'),
    ('유라클', '088340'),
    ('디아이씨', '092200'),
    ('이노인스트루먼트', '215790'),
    ('대한광통신', '010170'),
    ('티로보틱스', '117730'),
    ('노타', '486990'),
    # TOP 20
    ('HD현대에너지솔루션', '322000'),
    ('코아스', '071950'),
    ('효성', '004800'),
    ('로보티즈', '108490'),
    ('필옵틱스', '161580'),
    ('켐트로닉스', '089010'),
    ('두산로보틱스', '454910'),
    ('일동제약', '249420'),
    ('E8', '418620'),
    ('로보스타', '090360'),
    ('대원전선', '006340'),
    ('프리시젼바이오', '335810'),
    ('클로봇', '466100'),
    ('기가레인', '049080'),
    ('태성', '323280'),
    ('테이팩스', '055490'),
    ('포스코DX', '022100'),
    ('OCI홀딩스', '010060'),
    ('에이스테크', '088800'),
    ('LS ELECTRIC', '010120'),
]

def main():
    date_str = '2025-11-03'

    print(f"날짜: {date_str}")
    print(f"종목 수: {len(stock_list)}")
    print("\n거래대금 정보 (억원 단위):")
    print("=" * 80)

    trading_values = {}

    for stock_name, stock_code in stock_list:
        try:
            # KRX 공식 데이터에서 가져오기
            info = get_stock_info(stock_code, date_str)

            if info is not None and not info.empty:
                # DataFrame에서 거래대금 추출
                trading_value = info['거래대금'].iloc[0]
                # 억원 단위로 변환 (거래대금은 원 단위)
                trading_value_eok = trading_value / 100_000_000
                trading_values[stock_code] = trading_value_eok
                print(f"{stock_name:20s} ({stock_code}): {trading_value_eok:>10.0f}억원")
            else:
                # 실시간 데이터에서는 거래대금을 직접 제공하지 않으므로 0으로 처리
                print(f"{stock_name:20s} ({stock_code}): 데이터 없음 (당일)")
                trading_values[stock_code] = 0
        except Exception as e:
            print(f"{stock_name:20s} ({stock_code}): 오류 - {e}")
            trading_values[stock_code] = 0

    print("=" * 80)
    print(f"\n완료! 총 {len(trading_values)}개 종목 조회")

    # 결과 저장 (Python dict 형식)
    output_file = 'topgainers_trading_value_data.txt'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# 거래대금 데이터 (억원 단위)\n")
        f.write(f"# 날짜: {date_str}\n\n")
        for stock_code, trading_value in trading_values.items():
            f.write(f"'{stock_code}': {trading_value:.0f},\n")

    print(f"\n거래대금 데이터가 '{output_file}' 파일로 저장되었습니다.")

if __name__ == "__main__":
    main()
