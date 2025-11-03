from bs4 import BeautifulSoup

html_file = 'data/2025-11-03/topgainers.html'

with open(html_file, 'r', encoding='utf-8') as f:
    html_content = f.read()

soup = BeautifulSoup(html_content, 'html.parser')

# 테이블 찾기
table = soup.find('table', class_='tbl')
if table:
    rows = table.find_all('tr')
    print(f"총 {len(rows)}개 행 발견")

    # 첫 번째 데이터 행 확인
    for idx, row in enumerate(rows[2:7]):
        cols = row.find_all('td')
        print(f"\n행 {idx+2}: {len(cols)}개 컬럼")

        if len(cols) >= 3:
            first_col = cols[0]
            link = first_col.find('a')

            if link:
                print(f"  전체 컬럼 텍스트:")
                col_text = first_col.get_text(separator='|||').strip()
                text_parts = [part.strip() for part in col_text.split('|||') if part.strip()]
                print(f"  Parts: {text_parts}")
                print(f"  Parts count: {len(text_parts)}")
else:
    print("테이블을 찾을 수 없음")
