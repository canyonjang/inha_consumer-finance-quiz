import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime, timedelta, timezone

# ---------------------------------------------------------
# 1. 과목 및 설정 (수정 시 이 부분만 확인하세요)
# ---------------------------------------------------------
SUBJECT_NAME = "소비자재무설계 퀴즈"  # 과목 제목
CURRENT_WEEK = "7주차"            # 해당 주차
ADMIN_PASSWORD = "3383"          # 선생님용 비밀번호

# 퀴즈 데이터 (수동으로 제공해주신 7문항 반영)
QUIZ_DATA = [
    {"q": "1. 이슈5의 입장B의 위험 요소 중 하나로, 집값 급등 시 느끼는 상대적 박탈감을 의미하는 표현은 무엇인가?", "a": "벼락거지"},
    {"q": "2. 모건 하우절은, 시장 변동성을 벌금이 아니라, (___________)라고 생각하자라고 제안한다.", "a": "수수료"},
    {"q": "3. 모건 하우절은, 거품이 피해를 주는 것은 (________)투자자들이 자신들과는 다른 게임을 하는 (________)거래자들로부터 신호를 읽기 시작할 때라고 주장한다.", "a": "장기, 단기"},
    {"q": "4. (________________)은 자신의 능력을 과대평가하거나, 자신이 어떤 것을 예측할 때 실수할 확률이 적다고 믿는 성향이다.", "a": "자기과신"},
    {"q": "5. (__________)은 정보 처리 방식과 위험에 대한 태도를 결정짓는 핵심 요소이다.", "a": "성격"},
    {"q": "6. “MBTI에 대해서는, 성격의 (_____________)를 고려하지 않는다는 비판이 있다.", "a": "발달 단계"},
    {"q": "7. 아이젠크의 3요인 모델에 따르면, 외향적인 개인은 (_______) 행위(Herding bias)에 빠질 확률이 적다.", "a": "군집"}
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
