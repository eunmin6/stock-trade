# 📊 주식 포트폴리오 분석 도구

주식 보유 현황을 분석하고 시각화하는 Python 도구입니다.

## 🚀 주요 기능

- **포트폴리오 분석**: 전체 수익률, 종목별 손익 등 상세 분석
- **매도 거래 분석**: 일일 매도 거래 내역과 손익 분석
- **뉴스 분석**: 네이버 뉴스 크롤링 및 호재/악재 자동 분석
- **시각화**: 6개 차트로 포트폴리오 현황을 한눈에 파악
- **마크다운 리포트**: GitHub에서 바로 확인 가능한 리포트 생성
- **날짜별 관리**: 날짜별로 데이터와 리포트를 체계적으로 관리
- **신용/현금 통합**: 같은 종목의 신용/현금 투자를 자동으로 합산
- **정찰병 제외**: 보유 수량 1개인 정찰병 종목은 통계에서 제외

## 📁 프로젝트 구조

```
stock-trade/
├── analyze_holdings.py    # 보유 종목 분석 스크립트
├── analyze_tradings.py    # 매도 거래 분석 스크립트
├── analyze_news.py        # 뉴스 크롤링 및 분석 스크립트
├── requirements.txt        # 필요한 Python 패키지
├── data/                   # 데이터 폴더 (gitignore)
│   └── YYYY-MM-DD/
│       ├── holdings.xlsx   # 날짜별 보유 종목 데이터
│       └── tradings.xlsx   # 날짜별 매도 거래 데이터
└── report/                 # 리포트 출력 폴더
    └── YYYY-MM-DD/
        ├── holdings.png    # 보유 종목 시각화 차트
        ├── holdings.md     # 보유 종목 마크다운 리포트
        ├── tradings.png    # 매도 거래 시각화 차트
        ├── tradings.md     # 매도 거래 마크다운 리포트
        └── news_종목명.md  # 종목별 뉴스 분석 리포트
```

## 🛠️ 설치 방법

1. 저장소 클론
```bash
git clone https://github.com/eunmin6/stock-trade.git
cd stock-trade
```

2. 가상환경 생성 및 활성화 (선택사항)
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

3. 필요한 패키지 설치
```bash
pip install -r requirements.txt
```

## 📊 사용 방법

### 1. 보유 종목 분석

1. **데이터 준비**: `data/YYYY-MM-DD/holdings.xlsx` 형식으로 엑셀 파일 배치

2. **분석 실행**:
```bash
# 오늘 날짜 데이터 분석
python analyze_holdings.py

# 특정 날짜 데이터 분석
python analyze_holdings.py 2025-11-03
```

3. **결과 확인**: `report/YYYY-MM-DD/` 폴더에서 결과 확인
   - `holdings.png`: 시각화 차트
   - `holdings.md`: 마크다운 리포트

### 2. 매도 거래 분석

1. **데이터 준비**: `data/YYYY-MM-DD/tradings.xlsx` 형식으로 엑셀 파일 배치

2. **분석 실행**:
```bash
# 오늘 날짜 데이터 분석
python analyze_tradings.py

# 특정 날짜 데이터 분석
python analyze_tradings.py 2025-11-03
```

3. **결과 확인**: `report/YYYY-MM-DD/` 폴더에서 결과 확인
   - `tradings.png`: 시각화 차트
   - `tradings.md`: 마크다운 리포트

### 3. 뉴스 분석

1. **분석 실행**:
```bash
# 종목명으로 뉴스 분석 (최근 14일)
python analyze_news.py "삼성전자"
python analyze_news.py "SK하이닉스"

# 실행 시 종목명 입력
python analyze_news.py
```

2. **결과 확인**: `report/YYYY-MM-DD/` 폴더에서 결과 확인
   - `news_종목명.md`: 뉴스 분석 마크다운 리포트
   - 호재성 뉴스, 악재성 뉴스, 중립 뉴스 분류
   - 각 뉴스별 영향도(⭐) 표시

## 📈 출력 예시

### 시각화 차트 (holdings.png)
- 수익/손실 비율 (파이 차트)
- 종목별 비중 (파이 차트)
- 수익률 상위/하위 종목 (바 차트)
- 전체 종목 평가손익 (바 차트)
- 매입금액 vs 평가금액 (산점도)
- 포트폴리오 요약 통계
- **종목별 수익/손실 상세 테이블**

### 마크다운 리포트 (holdings.md)
- 전체 포트폴리오 현황
- 수익/손실 분류
- 종목별 수익/손실 상세 테이블
- 수익률 분석 (상위/하위 5개)
- 포트폴리오 비중
- 신용거래 현황

## 📋 필요한 패키지

- pandas >= 2.3.3
- openpyxl >= 3.1.5
- matplotlib >= 3.10.7
- seaborn >= 0.13.2
- numpy >= 2.3.4
- requests >= 2.32.5
- beautifulsoup4 >= 4.14.2
- lxml >= 6.0.2

## 🔒 개인정보 보호

- `data/` 폴더는 `.gitignore`에 포함되어 개인 거래 데이터가 저장소에 올라가지 않습니다.
- 리포트는 선택적으로 공유할 수 있습니다.

## 🤖 개발 도구

이 프로젝트는 [Claude Code](https://claude.com/claude-code)를 사용하여 개발되었습니다.

## 📝 라이선스

MIT License
