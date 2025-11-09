"""
SA20 리포트 생성 - 시가총액 + 텍스트 차트 포함
"""
import json
import os
from datetime import datetime
from anthropic import Anthropic

# API 키 설정
client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

# 데이터 로드
with open('news_data.json', 'r', encoding='utf-8') as f:
    news_data = json.load(f)

with open('technical_data.json', 'r', encoding='utf-8') as f:
    tech_data = json.load(f)

stock_name = news_data['stock_name']
stock_code = news_data['stock_code']
analysis_date = news_data['analysis_date']

# 프롬프트 생성
prompt = f"""당신은 한국 주식 시장 전문 애널리스트입니다. 아래 데이터를 바탕으로 **{stock_name}({stock_code})** 종목에 대한 깊이 있는 분석 리포트를 작성해주세요.

## 제공된 데이터

### 1. 시가총액 및 기본 정보
- **시가총액**: {tech_data['market_cap_uk']:,}억원
- **현재가**: {tech_data['current_price']:,}원

### 2. 뉴스 데이터 ({news_data['news_count']}건)
"""

for i, article in enumerate(news_data['news'], 1):
    prompt += f"\n[뉴스 {i}]\n"
    prompt += f"제목: {article['title']}\n"
    prompt += f"날짜: {article['date']}\n"
    prompt += f"출처: {article['press']}\n"
    prompt += f"내용: {article['content']}\n"
    prompt += f"링크: {article['link']}\n"

prompt += f"""

### 3. 기술적 분석 데이터
- 52주 최고가: {tech_data['week52_high']:,}원
- 52주 최저가: {tech_data['week52_low']:,}원
- 3년 평균 주가: {tech_data['avg_3y_price']:,}원
- 이동평균선:
  - MA5: {tech_data['ma5']:,}원
  - MA20: {tech_data['ma20']:,}원
  - MA60: {tech_data['ma60']:,}원
  - MA120: {tech_data['ma120']:,}원
- 거래량:
  - 3년 평균: {tech_data['avg_3y_volume']:,}주
  - 최근 1개월 평균: {tech_data['avg_1m_volume']:,}주
- 3개월 변동성: {tech_data['volatility_3m']}%
- 지지선: {', '.join(map(lambda x: f"{x:,}원", tech_data['supports']))}
- 저항선: {', '.join(map(lambda x: f"{x:,}원", tech_data['resistances']))}

### 4. 최근 3개월 주가 차트 (텍스트)
```
{tech_data['text_chart']}
```
(단위: 천원, 예: 21 = 21,000원)

---

## 리포트 작성 요구사항

다음 구조로 마크다운 리포트를 작성해주세요:

### 헤더 정보
```markdown
# {stock_name}({stock_code}) 종합 분석 리포트

**분석일**: {analysis_date}
**시가총액**: {tech_data['market_cap_uk']:,}억원
**현재가**: {tech_data['current_price']:,}원
```

### 섹션 A: 종목 정체성 파악
- 이 회사는 무엇을 하는 회사인가?
- 주력 사업과 최근 사업 변화는?
- 업계 내 위치는?

### 섹션 B: 주가 변동 핵심 원인
- **최근 2주 뉴스를 종합하여**, 주가 상승/하락의 **진짜 이유** 3~5가지를 찾아내세요.
- 단순 키워드가 아니라, **왜 그것이 주가에 영향을 주는지** 논리적으로 설명하세요.
- 각 원인마다 다음 형식으로 정리:
  ```markdown
  #### [원인 X]: (제목)
  - **카테고리**: 실적/신사업/제품/규제/시장 환경 등
  - **영향도**: 상/중/하
  - **상세 내용**: (2~3문장)
  - **근거 뉴스**: [뉴스 제목](링크)
  ```

### 섹션 C: 긍정 요인 상세
| 구분 | 내용 | 근거 뉴스 |
|------|------|-----------|
| ... | ... | ... |

### 섹션 D: 부정 요인 상세
| 구분 | 내용 | 근거 뉴스 |
|------|------|-----------|
| ... | ... | ... |

### 섹션 E: 종합 요약
- 3~5문장으로 이 종목의 핵심을 요약하세요.

### 섹션 F: 최근 3개월 주가 흐름 분석
```
{tech_data['text_chart']}
```
- 위 텍스트 차트를 보고, 최근 3개월 동안의 주가 흐름을 분석하세요.
- 주요 변곡점, 지지/저항 구간, 추세 방향 등을 설명하세요.

### 섹션 G: 기술적 분석
- 이동평균선 배열, 거래량 변화, 변동성 등을 종합하여 기술적 관점 평가
- 현재 주가 위치(52주 최고/최저 대비)
- 지지선/저항선 분석

### 섹션 H: 투자 시나리오
1. **낙관 시나리오**: 어떤 일이 일어나면 주가가 더 오를까?
2. **기본 시나리오**: 현재 추세가 유지되면?
3. **비관 시나리오**: 어떤 리스크가 현실화되면 하락할까?

### 섹션 I: 매매 전략 제안
#### 1. 데이 트레이딩 적합성
- 적합 여부: 예/아니오
- 근거: (변동성, 거래량, 일중 등락 패턴 등)
- 추천 진입/청산 시점

#### 2. 스윙 트레이딩 적합성
- 적합 여부: 예/아니오
- 근거: (중기 추세, 펀더멘털 변화, 모멘텀 등)
- 추천 진입 가격대
- 목표 가격 및 손절 가격

---

**중요**:
- 모든 분석은 **제공된 뉴스와 데이터에 근거**해야 합니다.
- 추측이나 일반론이 아니라, **구체적인 사실과 숫자**를 기반으로 작성하세요.
- 투자 권유가 아니라 **객관적 분석**임을 명시하세요.

리포트를 마크다운 형식으로 작성해주세요.
"""

print("Claude API 호출 중...")
print(f"토큰 예상: 약 {len(prompt) // 4} tokens (입력)")

# API 호출
response = client.messages.create(
    model="claude-3-7-sonnet-20250219",
    max_tokens=16000,
    temperature=0.3,
    messages=[{
        "role": "user",
        "content": prompt
    }]
)

report = response.content[0].text

# 리포트 저장
report_dir = f"report/analysis"
os.makedirs(report_dir, exist_ok=True)

report_filename = f"{report_dir}/{stock_name}-{analysis_date}.md"
with open(report_filename, 'w', encoding='utf-8') as f:
    f.write(report)

print(f"\n리포트 생성 완료!")
print(f"저장 위치: {report_filename}")
print(f"\n입력 토큰: {response.usage.input_tokens}")
print(f"출력 토큰: {response.usage.output_tokens}")
print(f"총 토큰: {response.usage.input_tokens + response.usage.output_tokens}")
