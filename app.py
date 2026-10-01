import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime, timedelta, timezone

# =========================================================
# 1. 과목 및 설정 (매주 이 부분만 수정하세요)
# =========================================================
SUBJECT_NAME = "가계자산 투자설계 퀴즈"   # 화면에 보이는 제목 (자유롭게 수정 가능)
SUBJECT_CODE = "가계자산투자설계"        # DB 저장용 이름 ★한 번 정하면 절대 바꾸지 마세요★
CURRENT_WEEK = "7주차"                  # 매주 여기만 바꾸면 됩니다
ADMIN_PASSWORD = "3383"                 # 교수용 비밀번호

# ---------------------------------------------------------
# 퀴즈 데이터 (7문항)
#   "q" : 학생에게 보이는 문제
#   "a" : 정답 (공백·영문 대소문자는 자동으로 무시됩니다)
#         복수정답을 모두 적어야 하는 문제는 "가치,효용"처럼 쉼표로 구분
# ---------------------------------------------------------
QUIZ_DATA = [
    {"q": "1. 경기 호전 예상 -> 기업 투자 증가(자금차입 증가) -> 자금 수요곡선이 (_______)으로 이동 -> 자금의 초과수요 발생 -> 시장금리 상승", "a": "우측"},
    {"q": "2. 물가 상승 예상 -> 자금 공급 감소(자금 수요 증가) -> 자금 공급곡선이 (_______)으로 이동 -> 시장금리 상승", "a": "좌측"},
    {"q": "3. (_______)물가지수는 계절적인 요인이나 일시적인 공급충격 등으로 가격 변동성이 큰 식료품과 에너지 관련 품목을 제외한 물가지수다.", "a": "근원"},
    {"q": "4. 일정 기간 발생한 국가 간 외환의 유입액에서 유출액을 차감하여 계산한 수지를 (_______)수지라고 한다.", "a": "국제"},
    {"q": "5. 경상수지 흑자 -> 달러화 국내 외환시장 유입(달러화 공급 증가) -> 달러화 가격 (______)", "a": "하락"},
    {"q": "6. BSI와 CSI가 서로 엇갈린 움직임을 보일 경우 경기상황을 판단하는 데 어려움이 있을 수 있다. 이에 따라 한국은행이 가계와 기업의 경제상황에 대한 인식을 종합적으로 평가할 수 있는 이 지수를 발표하고 있다. 무엇인가?", "a": "경제심리지수"},
    {"q": "7. 우리나라 경기순환주기는 평균 (_______)개월이다.", "a": "49"},
]




NUM_QUESTIONS = len(QUIZ_DATA)
# =========================================================


st.set_page_config(page_title=f"{SUBJECT_NAME}", layout="wide")


@st.cache_resource
def init_connection() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)


try:
    supabase = init_connection()
except Exception:
    st.error("수파베이스 연결 설정(Secrets)이 필요합니다.")

if "submitted_on_this_device" not in st.session_state:
    st.session_state.submitted_on_this_device = False

st.title(f"📊 {SUBJECT_NAME}")
st.caption(f"{SUBJECT_CODE} · {CURRENT_WEEK}")

tab1, tab2, tab3 = st.tabs(["✍️ 퀴즈 제출", "🖥️ 제출자 명단 확인", "🔐 성적 분석(교수용)"])


# --- [TAB 1] 학생 제출 화면 ---
with tab1:
    st.header("답안지")

    if st.session_state.submitted_on_this_device:
        st.warning("⚠️ 이 기기에서 제출이 완료되었습니다. 응시는 더 이상 불가능합니다.")
    else:
        with st.form("quiz_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("이름", placeholder="이름")
            with col2:
                student_id = st.text_input("학번", placeholder="학번")

            st.divider()

            user_responses = []
            for i, item in enumerate(QUIZ_DATA):
                st.markdown(f"**{item['q']}**")
                ans = st.text_input(f"{i+1}번 답안", key=f"q{i}")
                user_responses.append(ans)

            submitted = st.form_submit_button("답안 제출하기")

            if submitted:
                if not name or not student_id:
                    st.error("이름과 학번을 입력해 주세요.")
                else:
                    try:
                        # 같은 과목 + 같은 주차 + 같은 학번일 때만 중복으로 처리
                        existing_data = supabase.table("quiz_inha_fin_results").select("*")\
                            .eq("과목", SUBJECT_CODE)\
                            .eq("주차", CURRENT_WEEK)\
                            .eq("학번", student_id).execute()

                        if existing_data.data:
                            st.error(f"❌ {name} 학생은 이미 이번 주 답안을 제출했습니다.")
                        else:
                            kst = timezone(timedelta(hours=9))
                            now_time = datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S")

                            row_dict = {
                                "과목": SUBJECT_CODE,
                                "주차": CURRENT_WEEK,
                                "제출시간": now_time,
                                "이름": name,
                                "학번": student_id
                            }

                            # 채점 (공백 제거 + 영문 소문자 변환 후 비교)
                            total_correct = 0
                            for i, item in enumerate(QUIZ_DATA, 1):
                                s_ans_set = set(item['a'].replace(" ", "").lower().split(","))
                                u_ans_set = set(user_responses[i-1].replace(" ", "").lower().split(","))

                                is_correct = (s_ans_set == u_ans_set)
                                if is_correct:
                                    total_correct += 1

                                row_dict[f"q{i}_답"] = user_responses[i-1]
                                row_dict[f"q{i}_결과"] = "O" if is_correct else "X"

                            row_dict["총점"] = total_correct

                            supabase.table("quiz_inha_fin_results").insert(row_dict).execute()

                            st.session_state.submitted_on_this_device = True
                            st.success(f"{name} 학생, 제출 성공! ({total_correct}/{NUM_QUESTIONS})")
                            st.rerun()

                    except Exception:
                        # 과부하/에러 시 학생 화면이 멈추지 않도록 처리
                        pass


# --- [TAB 2] 제출 명단 확인 ---
with tab2:
    st.subheader(f"📍 {SUBJECT_CODE} {CURRENT_WEEK} 제출 완료 명단")
    st.info("명단을 확인하려면 아래 버튼을 누르세요.")

    if st.button("🔄 명단 확인/새로고침"):
        try:
            response = supabase.table("quiz_inha_fin_results").select("*")\
                .eq("과목", SUBJECT_CODE)\
                .eq("주차", CURRENT_WEEK).execute()
            today_list = pd.DataFrame(response.data)

            if not today_list.empty:
                st.write(f"현재 총 {len(today_list)}명 제출 완료")
                cols = st.columns(6)
                for i, row in enumerate(today_list.itertuples()):
                    cols[i % 6].success(f"✅ {row.이름}")
            else:
                st.write("아직 제출자가 없습니다.")
        except Exception:
            st.error("데이터 로드 실패")


# --- [TAB 3] 성적 분석 ---
with tab3:
    st.header("🔐 관리자 인증")
    admin_pw = st.text_input("비밀번호를 입력하세요", type="password")

    if admin_pw == ADMIN_PASSWORD:
        st.success("인증 성공")
        try:
            # 이 과목 데이터만 불러옵니다 (다른 과목과 섞이지 않음)
            response = supabase.table("quiz_inha_fin_results").select("*")\
                .eq("과목", SUBJECT_CODE).execute()
            data = pd.DataFrame(response.data)

            if not data.empty:
                st.subheader("학생별 평균 정답률 (전체 주차)")
                stats = data.groupby(['학번', '이름'])['총점'].mean().reset_index()
                stats['정답률(%)'] = (stats['총점'] / NUM_QUESTIONS * 100).round(1)
                st.dataframe(stats.sort_values(by='총점', ascending=False), use_container_width=True)

                st.divider()

                st.subheader("주차별 응시 현황")
                by_week = data.groupby('주차').agg(
                    응시인원=('학번', 'count'),
                    평균점수=('총점', 'mean')
                ).round(1).reset_index()
                st.dataframe(by_week, use_container_width=True)

                st.divider()

                st.download_button(
                    "엑셀 데이터 다운로드",
                    data=data.to_csv(index=False).encode('utf-8-sig'),
                    file_name=f"{SUBJECT_CODE}_결과.csv",
                    mime="text/csv"
                )
            else:
                st.info("데이터가 없습니다.")
        except Exception:
            st.error("데이터 로드 실패")
    elif admin_pw != "":
        st.error("비밀번호 불일치")
