import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta, timezone

# ---------------------------------------------------------
# 1. 과목 및 설정 (수정 시 이 부분만 확인하세요)
# ---------------------------------------------------------
SUBJECT_NAME = "소비자재무설계 퀴즈"  # 과목 제목
CURRENT_WEEK = "5주차"           # 해당 주차
ADMIN_PASSWORD = "3383"          # 선생님용 비밀번호

# 퀴즈 데이터 (수동으로 제공해주신 7문항 반영)
QUIZ_DATA = [
    {"q": "1. 이슈3의 입장A에서 평범한 사람이 부자가 되는 유일한 길로 꼽으며, 성실하게 모은 목돈을 안전한 자산에 묻어두고 기다려야 한다고 강조하는 것은 무엇인가?", "a": "복리"},
    {"q": "2. 나와 가족의 인생에서 목돈이 필요한 중요 이벤트가 몇 살에 생길지를 미리 예상해 보기 위한 표는?", "a": "생애설계연표"},
    {"q": "3. 현재 가지고 있는 자산 부채의 종류와 규모를 파악하기 위한 표는?", "a": "자산부채 상태표"},
    {"q": "4. 매월 평균적인 수입과 지출 상황을 파악하는 표는?", "a": "현금흐름표"},
    {"q": "5. 총소득에서 총지출이 차지하는 비율을 알려주는 지표는?", "a": "가계수지지표"},
    {"q": "6. “미국의 한 연구에 따르면, 유동성 비율과 (______________)이 높을수록, 부채비율이 낮을수록 재무적 웰빙 수준이 높아진다.", "a": "투자비율"},
    {"q": "7. 사회초년생 필수 계좌 3가지는 CMA, (________), 연금저축 등이다.", "a": "ISA"}
]

NUM_QUESTIONS = len(QUIZ_DATA) 
# ---------------------------------------------------------

# 페이지 설정
st.set_page_config(page_title=f"{SUBJECT_NAME}", layout="wide")

# 구글 시트 연결
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except:
    st.error("구글 시트 연결 설정(Secrets)이 필요합니다.")

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
                        # 제출 시 중복 확인을 위해 실시간 데이터 읽기
                        master_df = conn.read(worksheet="전체데이터", ttl=0)
                        
                        already_exists = master_df[
                            (master_df['주차'] == CURRENT_WEEK) & 
                            (master_df['학번'] == student_id)
                        ]

                        if not already_exists.empty:
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
                            
                            # 데이터 업데이트
                            updated_master = pd.concat([master_df, pd.DataFrame([row_dict])], ignore_index=True)
                            conn.update(worksheet="전체데이터", data=updated_master)
                            
                            st.session_state.submitted_on_this_device = True
                            st.success(f"{name} 학생, 제출 성공! ({total_correct}/{NUM_QUESTIONS})")
                            # st.balloons() # 트래픽 최적화를 위해 애니메이션 주석 처리 권장
                            st.rerun() 
                            
                    except Exception as e:
                        # 과부하 시 pass 처리하여 사용자 불편 최소화
                        pass

# --- [TAB 2] 제출 명단 확인 (트래픽 최적화 적용) ---
with tab2:
    st.subheader(f"📍 {CURRENT_WEEK} 제출 완료 명단")
    st.info("명단을 확인하려면 아래 버튼을 누르세요.")
    
    if st.button("🔄 명단 확인/새로고침"):
        try:
            # 트래픽 부하 감소를 위해 5분 캐시(ttl=300) 적용
            data = conn.read(worksheet="전체데이터", ttl=300)
            today_list = data[data['주차'] == CURRENT_WEEK]
            
            if not today_list.empty:
                st.write(f"현재 총 {len(today_list)}명 제출 완료")
                cols = st.columns(6)
                for i, row in enumerate(today_list.itertuples()):
                    cols[i % 6].success(f"✅ {row.이름}")
            else:
                st.write("아직 제출자가 없습니다.")
        except:
            st.error("데이터 로드 실패")

# --- [TAB 3] 성적 분석 ---
with tab3:
    st.header("🔐 관리자 인증")
    admin_pw = st.text_input("비밀번호를 입력하세요", type="password")
    
    if admin_pw == ADMIN_PASSWORD:
        st.success("인증 성공")
        try:
            # 관리자용 데이터는 실시간 로드
            data = conn.read(worksheet="전체데이터", ttl=0)
            if not data.empty:
                st.subheader("학생별 평균 정답률")
                stats = data.groupby(['학번', '이름'])['총점'].mean().reset_index()
                stats['정답률(%)'] = (stats['총점'] / NUM_QUESTIONS * 100).round(1)
                st.dataframe(stats, use_container_width=True)
                st.divider()
                st.download_button("엑셀 데이터 다운로드", data=data.to_csv(index=False).encode('utf-8-sig'), file_name=f"{SUBJECT_NAME}_결과.csv", mime="text/csv")
            else:
                st.info("데이터가 없습니다.")
        except:
            st.error("데이터 로드 실패")
    elif admin_pw != "":
        st.error("비밀번호 불일치")

