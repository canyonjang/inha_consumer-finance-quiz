import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime, timedelta, timezone

# ---------------------------------------------------------
# 1. 과목 및 설정 (수정 시 이 부분만 확인하세요)
# ---------------------------------------------------------
SUBJECT_NAME = "소비자재무설계 퀴즈"  # 과목 제목
CURRENT_WEEK = "10주차"            # 해당 주차
ADMIN_PASSWORD = "3383"          # 선생님용 비밀번호

# 퀴즈 데이터 (수동으로 제공해주신 7문항 반영)
QUIZ_DATA = [
    {"q": "1. (________)은, 머릿속 상상이나 논리적인 추론에만 그치는 것이 아니라, 실제로 우리의 감각기관(눈, 코, 귀 등)을 통해 관찰하거나 도구로 측정이 가능한 것이다.", "a": "경험"},
    {"q": "2. 상식은 진짜 진실이 아닌 거짓 믿음일 수도 있어서 문제이다. 그래서 상식에 대해 항상 (__________) 사고하기가 필요하다.", "a": "비판적"},
    {"q": "3. 질적인 성격을 가진 연구대상을 수치화하여 관찰 및 측정이 가능하도록 만드는 것이 (_______)이다.", "a": "양화"},
    {"q": "4. 과학적 연구의 궁극적 목적은 연구대상인 현상이 일어나게 된 원인을 규명하는 것이다. 즉 (______________) 관계를 밝히는 것이 최종 목적이다.", "a": "인과적"},
    {"q": "5. 소비자 재무설계(사회과학)에서는 특정 조건 하에서 특정 현상이 발생할 개연성 또는 발생할 확률이 높다는 (__________) 법칙성을 밝히고자 한다.", "a": "경향적"},
    {"q": "6. (______________)은 어떤 하나의 현상이 발생하면 다른 현상도 발생하고, 하나의 현상이 변화했을 때 다른 현상도 함께 변화하는 관계를 말한다.", "a": "상관성"},
    {"q": "7. 제3의 요인에 의해서 설명될 수 있는 두 현상 간의 관계는 (_______________)이다.", "a": "허위관계"}
]

NUM_QUESTIONS = len(QUIZ_DATA) 
# ---------------------------------------------------------

# 페이지 설정
st.set_page_config(page_title=f"{SUBJECT_NAME}", layout="wide")

# Supabase 연결 설정
@st.cache_resource
def init_connection() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

try:
    supabase = init_connection()
except Exception as e:
    st.error("수파베이스 연결 설정(Secrets)이 필요합니다.")

if "submitted_on_this_device" not in st.session_state:
    st.session_state.submitted_on_this_device = False

st.title(f"📊 {SUBJECT_NAME}")

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
                        # 제출 시 중복 확인을 위해 수파베이스 데이터 조회
                        existing_data = supabase.table("quiz_inha_fin_results").select("*").eq("주차", CURRENT_WEEK).eq("학번", student_id).execute()

                        if existing_data.data: # 데이터가 존재하면
                            st.error(f"❌ {name} 학생은 이미 이번 주 답안을 제출했습니다.")
                        else:
                            kst = timezone(timedelta(hours=9))
                            now_time = datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S")
                            
                            row_dict = {
                                "주차": CURRENT_WEEK,
                                "제출시간": now_time,
                                "이름": name,
                                "학번": student_id
                            }
                            
                            # 채점 로직 (영어 대소문자 무시 적용)
                            total_correct = 0
                            for i, item in enumerate(QUIZ_DATA, 1):
                                # 양측 답안 모두 공백 제거 및 소문자 변환 후 비교
                                s_ans_set = set(item['a'].replace(" ", "").lower().split(","))
                                u_ans_set = set(user_responses[i-1].replace(" ", "").lower().split(","))
                                
                                is_correct = (s_ans_set == u_ans_set)
                                if is_correct: total_correct += 1
                                
                                row_dict[f"q{i}_답"] = user_responses[i-1]
                                row_dict[f"q{i}_결과"] = "O" if is_correct else "X"
                            
                            row_dict["총점"] = total_correct
                            
                            # 수파베이스에 데이터 Insert
                            supabase.table("quiz_inha_fin_results").insert(row_dict).execute()
                            
                            st.session_state.submitted_on_this_device = True
                            st.success(f"{name} 학생, 제출 성공! ({total_correct}/{NUM_QUESTIONS})")
                            # st.balloons() # 트래픽 최적화를 위해 애니메이션 주석 처리 권장
                            st.rerun() 
                            
                    except Exception as e:
                        # 과부하/에러 시 pass 처리하여 사용자 불편 최소화
                        pass

# --- [TAB 2] 제출 명단 확인 ---
with tab2:
    st.subheader(f"📍 {CURRENT_WEEK} 제출 완료 명단")
    st.info("명단을 확인하려면 아래 버튼을 누르세요.")
    
    if st.button("🔄 명단 확인/새로고침"):
        try:
            # 수파베이스에서 이번 주차 데이터만 바로 로드 (수파베이스는 응답이 매우 빨라 캐싱 없이도 원활함)
            response = supabase.table("quiz_inha_fin_results").select("*").eq("주차", CURRENT_WEEK).execute()
            today_list = pd.DataFrame(response.data)
            
            if not today_list.empty:
                st.write(f"현재 총 {len(today_list)}명 제출 완료")
                cols = st.columns(6)
                for i, row in enumerate(today_list.itertuples()):
                    cols[i % 6].success(f"✅ {row.이름}")
            else:
                st.write("아직 제출자가 없습니다.")
        except Exception as e:
            st.error("데이터 로드 실패")

# --- [TAB 3] 성적 분석 ---
with tab3:
    st.header("🔐 관리자 인증")
    admin_pw = st.text_input("비밀번호를 입력하세요", type="password")
    
    if admin_pw == ADMIN_PASSWORD:
        st.success("인증 성공")
        try:
            # 관리자용 데이터 로드
            response = supabase.table("quiz_inha_fin_results").select("*").execute()
            data = pd.DataFrame(response.data)
            
            if not data.empty:
                st.subheader("학생별 평균 정답률")
                stats = data.groupby(['학번', '이름'])['총점'].mean().reset_index()
                stats['정답률(%)'] = (stats['총점'] / NUM_QUESTIONS * 100).round(1)
                st.dataframe(stats, use_container_width=True)
                st.divider()
                st.download_button("엑셀 데이터 다운로드", data=data.to_csv(index=False).encode('utf-8-sig'), file_name=f"{SUBJECT_NAME}_결과.csv", mime="text/csv")
            else:
                st.info("데이터가 없습니다.")
        except Exception as e:
            st.error("데이터 로드 실패")
    elif admin_pw != "":
        st.error("비밀번호 불일치")
