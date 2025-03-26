import sqlite3
import random
import hashlib
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional


# 데이터베이스 연결 유틸리티
def get_db_connection():
    conn = sqlite3.connect("leave_management.db")
    conn.row_factory = sqlite3.Row
    return conn

# 비밀번호 해시 함수 (Streamlit 앱과 동일)
def hash_password(password, salt=None):
    if salt is None:
        salt = str(random.randint(1000, 9999))

    salted_password = f"{salt}{password}"
    hashed = hashlib.sha256(salted_password.encode()).hexdigest()

    return f"{salt}${hashed}"

def verify_password(stored_password, provided_password):
    try:
        salt, hashed = stored_password.split('$')
        new_hash = hashlib.sha256(f"{salt}{provided_password}".encode()).hexdigest()
        return new_hash == hashed
    except:
        return False

# 날짜 범위 내 날짜 계산 함수 (Streamlit 앱과 동일)
def calculate_working_days(start_date, end_date, leave_type):
    start = datetime.strptime(str(start_date), "%Y-%m-%d")
    end = datetime.strptime(str(end_date), "%Y-%m-%d")
    
    # 반차인 경우 하루 이상 선택 불가
    if (leave_type == 'MORNING_HALF' or leave_type == 'AFTERNOON_HALF'):
        if start_date != end_date:
            return {"error": "반차는 하루만 선택 가능합니다"}
        return {"days": 0.5}
    
    # 주말을 제외한 날짜 계산
    days = 0
    current = start
    while current <= end:
        # 주말 제외 (토요일(5)과 일요일(6) 제외)
        if current.weekday() < 5:
            days += 1
        current += timedelta(days=1)
    
    return {"days": days}

# Pydantic 모델
class UserCreate(BaseModel):
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class LeaveRequest(BaseModel):
    start_date: str
    end_date: str
    leave_type: str

class LeaveResponse(BaseModel):
    id: int
    username: str
    start_date: str
    end_date: str
    days: float
    leave_type: str
    status: str

# FastAPI 앱 생성
app = FastAPI(title="연차 관리 시스템 API")

# CORS 미들웨어 추가
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 모든 오리진 허용 (프로덕션에서는 제한 필요)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OAuth2 인증
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# 회원가입 엔드포인트
@app.post("/signup")
async def signup(user: UserCreate):
    # 입력 검증
    if len(user.username) != 3:
        raise HTTPException(status_code=400, detail="이름은 3글자여야 합니다.")

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            # 사용자 추가
            hashed_password = hash_password(user.password)
            cursor.execute("""
                INSERT INTO employees (username, password, total_leave, used_leave)
                VALUES (?, ?, 14, 0)
            """, (user.username, hashed_password))

            conn.commit()
            return {"message": f"{user.username}님, 회원가입이 완료되었습니다!"}

        except sqlite3.IntegrityError:
            raise HTTPException(status_code=400, detail="이미 존재하는 이름입니다. 다른 이름을 사용해주세요.")
        except sqlite3.Error as e:
            raise HTTPException(status_code=500, detail=f"데이터베이스 오류: {e}")
        finally:
            conn.close()

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"회원가입 중 오류 발생: {e}")

# 로그인 엔드포인트
@app.post("/login")
async def login(user: UserLogin):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 사용자 정보 조회
        cursor.execute("SELECT password, total_leave, used_leave FROM employees WHERE username=?", (user.username,))
        user_record = cursor.fetchone()

        if user_record:
            stored_password = user_record['password']
            total_leave = user_record['total_leave']
            used_leave = user_record['used_leave']

            # 비밀번호 검증
            if verify_password(stored_password, user.password):
                return {
                    "message": "로그인 성공", 
                    "username": user.username,
                    "total_leave": total_leave,
                    "used_leave": used_leave
                }
            else:
                raise HTTPException(status_code=401, detail="로그인 실패! 비밀번호가 일치하지 않습니다.")
        else:
            raise HTTPException(status_code=404, detail="존재하지 않는 사용자입니다.")

    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"데이터베이스 오류: {e}")
    finally:
        conn.close()

# 휴가 신청 엔드포인트
@app.post("/leave-request")
async def create_leave_request(request: LeaveRequest, username: str):
    # 예상 사용 연차 계산
    result = calculate_working_days(request.start_date, request.end_date, request.leave_type)
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    expected_days = result['days']

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 남은 연차 확인
        cursor.execute("SELECT total_leave, used_leave FROM employees WHERE username=?", (username,))
        user = cursor.fetchone()
        
        remaining_leave = user['total_leave'] - user['used_leave']
        
        if expected_days > remaining_leave:
            raise HTTPException(status_code=400, detail="남은 연차가 부족합니다.")

        try:
            # 휴가 요청 테이블에 저장
            cursor.execute("""
                INSERT INTO leave_requests 
                (username, start_date, end_date, days, leave_type, status)
                VALUES (?, ?, ?, ?, ?, 'PENDING')
            """, (username, request.start_date, request.end_date, 
                  expected_days, request.leave_type))

            # 직원 테이블의 사용 연차 업데이트
            cursor.execute("""
                UPDATE employees
                SET used_leave = used_leave + ?
                WHERE username = ?
            """, (expected_days, username))

            conn.commit()
            return {"message": "✅ 휴가 신청이 완료되었습니다!", "days": expected_days}

        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=500, detail=f"휴가 신청 중 오류 발생: {e}")

    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"데이터베이스 오류: {e}")
    finally:
        conn.close()

# 휴가 신청 내역 조회 엔드포인트
@app.get("/leave-history", response_model=List[LeaveResponse])
async def get_leave_history(username: str):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 현재 사용자의 휴가 신청 내역 조회 (최신 순으로 정렬)
        cursor.execute("""
            SELECT id, username, start_date, end_date, days, leave_type, status
            FROM leave_requests 
            WHERE username = ?
            ORDER BY id DESC
        """, (username,))
        
        leave_history = cursor.fetchall()
        
        return [
            LeaveResponse(
                id=row['id'],
                username=row['username'],
                start_date=row['start_date'],
                end_date=row['end_date'],
                days=row['days'],
                leave_type=row['leave_type'],
                status=row['status']
            ) for row in leave_history
        ]

    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"휴가 신청 내역 조회 중 오류 발생: {e}")
    finally:
        conn.close()

# 사용자 정보 조회 엔드포인트
@app.get("/user-info")
async def get_user_info(username: str):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT total_leave, used_leave 
            FROM employees 
            WHERE username = ?
        """, (username,))
        
        user = cursor.fetchone()
        
        if user:
            return {
                "total_leave": user['total_leave'],
                "used_leave": user['used_leave'],
                "remaining_leave": user['total_leave'] - user['used_leave']
            }
        else:
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"사용자 정보 조회 중 오류 발생: {e}")
    finally:
        conn.close()

# FastAPI 서버 실행 (로컬 개발용)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)