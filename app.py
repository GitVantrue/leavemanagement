import streamlit as st
import sqlite3
import random
import pandas as pd
from datetime import datetime
import hashlib

# 페이지 설정을 스크립트 최상단에 위치
st.set_page_config(page_title="연차 관리 시스템", page_icon="🏖️", layout="wide")

# 포켓몬 이모지 딕셔너리 (로그인한 사용자 옆에 보여줄 이모지)
POKEMON_EMOJIS = {
    "이상해": "🌱", "피카츄": "⚡", "파이리": "🔥", "꼬부기": "💧",
    "버터플": "🦋", "야도란": "🤖", "피존투": "🐦", "또가스": "💨",
    "식스테": "🐟", "팬텀": "👻"
}

# 상태 변환 딕셔너리
STATUS_DICT = {
    'PENDING': '수락 대기중',
    'APPROVED': '승인됨',
    'REJECTED': '반려됨'
}

# 비밀번호 해시 함수
def hash_password(password, salt=None):
    if salt is None:
        salt = str(random.randint(1000, 9999))
    
    salted_password = f"{salt}{password}"
    hashed = hashlib.sha256(salted_password.encode()).hexdigest()
    
    return f"{salt}${hashed}"

# 비밀번호 검증 함수
def verify_password(stored_password, provided_password):
    try:
        salt, hashed = stored_password.split('$')
        new_hash = hashlib.sha256(f"{salt}{provided_password}".encode()).hexdigest()
        return new_hash == hashed
    except:
        return False

# 데이터베이스 초기화 함수
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
            used_leave INTEGER DEFAULT 0
        )
        """)

        # 휴가 신청 테이블 생성
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS leave_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            request_date DATE NOT NULL,
            days INTEGER NOT NULL,
            status TEXT DEFAULT 'PENDING'
        )
        """)

        conn.commit()
        conn.close()
    except Exception as e:
        st.error(f"데이터베이스 초기화 중 오류 발생: {e}")

# 회원가입 페이지 함수
def signup_page():
    st.title("🌟 연차 관리 시스템 회원가입")

    with st.form(key="signup_form", clear_on_submit=True):
        new_username = st.text_input("👤 이름 (포켓몬 3글자)", key="signup_username")
        new_password = st.text_input("🔐 비밀번호", type="password", key="signup_password")
        confirm_password = st.text_input("🔐 비밀번호 확인", type="password", key="signup_confirm_password")

        submit_button = st.form_submit_button("회원가입")

        if submit_button:
            # 입력 검증
            if not new_username or not new_password:
                st.error("이름과 비밀번호를 모두 입력해주세요.")
                return

            if len(new_username) != 3:
                st.error("이름은 3글자여야 합니다.")
                return

            if new_password != confirm_password:
                st.error("비밀번호가 일치하지 않습니다.")
                return

            try:
                conn = sqlite3.connect("leave_management.db")
                cursor = conn.cursor()

                try:
                    # 사용자 추가
                    hashed_password = hash_password(new_password)
                    cursor.execute("""
                        INSERT INTO employees (username, password, total_leave, used_leave)
                        VALUES (?, ?, 14, 0)
                    """, (new_username, hashed_password))

                    conn.commit()
                    st.success(f"{new_username}님, 회원가입이 완료되었습니다!")
                    st.session_state['current_page'] = 'login'
                    st.experimental_rerun()

                except sqlite3.IntegrityError:
                    st.error("이미 존재하는 이름입니다. 다른 이름을 사용해주세요.")
                except sqlite3.Error as e:
                    st.error(f"데이터베이스 오류: {e}")
                finally:
                    conn.close()

            except Exception as e:
                st.error(f"회원가입 중 오류 발생: {e}")

# 로그인 함수
def login_page():
    st.title("🔑 연차 관리 시스템 로그인")

    with st.form(key="login_form"):
        username = st.text_input("👤 ID (포켓몬 3글자)")
        password = st.text_input("🔐 비밀번호", type="password")

        login_button = st.form_submit_button("로그인")
        signup_link = st.form_submit_button("회원가입")

        if signup_link:
            st.session_state['current_page'] = 'signup'
            st.experimental_rerun()

        if login_button:
            try:
                conn = sqlite3.connect("leave_management.db")
                cursor = conn.cursor()

                # 사용자 정보 조회
                cursor.execute("SELECT password, total_leave, used_leave FROM employees WHERE username=?", (username,))
                user = cursor.fetchone()

                if user:
                    stored_password, total_leave, used_leave = user

                    # 비밀번호 검증
                    if verify_password(stored_password, password):
                        st.session_state['logged_in'] = True
                        st.session_state['username'] = username
                        st.session_state['total_leave'] = total_leave
                        st.session_state['used_leave'] = used_leave
                        st.experimental_rerun()
                    else:
                        st.error("로그인 실패! 비밀번호가 일치하지 않습니다.")
                else:
                    st.error("존재하지 않는 사용자입니다.")

            except sqlite3.Error as e:
                st.error(f"데이터베이스 오류: {e}")
            finally:
                conn.close()

# 메인 페이지 함수
def main_page():
    # 상단에 사용자 정보와 포켓몬 이모지 표시
    emoji = POKEMON_EMOJIS.get(st.session_state['username'], "🧑")
    st.title(f"{emoji} {st.session_state['username']}님의 연차 관리")

    # 개인 연차 정보 표시
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("총 연차", f"{st.session_state['total_leave']}일", delta_color="off")

    with col2:
        st.metric("사용한 연차", f"{st.session_state['used_leave']}일", delta_color="off")

    with col3:
        remaining_leave = st.session_state['total_leave'] - st.session_state['used_leave']
        st.metric("남은 연차", f"{remaining_leave}일",
                  delta=f"{remaining_leave}일" if remaining_leave > 0 else "연차 소진",
                  delta_color="normal")

    st.divider()

    # 휴가 신청 섹션
    st.header("✍️ 휴가 신청")

    with st.form("leave_request_form"):
        leave_date = st.date_input("📅 휴가 날짜 선택")
        remaining_leave = st.session_state['total_leave'] - st.session_state['used_leave']
        leave_days = st.number_input("🕒 신청할 연차 일수",
                                     min_value=1,
                                     max_value=remaining_leave,
                                     step=1)

        submit_leave = st.form_submit_button("휴가 신청하기")

        if submit_leave:
            conn = sqlite3.connect("leave_management.db")
            cursor = conn.cursor()

            try:
                # 휴가 요청 테이블에 저장
                cursor.execute("""
                    INSERT INTO leave_requests (username, request_date, days)
                    VALUES (?, ?, ?)
                """, (st.session_state['username'], leave_date, leave_days))

                # 직원 테이블의 사용 연차 업데이트
                cursor.execute("""
                    UPDATE employees
                    SET used_leave = used_leave + ?
                    WHERE username = ?
                """, (leave_days, st.session_state['username']))

                conn.commit()
                st.success("✅ 휴가 신청이 완료되었습니다!")

                # 세션 상태 업데이트
                st.session_state['used_leave'] += leave_days
                st.experimental_rerun()

            except Exception as e:
                st.error(f"휴가 신청 중 오류 발생: {e}")

            finally:
                conn.close()

    # 휴가 신청 내역 표시
    st.header("📋 휴가 신청 내역")
    conn = sqlite3.connect("leave_management.db")
    cursor = conn.cursor()

    cursor.execute("SELECT request_date, days, status FROM leave_requests WHERE username = ?", (st.session_state['username'],))
    leave_history = cursor.fetchall()
    conn.close()

    if leave_history:
        # 데이터프레임 생성 및 상태 변환
        history_df = pd.DataFrame(leave_history, columns=['날짜', '일수', '상태'])
        history_df['상태'] = history_df['상태'].map(STATUS_DICT)
        
        # 남은 연차 계산 추가
        total_leave = st.session_state['total_leave']
        used_leave = st.session_state['used_leave']
        history_df['신청 후 남은 연차'] = total_leave - used_leave

        st.dataframe(history_df, use_container_width=True)
    else:
        st.write("아직 신청한 휴가가 없습니다.")

# 메인 앱 로직
def main():
    # 데이터베이스 초기화
    init_database()

    # 세션 상태 초기화
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False

    if 'current_page' not in st.session_state:
        st.session_state['current_page'] = 'login'

    # 페이지 전환 로직
    if not st.session_state['logged_in']:
        if st.session_state['current_page'] == 'login':
            login_page()
        elif st.session_state['current_page'] == 'signup':
            signup_page()
    else:
        main_page()

        # 로그아웃 버튼
        if st.sidebar.button("🚪 로그아웃"):
            st.session_state['logged_in'] = False
            st.session_state['current_page'] = 'login'
            st.experimental_rerun()

# 앱 실행
if __name__ == "__main__":
    main()
