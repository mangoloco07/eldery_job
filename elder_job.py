import streamlit as st
import pandas as pd
import json
import uuid
import time
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore

# 페이지 설정
st.set_page_config(page_title="노인 일자리 매칭 도움 AI", page_icon="👵👴", layout="wide")

# Firestore 연동
if not firebase_admin._apps:
    cred_dict = dict(st.secrets["firebase"])
    cred_dict["private_key"] = cred_dict["private_key"].replace("\\n", "\n")
    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred)

db = firestore.client()

# Groq API 연동
st.sidebar.title("🔑 API 설정")
if "GROQ_API_KEY" in st.secrets and st.secrets["GROQ_API_KEY"]:
    groq_api_key = st.secrets["GROQ_API_KEY"]
    st.sidebar.success("✅ AI 엔진(Groq) 연결됨")
else:
    groq_api_key = st.sidebar.text_input(
        "Groq API Key 입력",
        type="password",
        help="console.groq.com에서 발급받은 API 키(gsk_...)를 입력하세요."
    )

def get_groq_client(api_key):
    if not api_key:
        return None
    return Groq(api_key=api_key.strip())

# 2026 사업분류코드 및 기본 채용 조건
LITERACY_CODES = {"B-02", "B-09", "B-12"}
WALKING_CODES = {"A-02", "A-13", "A-16", "A-18", "A-08", "B-08", "E-13", "E-14", "E-15"}
HOURS_CODES = {f"E-0{i}" if i < 10 else f"E-{i}" for i in range(1, 13)}

RAW_BUSINESS_DATA = [
    ("A-01", "공익활동", "노노케어(정서지원)", "취약노인 가구를 방문하여 안부확인 및 말벗, 정서관리 등 수행"),
    ("A-02", "공익활동", "노노케어(활동지원)", "취약노인 가구를 방문하여 수혜노인 활동 지원 및 일상동행, 생활실태 점검 등 수행"),
    ("A-03", "공익활동", "장애인봉사", "지역 내 장애인 가정 및 장애인 보호시설, 학교 내 특수학급 등 지원"),
    ("A-04", "공익활동", "취약가정봉사", "지역 내 다문화가정 및 한부모 가족 상담, 정서지원, 아동보호 서비스 제공"),
    ("A-05", "공익활동", "청소년 선도 봉사", "청소년 비행우발지역 선도 및 상담지원"),
    ("A-06", "공익활동", "생활시설 이용자 지원 봉사", "재가복지시설, 장애인 및 아동생활시설 등 취약계층 이용자 지원"),
    ("A-07", "공익활동", "학교급식 지원봉사", "학생 대상 급식 및 식사예절 지도 등 지원"),
    ("A-08", "공익활동", "스쿨존 교통지원 봉사", "유치원/학교 주변 교통정리, 교통안전 캠페인 및 어린이 안심 등하교 지원"),
    ("A-09", "공익활동", "CCTV상시관제", "학교 내·외부 CCTV 모니터링 후 문제 발생 시 구두보고 및 조치 요청"),
    ("A-10", "공익활동", "보육시설봉사", "보육교사 보조, 생활지도 및 강의 등 지원"),
    ("A-11", "공익활동", "지역아동센터봉사", "지역아동센터 아동의 방과후 교육, 귀가 및 급식 등 지원"),
    ("A-12", "공익활동", "도서관봉사", "국·공립 및 초·중·고등학교 도서관 관리지원"),
    ("A-13", "공익활동", "공원·놀이터 지원봉사", "공원, 놀이터 등 야외 공공시설 관리지원"),
    ("A-14", "공익활동", "문화재 시설 봉사", "지역 문화재 보호, 훼손방지 및 관람편의 제공 지원"),
    ("A-15", "공익활동", "공공업무 및 복지시설 지원봉사", "보건소, 복지기관, 경로당, 유기동물 보호센터 매니저, 위생지원단 등 지원"),
    ("A-16", "공익활동", "지역사회 환경개선 봉사", "지역 내 주거환경 및 생태환경 정화 업무"),
    ("A-17", "공익활동", "자원순환 및 재활용 지원봉사", "아이스팩/커피찌꺼기/종이팩/플라스틱/폐건전지/폐의약품 수거 및 자원순환 봉사"),
    ("A-18", "공익활동", "교통 지원 봉사", "주차 혼잡지역 질서유지 및 계도, 전기차 충전소 관리원 등"),
    ("A-19", "공익활동", "지역사회안전망 구축 지원", "지역사회 방역활동, 안전 위해 요소 점검(지하철, 파손도로) 등"),
    ("A-20", "공익활동", "기타 공공서비스", "기타 분류 안 된 공공서비스 활동"),
    ("A-21", "공익활동", "건강 체조 취미생활 지도", "체육(건강) 및 각종 취미관련 경륜전수 활동"),
    ("A-22", "공익활동", "문화공연 활동", "복지소외지역 또는 각종 생활시설 등 대상 문화 제공활동"),
    ("A-23", "공익활동", "체험 활동 지원", "지역 내 숲 체험 및 문화체험 해설지원 등"),
    ("A-24", "공익활동", "경륜전수 활동", "유아 및 초·중학생 대상 경륜전수 활동"),
    ("A-29", "공익활동", "경로당 배식 지원", "경로당 내 배식 등 지원"),

    ("B-01", "역량활용", "보육시설 운영지원", "어린이집 운영지원"),
    ("B-02", "역량활용", "교육시설 운영지원", "유치원, 초·중·고등학교, 대학, 평생교육시설 등 운영지원"),
    ("B-03", "역량활용", "돌봄·양육·생활시설 운영지원", "공동육아나눔터, 다함께돌봄센터, 지역아동센터, 보육원, 건강가정지원센터 등 운영지원"),
    ("B-04", "역량활용", "노인시설 운영지원", "노인복지시설, 재가노인복지시설, 치매안심센터 등 운영 및 노인맞춤돌봄서비스 지원"),
    ("B-05", "역량활용", "장애인시설 운영지원", "장애인 거주시설, 자립생활지원시설, 직업재활시설 등 운영지원"),
    ("B-06", "역량활용", "국가·지자체·공공단체 시설 운영지원", "행정복지센터, 의료시설, 치안시설, 우체국, 소방서 등 운영지원"),
    ("B-07", "역량활용", "지역 시설·기관 운영지원", "지역 내 사회적경제조직, 수요처 운영지원 및 복지 서비스 제공"),
    ("B-08", "역량활용", "안전관리 지원", "디지털 교통안전 도우미, 바다안전순찰대, 승강기안전단, 치안지킴이 등 안전점검"),
    ("B-09", "역량활용", "보건관리 지원", "건강의료서비스매니저, 디지털 헬스케어 매니저, 자살예방 상담원 등 보건증진 지원"),
    ("B-10", "역량활용", "환경보존 지원", "나눔자원관리, 산림자원보존사업단, 생태도슨트 등 환경보존 활동"),
    ("B-11", "역량활용", "돌봄 지원", "고독사예방게이트키퍼, 발달장애인 활동매니저, 온동네 초등돌봄(늘봄학교), 응급안전 지킴이 등"),
    ("B-12", "역량활용", "국민편의 지원", "다문화 정착지원, 공항서포터즈, 금융업무지원, 연금가이드, 점자 도우미 등 서비스 안내"),

    ("E-01", "공동체사업단", "식품제조-간식류", "식재료를 활용하여 간식류 식품 제조 및 판매"),
    ("E-02", "공동체사업단", "식품제조-참기름 및 장류", "참기름, 장류 등 식품 제조 및 판매"),
    ("E-03", "공동체사업단", "식품제조-도시락 및 반찬류", "도시락 및 반찬류 식품 제조 및 판매"),
    ("E-04", "공동체사업단", "식품제조-기타", "기타 식품 제조 및 판매"),
    ("E-05", "공동체사업단", "공산품제작-비누류", "규격에 맞춘 비누류 공산품 제작 및 판매"),
    ("E-06", "공동체사업단", "공산품제작-봉제제품", "봉제제품 제작 및 판매"),
    ("E-07", "공동체사업단", "매장운영-카페", "소규모 실버 카페 매장 운영"),
    ("E-08", "공동체사업단", "매장운영-음식점", "소규모 음식점 매장 운영"),
    ("E-09", "공동체사업단", "매장운영-매점(편의점)", "소규모 매점 및 편의점 운영"),
    ("E-10", "공동체사업단", "매장운영-기타", "기타 소규모 매장 및 점포 운영"),
    ("E-11", "공동체사업단", "지역영농", "유·휴경지를 활용하여 콩, 고사리 등 농산물 공동 경작 및 판매"),
    ("E-12", "공동체사업단", "기타 공산품제조/서비스", "사업 수익을 통해 재화 및 기타 서비스 제공"),
    ("E-13", "공동체사업단", "운송-아파트 택배", "아파트 단지 내 택배 물품 배송 및 집하"),
    ("E-14", "공동체사업단", "운송-지하철 택배", "지하철을 이용하여 각종 수하물 및 서류 배달"),
    ("E-15", "공동체사업단", "운송-기타", "기타 물품 운송 및 배달 서비스"),
    ("E-16", "공동체사업단", "이미용 서비스", "이미용 서비스 제공"),
    ("E-17", "공동체사업단", "세차 서비스", "차량 세차 서비스 제공"),
    ("E-18", "공동체사업단", "세탁 서비스", "세탁 서비스 제공"),
    ("E-19", "공동체사업단", "기타 서비스", "기타 공동체사업단 서비스 제공")
]

BUSINESS_CODES = {}
for code, category, name, desc in RAW_BUSINESS_DATA:
    BUSINESS_CODES[code] = {
        "category": category,
        "name": name,
        "desc": desc,
        "req_walking": code in WALKING_CODES,
        "req_literacy": code in LITERACY_CODES,
        "is_hours": code in HOURS_CODES
    }

# 4. 세션 초기화
# 4. 세션 초기화
INITIAL_CHAT = [
    {"role": "assistant", "content": "안녕하세요, 어르신! 반갑습니다. 프로필 작성을 도와드릴 도우미입니다. 먼저, 현재 어느 지역(시/군/구)에 살고 계신가요?"}
]
if "chat_history" not in st.session_state:
    st.session_state.chat_history = list(INITIAL_CHAT)

if "user_id" not in st.session_state:
    st.session_state.user_id = f"senior_{str(uuid.uuid4())[:8]}"

# Firebase 읽기/쓰기/삭제 함수
def get_jobs_from_firestore():
    docs = db.collection("db1_jobs").stream()
    jobs = []
    for doc in docs:
        d = doc.to_dict()
        d["id"] = doc.id
        jobs.append(d)
    return sorted(jobs, key=lambda x: x.get("id", ""))

def save_job_to_firestore(job_data):
    doc_ref = db.collection("db1_jobs").document(job_data["id"])
    doc_ref.set(job_data)

def delete_job_from_firestore(job_id):
    db.collection("db1_jobs").document(job_id).delete()
    db.collection("db2_preferences").document(job_id).delete()

def save_senior_profile_to_firestore(profile_data):
    doc_ref = db.collection("db2_seniors").document(st.session_state.user_id)
    doc_ref.set(profile_data)

def get_senior_profile_from_firestore():
    doc = db.collection("db2_seniors").document(st.session_state.user_id).get()
    return doc.to_dict() if doc.exists else None

def delete_senior_profile_from_firestore():
    db.collection("db2_seniors").document(st.session_state.user_id).delete()

def increment_b_index_in_firestore(job_id):
    pref_ref = db.collection("db2_preferences").document(job_id)
    doc = pref_ref.get()
    if doc.exists:
        pref_ref.update({"select_count": firestore.Increment(1)})
    else:
        pref_ref.set({"select_count": 1})

def get_preferences_from_firestore():
    docs = db.collection("db2_preferences").stream()
    return {doc.id: doc.to_dict() for doc in docs}

# Groq API 호출 헬퍼
# Groq API 호출 헬퍼
def call_groq_safe(client, messages, temperature=0.7, json_mode=False):
    priority_models = [
        "openai/gpt-oss-120b",
        "qwen/qwen3.8-27b",
        "openai/gpt-oss-20b",
    ]
    exclude_keywords = ("whisper", "guard", "safeguard", "orpheus", "tts")

    try:
        available = [
            m.id for m in client.models.list().data
            if not any(k in m.id.lower() for k in exclude_keywords)
        ]
    except Exception:
        available = []

    models = [m for m in priority_models if not available or m in available]
    for m in available:
        if m not in models:
            models.append(m)
    if not models:
        models = priority_models

    last_error = None
    for model_name in models:
        for attempt in range(2):
            try:
                kwargs = {
                    "model": model_name,
                    "messages": messages,
                    "temperature": temperature,
                }
                if json_mode:
                    kwargs["response_format"] = {"type": "json_object"}
                response = client.chat.completions.create(**kwargs)
                return response.choices[0].message.content
            except Exception as e:
                last_error = e
                err_str = str(e)
                if "429" in err_str or "503" in err_str:
                    time.sleep(1.5)
                    continue
                break
    raise last_error
    
# 기타 채용 조건 일치도 점수 계산 (Groq)
def calculate_a_index_with_llm(client, senior_exps, job_extras):
    exact_matched = list(set(job_extras).intersection(set(senior_exps)))

    if not job_extras:
        return 50.0, ["기본 일치"]
    if not senior_exps:
        return 50.0, ["미입력"]

    if not client:
        score = min(50 + len(exact_matched) * 25, 100)
        return float(score), exact_matched if exact_matched else ["기본 일치"]

    try:
        prompt = (
            "당신은 노인일자리 직무-역량 매칭 전문가입니다.\n"
            "구직자의 과거 경력 및 자격 목록과 채용 우대 조건(기타 채용 조건) 목록을 비교하여 의미적 연관성을 평가해 주세요.\n\n"
            f"구직자 경력 및 자격: {json.dumps(senior_exps, ensure_ascii=False)}\n"
            f"채용 우대조건: {json.dumps(job_extras, ensure_ascii=False)}\n\n"
            "평가 규칙:\n"
            "1. 단순 단어 일치뿐만 아니라 의미가 통하는 유의어/연관역량(예: '요리'↔'조리', '택배'↔'배송')도 매칭으로 인정합니다.\n"
            "2. 기본 점수는 50점입니다. 일치하거나 연관성이 인정된 항목 수에 따라 50점~100점 사이로 점수를 산출하세요.\n"
            "3. 일치 및 연관 인정된 역량을 텍스트 리스트로 정리하세요. (예: ['요리 ↔ 조리 (연관 인정)', '택배 (일치)'])\n\n"
            "반드시 JSON 포맷으로 응답하세요:\n"
            '{"score": 85, "matched_reasons": ["요리 ↔ 조리 (연관 인정)"]}'
        )

        raw_text = call_groq_safe(
            client,
            messages=[
                {"role": "system", "content": "You are an HR matching expert that outputs strictly valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
            json_mode=True
        )
        res = json.loads(raw_text)
        return float(res.get("score", 50)), res.get("matched_reasons", exact_matched)
    except Exception:
        score = min(50 + len(exact_matched) * 25, 100)
        return float(score), exact_matched if exact_matched else ["기본 일치"]

# 모드 선택
st.sidebar.divider()
user_role = st.sidebar.radio(
    "접속 모드 선택",
    ["🏢 사업주 모드", "👵 구직자 모드", "⚙️ 일자리 추천"]
)

# ---------------------------------------------------------
# [1] 사업주 모드
# ---------------------------------------------------------
if user_role == "🏢 사업주 모드":
    st.header("🏢 사업주 전용 - 일자리 등록")

    with st.form("employer_form"):
        col1, col2 = st.columns(2)
        with col1:
            title = st.text_input("업무명")
            comp_name = st.text_input("사업체(기관)명")
            code_sel = st.selectbox(
                "2026 사업분류코드 선택",
                list(BUSINESS_CODES.keys()),
                format_func=lambda x: f"[{x}] {BUSINESS_CODES[x]['name']} ({BUSINESS_CODES[x]['category']})"
            )
            region = st.text_input("지역 (시/군/구)")

        with col2:
            pay = st.number_input("임금 (월/원)", value=0, step=10000)
            hours = st.number_input("근무 시간 (월/시간)", value=0, step=5)
            extra_conds = st.text_input("기타 채용 조건 (우대 키워드, 쉼표 구분)")

        req_w = code_sel in WALKING_CODES
        req_l = code_sel in LITERACY_CODES
        is_h = code_sel in HOURS_CODES

        st.info(f"💡 **기본 채용 조건**: 거동 ({'예' if req_w else '아니오'}) | 기초문해력 ({'예' if req_l else '아니오'}) | 장시간근무 ({'예' if is_h else '아니오'})")

        submit = st.form_submit_button("등록")
        if submit:
            existing_jobs = get_jobs_from_firestore()
            max_num = 0
            for j in existing_jobs:
                try:
                    num = int(j["id"].split("-")[-1])
                    if num > max_num:
                        max_num = num
                except ValueError:
                    pass
            new_job_id = f"JOB-2026-{max_num + 1:02d}"

            new_job = {
                "id": new_job_id,
                "company_name": comp_name,
                "title": title,
                "code": code_sel,
                "region_sigungu": region,
                "pay": pay,
                "hours": hours,
                "req_walking": req_w,
                "req_literacy": req_l,
                "is_hours": is_h,
                "extra_conditions": [x.strip() for x in extra_conds.split(",") if x.strip()]
            }
            save_job_to_firestore(new_job)
            st.success(f"✅ 일자리가 등록되었습니다. (ID: {new_job_id})")
            st.rerun()

    st.subheader("📋 현재 등록된 일자리")
    db1_jobs = get_jobs_from_firestore()
    if db1_jobs:
        st.dataframe(pd.DataFrame(db1_jobs), use_container_width=True)

        st.divider()
        st.subheader("🗑️ 일자리 삭제")
        job_options = {
            j["id"]: f"[{j['id']}] {j.get('title', '제목없음')} - {j.get('company_name', '')} ({j.get('region_sigungu', '')})"
            for j in db1_jobs
        }
        del_col1, del_col2 = st.columns([3, 1])
        with del_col1:
            selected_job_id = st.selectbox(
                "삭제할 일자리 선택",
                options=list(job_options.keys()),
                format_func=lambda x: job_options[x],
                label_visibility="collapsed"
            )
        with del_col2:
            if st.button("🗑️ 선택한 일자리 삭제", use_container_width=True):
                delete_job_from_firestore(selected_job_id)
                st.success(f"일자리({selected_job_id})가 삭제되었습니다.")
                st.rerun()
    else:
        st.write("등록된 일자리가 없습니다.")

# ---------------------------------------------------------
# [2] 구직자 모드
# ---------------------------------------------------------
elif user_role == "👵 구직자 모드":
    st.header("👵 어르신을 위한 챗봇")

    if not groq_api_key:
        st.warning("⚠️ 사이드바에 Groq API Key를 먼저 입력해 주세요.")
    else:
        client = get_groq_client(groq_api_key)

        for msg in st.session_state.chat_history:
            st.chat_message(msg["role"]).write(msg["content"])

        if user_input := st.chat_input("답변을 입력하세요 (예: 나 수원시 살고 옛날에 청소 일 했어. 허리가 좀 아파.)"):
            st.session_state.chat_history.append({"role": "user", "content": user_input})
            st.chat_message("user").write(user_input)

            system_prompt = (
                "당신은 어르신의 일자리 프로필 작성을 위해 필요한 정보만 여쭤보는 친절한 한국어 인터뷰 도우미입니다.\n\n"
                "[절대 준수 규칙]\n"
                "1. 일자리 추천 절대 금지: 대화 중에 절대 특정 일자리, 직무, 근무지, 사업 내용을 언급하거나 추천하지 마세요. 일자리 매칭은 별도의 '일자리 추천' 메뉴에서 시스템이 자동으로 수행하므로 당신은 오직 정보만 수집합니다.\n"
                "2. 한 번에 질문 딱 1개만: 어르신이 헷갈리지 않으시도록 반드시 한 턴에 질문 1개만 하세요. 절대 두 가지 이상을 한꺼번에 묻지 마세요.\n"
                "3. 짧고 다정한 호응: 어르신 말씀에 1문장으로 따뜻하게 공감한 뒤, 아직 파악되지 않은 다음 항목 질문 1개만 이어가세요.\n\n"
                "[수집해야 할 5가지 프로필 항목]\n"
                "1) 거주 지역 (시/군/구)\n"
                "2) 글 읽기 및 쓰기 가능 여부\n"
                "3) 거동 가능 여부(허리·무릎 등 불편한 곳 유무) 및 오래(장시간) 일하기 가능 여부\n"
                "4) 희망하는 월 임금과 월 근무 시간\n"
                "5) 과거에 해보신 일(경력)이나 잘하시는 일\n\n"
                "[수집 완료 시 행동]\n"
                "위 5가지 항목이 모두 파악되면 추가 질문이나 일자리 추천을 절대 하지 말고, 오직 아래 안내만 하세요:\n"
                "\"말씀해 주신 내용을 모두 확인했습니다! 아래의 '💾 내 일자리 프로필 저장하기' 버튼을 누르신 뒤, 왼쪽 메뉴에서 '⚙️ 일자리 추천'을 선택해 주세요.\""
            )
            
            messages = [{"role": "system", "content": system_prompt}] + st.session_state.chat_history

            with st.chat_message("assistant"):
                try:
                    bot_reply = call_groq_safe(client, messages=messages, temperature=0.7, json_mode=False)
                    st.write(bot_reply)
                    st.session_state.chat_history.append({"role": "assistant", "content": bot_reply})
                except Exception as e:
                    st.error(f"⚠️ Groq API 오류가 발생했습니다: {e}")

        st.divider()

        btn_col1, btn_col2 = st.columns(2)
        with btn_col1:
            save_clicked = st.button("💾 내 일자리 프로필 저장하기", use_container_width=True)
        with btn_col2:
            reset_chat_clicked = st.button("🔄 대화 내역 초기화", use_container_width=True)

        if reset_chat_clicked:
            st.session_state.chat_history = list(INITIAL_CHAT)
            st.rerun()

        if save_clicked:
            with st.spinner("대화를 정밀 분석 중입니다..."):
                parse_prompt = (
                    "다음 대화 내역 전체를 분석하여 구직자의 프로필을 JSON 형식으로만 파싱해 주세요.\n"
                    "반드시 JSON 포맷만을 출력해야 합니다. 파악되지 않은 값은 기본값(false 또는 null)을 넣으세요.\n\n"
                    "JSON 키 항목:\n"
                    "- region_sigungu (string: 시/군/구, 예: '수원시')\n"
                    "- has_literacy (boolean: 읽기/쓰기 가능 여부)\n"
                    "- can_walking (boolean: 거동 가능 여부, 통증/불편 시 false)\n"
                    "- can_hours (boolean: 장시간 근무 가능 여부)\n"
                    "- target_pay (int: 희망 월 임금 숫자만)\n"
                    "- target_hours (int: 희망 월 근무시간 숫자만)\n"
                    "- experiences (list of strings: 과거 경력 키워드)\n\n"
                    f"대화 내역:\n{json.dumps(st.session_state.chat_history, ensure_ascii=False)}"
                )

                try:
                    raw_json_str = call_groq_safe(
                        client,
                        messages=[
                            {"role": "system", "content": "You are a data extraction assistant that outputs strictly valid JSON."},
                            {"role": "user", "content": parse_prompt}
                        ],
                        temperature=0.0,
                        json_mode=True
                    )
                    parsed_json = json.loads(raw_json_str)
                    save_senior_profile_to_firestore(parsed_json)
                    st.success("✅ 구직자 프로필이 저장되었습니다.")
                except Exception as e:
                    st.error(f"⚠️ 프로필 분석 중 오류가 발생했습니다: {e}")

        senior = get_senior_profile_from_firestore()
        if senior:
            st.subheader(f"📋 현재 저장된 구직자 프로필 (`{st.session_state.user_id}`)")
            st.json(senior)
            if st.button("🗑️ 저장된 프로필 삭제하기"):
                delete_senior_profile_from_firestore()
                st.success("저장된 구직자 프로필이 삭제되었습니다.")
                st.rerun()

# ---------------------------------------------------------
# [3] 일자리 추천 모드
# ---------------------------------------------------------
elif user_role == "⚙️ 일자리 추천":
    senior = get_senior_profile_from_firestore()
    db1_jobs = get_jobs_from_firestore()

    if not senior:
        st.warning("⚠️ '👵 구직자 모드' 탭에서 프로필을 먼저 저장해 주세요.")
    elif not db1_jobs:
        st.warning("⚠️ '🏢 사업주 모드' 탭에서 일자리를 먼저 등록해 주세요.")
    else:
        client = get_groq_client(groq_api_key)
        db2_prefs = get_preferences_from_firestore()

        # [하드필터링]
        passed_jobs = []
        failed_jobs = []

        for j in db1_jobs:
            reasons = []
            if j.get("region_sigungu") != senior.get("region_sigungu"):
                reasons.append(f"지역 불일치 ({j.get('region_sigungu')} ≠ {senior.get('region_sigungu')})")
            if j.get("req_walking") and not senior.get("can_walking", False):
                reasons.append("거동 조건 미달")
            if j.get("req_literacy") and not senior.get("has_literacy", False):
                reasons.append("기초문해력 미달")
            if j.get("is_hours") and not senior.get("can_hours", False):
                reasons.append("장시간근무 미달")
            if j.get("pay", 0) < (senior.get("target_pay") or 0) * 0.8:
                reasons.append("희망임금 미달")

            if reasons:
                failed_jobs.append((j, reasons))
            else:
                passed_jobs.append(j)

        # [소프트스코어링]
        st.divider()
        scored_list = []

        with st.spinner("Firebase DB 데이터와 Groq AI를 통해 실시간 분석 중입니다..."):
            for j in passed_jobs:
                job_extras = j.get("extra_conditions", [])
                senior_exps = senior.get("experiences") or []

                a_index, matched_reasons = calculate_a_index_with_llm(client, senior_exps, job_extras)

                pref_data = db2_prefs.get(j["id"], {"select_count": 0})
                select_cnt = pref_data.get("select_count", 0)
                b_index = min(select_cnt * 10, 100)

                if select_cnt == 0:
                    final_score = float(a_index)
                    weight_info = "기타 채용 조건과의 일치도 점수 100% (최초)"
                else:
                    final_score = (a_index * 0.6) + (b_index * 0.4)
                    weight_info = f"기타 채용 조건과의 일치도 점수({a_index:.1f}점)*0.6 + 유사 고령자의 선호도 점수({b_index}점)*0.4"

                scored_list.append({
                    "job": j,
                    "a_index": a_index,
                    "b_index": b_index,
                    "final_score": final_score,
                    "weight_info": weight_info,
                    "matched": matched_reasons
                })

        scored_list.sort(key=lambda x: x["final_score"], reverse=True)

        st.subheader("🏆 맘에 드는 일자리 순위")

        if not scored_list:
            st.info("조건에 부합하는 일자리가 없습니다.")
        else:
            for rank, item in enumerate(scored_list, 1):
                j = item["job"]
                with st.expander(f"✨ [{rank}위] {j['title']} (최종 점수: {item['final_score']:.1f}점)", expanded=True):
                    st.write(f"- **사업체명**: {j['company_name']} | **사업코드**: `{j['code']}`")
                    st.write(f"- **기타 채용 조건과의 일치도**: **{item['a_index']:.1f}점** (매칭 판단: `{', '.join(item['matched'])}`)")
                    st.write(f"- **유사 고령자 선호도**: **{item['b_index']}점** (산출 방식: {item['weight_info']})")

                    if st.button(f"👍 이 일자리 마음에 듭니다 (JOB: {j['id']})", key=j['id']):
                        increment_b_index_in_firestore(j["id"])
                        st.success("✅ 선택 내역이 반영되었습니다!")
