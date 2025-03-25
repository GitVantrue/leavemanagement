import sqlite3
import random
import hashlib

# 비밀번호 해시 함수 (기존 앱과 동일하게)
def hash_password(password, salt=None):
    if salt is None:
        salt = str(random.randint(1000, 9999))
    
    salted_password = f"{salt}{password}"
    hashed = hashlib.sha256(salted_password.encode()).hexdigest()
    
    return f"{salt}${hashed}"

# 데이터베이스 초기화 및 초기 데이터 복원 함수
def reset_database():
    # 데이터베이스 연결
    conn = sqlite3.connect("leave_management.db")
    cursor = conn.cursor()

    # 기존 동적으로 추가된 테이블 데이터는 삭제하고 초기 데이터만 유지
    cursor.execute("DELETE FROM leave_requests")
    cursor.execute("DELETE FROM employees")

    # 포켓몬 이름들
    pokemon_names = ["이상해", "피카츄", "파이리", "꼬부기", "버터플", "야도란", "피존투", "또가스", "식스테", "팬텀"]
    password = "1234qwer!"
    leave_days = [14, 15, 16] * 3 + [15]  # 총 10명

    # 초기 데이터 삽입
    for name in pokemon_names:
        total_leave = random.choice(leave_days)
        used_leave = random.randint(0, min(total_leave, 7))  # 사용 연차 (최소 0일, 최대 7일)
        
        # 비밀번호 해시화
        hashed_password = hash_password(password)
        
        cursor.execute("""
            INSERT INTO employees (username, password, total_leave, used_leave) 
            VALUES (?, ?, ?, ?)
        """, (name, hashed_password, total_leave, used_leave))

    conn.commit()
    conn.close()
    print("데이터베이스가 초기 상태로 리셋되었습니다!")

# 직접 실행할 경우
if __name__ == "__main__":
    reset_database()
