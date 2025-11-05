import re
from pathlib import Path

# 파일 경로 설정
report_dir = Path(__file__).parent.parent / "report" / "tradings"

# 수정할 파일 목록
files_to_fix = [
    "2025-10-23.md",
    "2025-10-27.md",
    "2025-10-28.md",
    "2025-10-29.md",
    "2025-10-30.md",
    "2025-10-31.md",
    "2025-11-03.md",
    "2025-11-04.md"
]

# 추가할 테이블 헤더
table_header = """| 순위 | 종목명 | 거래타입 | 시작시간 | 종료시간 | 보유시간 | 분할매수 | 분할매도 | 시총(억) | 거래대금(억) | 매입금액 | 매도금액 | 손익금액 | 수익률 |
|------|--------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|--------|
"""

def fix_table_header(file_path):
    """테이블 헤더가 빠진 '거래별 손익 상세' 섹션에 헤더 추가"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # '## 💰 거래별 손익 상세' 다음에 오는 첫 번째 테이블 행 찾기
    # 패턴: ## 💰 거래별 손익 상세 다음에 빈 줄이 오고, | 1 |로 시작하는 행
    pattern = r'(## 💰 거래별 손익 상세\n\n)((\| \d+ \|.+\n)+)'

    def replace_func(match):
        section_title = match.group(1)
        table_rows = match.group(2)
        return section_title + table_header + table_rows

    # 패턴이 매치되는지 확인
    if re.search(pattern, content):
        new_content = re.sub(pattern, replace_func, content)

        # 변경사항이 있는 경우에만 파일 쓰기
        if new_content != content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            return True
    return False

# 모든 파일 처리
print("Starting table header fix...\n")
fixed_count = 0

for filename in files_to_fix:
    file_path = report_dir / filename
    if file_path.exists():
        if fix_table_header(file_path):
            print(f"Fixed: {filename}")
            fixed_count += 1
        else:
            print(f"No fix needed: {filename}")
    else:
        print(f"Not found: {filename}")

print(f"\nComplete: {fixed_count}/{len(files_to_fix)} files fixed")
