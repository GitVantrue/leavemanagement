import sqlite3
import random

# 데이터베이스 연결
conn = sqlite3.connect("leave_management.db")
cursor = conn.cursor()

# 직원 테이블 생성
cursor.execute("""
CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    total_leave INTEGER,
    used_leave INTEGER
)
""")

# 직원 정보 추가
pokemon_names = ["이상해", "피카츄", "파이리", "꼬부기", "버터플", "야도란", "피존투", "또가스", "식스테", "팬텀"]
password = "1234qwer!"
leave_days = [14, 15, 16] * 3 + [15]  # 총 10명

# 기존 데이터 삭제 후 재생성
cursor.execute("DELETE FROM employees")

for name in pokemon_names:
    total_leave = random.choice(leave_days)
    used_leave = random.randint(5, min(total_leave, 12))  # 사용 연차 (최소 5일, 최대 12일)
    cursor.execute("INSERT INTO employees (username, password, total_leave, used_leave) VALUES (?, ?, ?, ?)", 
                   (name, password, total_leave, used_leave))

conn.commit()
conn.close()
print("직원 계정 10개 생성 완료!")


