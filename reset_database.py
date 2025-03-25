import sqlite3
import random
import hashlib

# 비밀번호 해시 함수
def hash_password(password, salt=None):
    if salt is None:
        salt = str(random.randint(1000, 9999))
    
    salted_password = f"{salt}{password}"
    hashed = hashlib.sha256(salted_password.encode()).hexdigest()
    
    return f"{salt}${hashed}"

# 데이터베이스 초기화 및 마이그레이션 함수
def init_database():
    try:
        conn = sqlite3.connect("leave_management.db")
        cursor = conn.cursor()

        # 직원 테이블 생성
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            total_leave INTEGER DEFAULT 14,
            used_leave REAL DEFAULT 0
        )
        """)

        # 휴가 신청 테이블 생성
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS leave_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            days REAL NOT NULL,
            leave_type TEXT NOT NULL,
            status TEXT DEFAULT 'PENDING'
        )
        """)

        conn.commit()
        conn.close()
    except Exception as e:
        st.error(f"데이터베이스 초기화 중 오류 발생: {e}")

        # 기존 테이블에 새 컬럼 추가 (이미 존재하면 무시됨)
        try:
            cursor.execute("ALTER TABLE leave_requests ADD COLUMN start_date DATE")
        except sqlite3.OperationalError:
            pass

        try:
            cursor.execute("ALTER TABLE leave_requests ADD COLUMN end_date DATE")
        except sqlite3.OperationalError:
            pass

        try:
            cursor.execute("ALTER TABLE leave_requests ADD COLUMN leave_type TEXT")
        except sqlite3.OperationalError:
            pass

        # 기존 데이터가 있다면 default 값 업데이트
        cursor.execute("""
        UPDATE leave_requests 
        SET start_date = request_date, 
            end_date = request_date, 
            leave_type = 'FULL_DAY'
        WHERE start_date IS NULL
        """)

        conn.commit()
        conn.close()
        print("데이터베이스가 초기화되었습니다!")
    except Exception as e:
        print(f"데이터베이스 초기화 중 오류 발생: {e}")

# 데이터베이스에 초기 사용자 추가 함수
def reset_database():
    # 데이터베이스 연결
    conn = sqlite3.connect("leave_management.db")
    cursor = conn.cursor()

    # 기존 동적으로 추가된 테이블 데이터는 삭제하고 초기 데이터만 유지
    cursor.execute("DELETE FROM leave_requests")
    cursor.execute("DELETE FROM employees")

    # 포켓몬 이름들
    pokemon_names = ["이상해", "피카츄", "파이리", "꼬부기", "버터플", "야도란", "피존투", "또가스", "식스테", "팬텀"]
    password = "1234qwer"

    # 초기 데이터 삽입
    for name in pokemon_names:
        total_leave = random.choice([14, 15, 16])  # total_leave는 14, 15, 16 중 랜덤
        used_leave = random.randint(0, total_leave)  # used_leave는 total_leave 이하로 랜덤
        
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
    init_database()  # 데이터베이스 초기화 및 마이그레이션
    reset_database()  # 초기 데이터 삽입
