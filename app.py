import streamlit as st
import pandas as pd
from datetime import datetime
import bcrypt
import gspread
from google.oauth2.service_account import Credentials

# ================================================================
#  CONFIG
# ================================================================
st.set_page_config(page_title="AskSQI", layout="centered")

for key, default in [("user", None), ("role", "student"), ("show_welcome", False)]:
    if key not in st.session_state:
        st.session_state[key] = default

COURSES = [
    "Software Engineering", "Product Management", "Web Design",
    "Cyber Security", "Java Programming", "Data Science",
    "Data Analysis", "Robotics Engineering", "Artificial Intelligence (AI)",
    "Networking", "Accounting Applications", "Hardware Engineering",
]
LEVELS = [1, 2, 3, 4, 5, 6]

USERS_SHEET     = "users"
QUESTIONS_SHEET = "questions"
ANSWERS_SHEET   = "answers"

USERS_HEADERS     = ["username", "password_hash", "role", "created_at"]
QUESTIONS_HEADERS = ["id", "title", "description", "course", "level",
                     "code", "error_message", "author", "created_at"]
ANSWERS_HEADERS   = ["id", "question_id", "answer", "responder", "verified", "created_at"]

ADMIN_ROLES = ("instructor", "admin")


# ================================================================
#  GOOGLE SHEETS HELPERS
# ================================================================
def ensure_headers(ws, headers):
    existing = ws.row_values(1)
    if existing != headers:
        if not existing:
            ws.append_row(headers)
        else:
            ws.delete_rows(1)
            ws.insert_row(headers, 1)


def append_row(ws, row_values):
    ws.append_row(row_values, value_input_option="USER_ENTERED")


def next_id(df, id_col="id"):
    if df.empty or id_col not in df.columns:
        return 1
    mx = pd.to_numeric(df[id_col], errors="coerce").max()
    return 1 if pd.isna(mx) else int(mx) + 1


def normalize_questions_df(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    df["id"]    = pd.to_numeric(df.get("id"), errors="coerce")
    df["level"] = pd.to_numeric(df.get("level"), errors="coerce").fillna(1).astype(int).clip(1, 6)
    return df


def normalize_answers_df(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    df["id"]          = pd.to_numeric(df.get("id"), errors="coerce")
    df["question_id"] = pd.to_numeric(df.get("question_id"), errors="coerce")
    df["verified"]    = df.get("verified", "").astype(str).str.lower().isin(["true", "1", "yes"])
    return df


@st.cache_resource
def get_gspread_client():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ],
    )
    return gspread.authorize(creds)


@st.cache_resource
def open_db():
    return get_gspread_client().open_by_key(st.secrets["SPREADSHEET_ID"])


def _read_ws(sheet_name: str, headers: list) -> pd.DataFrame:
    ws = open_db().worksheet(sheet_name)
    ensure_headers(ws, headers)
    return pd.DataFrame(ws.get_all_records())


@st.cache_data(ttl=60)
def read_users_df() -> pd.DataFrame:
    return _read_ws(USERS_SHEET, USERS_HEADERS)


@st.cache_data(ttl=15)
def read_questions_df() -> pd.DataFrame:
    return normalize_questions_df(_read_ws(QUESTIONS_SHEET, QUESTIONS_HEADERS))


@st.cache_data(ttl=15)
def read_answers_df() -> pd.DataFrame:
    return normalize_answers_df(_read_ws(ANSWERS_SHEET, ANSWERS_HEADERS))


def refresh_data():
    return read_users_df(), read_questions_df(), read_answers_df()


# ----------------------------------------------------------------
#  Delete helpers
# ----------------------------------------------------------------
def _overwrite_sheet(ws, headers: list, df: pd.DataFrame):
    ws.clear()
    ws.append_row(headers)
    if not df.empty:
        rows = df[headers].fillna("").values.tolist()
        ws.append_rows(rows, value_input_option="USER_ENTERED")


def delete_question(q_id: int):
    q_df = read_questions_df()
    a_df = read_answers_df()
    q_df = q_df[q_df["id"] != q_id]
    a_df = a_df[a_df["question_id"] != q_id]
    sh = open_db()
    _overwrite_sheet(sh.worksheet(QUESTIONS_SHEET), QUESTIONS_HEADERS, q_df)
    _overwrite_sheet(sh.worksheet(ANSWERS_SHEET),   ANSWERS_HEADERS,   a_df)
    read_questions_df.clear()
    read_answers_df.clear()


def delete_answer(a_id: int):
    a_df = read_answers_df()
    a_df = a_df[a_df["id"] != a_id]
    _overwrite_sheet(open_db().worksheet(ANSWERS_SHEET), ANSWERS_HEADERS, a_df)
    read_answers_df.clear()


# ================================================================
#  AUTH HELPERS
# ================================================================
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def check_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except Exception:
        return False


def validate_password(password: str):
    """Return an error string, or None if the password is valid."""
    if len(password) < 8:
        return "Password must be at least 8 characters."
    if not any(c.isupper() for c in password):
        return "Password must contain at least one uppercase letter."
    if not any(c.isdigit() for c in password):
        return "Password must contain at least one number."
    return None


def auth_sidebar(users_df):
    st.sidebar.title("Account")

    if not st.session_state["user"]:
        mode = st.sidebar.radio("Select option", ["Login", "Register"], horizontal=True)

        if mode == "Register":
            username = st.sidebar.text_input("Username", key="reg_username")
            password = st.sidebar.text_input("Password", type="password", key="reg_password")
            st.sidebar.caption("Min 8 chars · 1 uppercase · 1 number")

            if st.sidebar.button("Create account", key="reg_btn"):
                username, password = username.strip(), password.strip()
                if not username or not password:
                    st.sidebar.error("Username and password are required.")
                    return
                if not users_df.empty and username in users_df["username"].astype(str).values:
                    st.sidebar.error("Username already exists.")
                    return
                err = validate_password(password)
                if err:
                    st.sidebar.error(err)
                    return
                users_ws = open_db().worksheet(USERS_SHEET)
                append_row(users_ws, [
                    username, hash_password(password), "student",
                    datetime.now().strftime("%Y-%m-%d %H:%M"),
                ])
                read_users_df.clear()
                st.sidebar.success("Account created! Please log in.")
                st.rerun()

        else:
            username = st.sidebar.text_input("Username", key="login_username")
            password = st.sidebar.text_input("Password", type="password", key="login_password")

            if st.sidebar.button("Login", key="login_btn"):
                username, password = username.strip(), password.strip()
                if users_df.empty:
                    st.sidebar.error("No users found. Please register first.")
                    return
                match = users_df[users_df["username"].astype(str) == username]
                if match.empty:
                    st.sidebar.error("User not found.")
                    return
                if check_password(password, str(match.iloc[0]["password_hash"])):
                    st.session_state["user"]         = username
                    st.session_state["role"]         = str(match.iloc[0].get("role", "student"))
                    st.session_state["show_welcome"] = True
                    st.rerun()
                else:
                    st.sidebar.error("Incorrect password.")
    else:
        st.sidebar.write(f"Logged in as: **{st.session_state['user']}**")
        st.sidebar.write(f"Role: **{st.session_state['role']}**")
        if st.sidebar.button("Logout", key="logout_btn"):
            st.session_state.update({"user": None, "role": "student", "show_welcome": False})
            st.rerun()


# ================================================================
#  BOOT
# ================================================================
users_df = read_users_df()
auth_sidebar(users_df)

if not st.session_state["user"]:
    st.title("💬 AskSQI")
    st.info("Please login or register using the sidebar to ask or answer questions.")
    st.stop()

if st.session_state.pop("show_welcome", False):
    st.success(f"Welcome, **{st.session_state['user']}**! You can now ask questions and support your peers.")

questions_df = read_questions_df()
answers_df   = read_answers_df()

current_user = st.session_state["user"]
current_role = st.session_state.get("role", "student")
is_admin     = current_role in ADMIN_ROLES

# ================================================================
#  HEADER
# ================================================================
st.title("💬 AskSQI")
st.subheader("A safe, inclusive space for asking and answering questions across all courses")
st.markdown(
    "Ask questions outside class hours, share code and error messages when needed, "
    "and receive peer support with instructor-reviewed guidance when available."
)

# ================================================================
#  TABS  (Dashboard only visible to instructors / admins)
# ================================================================
if is_admin:
    tab_browse, tab_ask, tab_mine, tab_stats = st.tabs(
        ["📚 Browse", "✍🏽 Ask", "🙋 My Questions", "📊 Dashboard"]
    )
else:
    tab_browse, tab_ask, tab_mine = st.tabs(
        ["📚 Browse", "✍🏽 Ask", "🙋 My Questions"]
    )
    tab_stats = None


# ================================================================
#  SHARED RENDERER
# ================================================================
def question_status(q_id, a_df):
    if a_df.empty:
        return "🔴 Unanswered"
    rel = a_df[a_df["question_id"] == q_id]
    if rel.empty:
        return "🔴 Unanswered"
    if rel["verified"].any():
        return "✅ Verified"
    return "🟡 Answered"


def render_questions(q_subset: pd.DataFrame, a_df: pd.DataFrame, allow_delete_q: bool = False):
    if q_subset.empty:
        st.info("No questions to show.")
        return

    for _, q in q_subset.sort_values("id", ascending=False).iterrows():
        q_id   = int(pd.to_numeric(q.get("id", 0), errors="coerce") or 0)
        author = q.get("author", "Unknown")
        rel    = a_df[a_df["question_id"] == q_id] if not a_df.empty else pd.DataFrame()
        n_ans  = len(rel)
        status = question_status(q_id, a_df)

        header = (
            f"{status}  |  {q.get('title', '(No title)')}  •  "
            f"{q.get('course', '?')}  •  Level {q.get('level', 1)}  •  "
            f"👤 {author}  •  💬 {n_ans} answer{'s' if n_ans != 1 else ''}"
        )

        with st.expander(header):
            st.write(q.get("description", ""))

            err = q.get("error_message", "")
            if isinstance(err, str) and err.strip():
                st.markdown("**🧯 Error Message**")
                st.code(err, language="text")

            snippet = q.get("code", "")
            if isinstance(snippet, str) and snippet.strip():
                st.markdown("**🧩 Code Snippet**")
                st.code(snippet, language="python")

            # Delete question
            if allow_delete_q and (is_admin or author == current_user):
                if st.button("🗑️ Delete question", key=f"del_q_{q_id}",
                             help="Deletes this question and all its answers"):
                    delete_question(q_id)
                    st.warning("Question deleted.")
                    st.rerun()

            # ---- Answers ----
            st.markdown("**💡 Answers**")
            if rel.empty:
                st.info("No answers yet. Be the first to help!")
            else:
                for _, a in rel.sort_values("verified", ascending=False).iterrows():
                    a_id       = int(pd.to_numeric(a.get("id", 0), errors="coerce") or 0)
                    responder  = a.get("responder", "Unknown")
                    badge      = "✅ Instructor Verified" if bool(a.get("verified", False)) else "👤 Peer Answer"

                    col_ans, col_del = st.columns([11, 1])
                    with col_ans:
                        st.markdown(f"**{badge}**")
                        st.write(a.get("answer", ""))
                        st.caption(f"— {responder} · {a.get('created_at', '')}")
                    with col_del:
                        if is_admin or responder == current_user:
                            if st.button("🗑️", key=f"del_a_{a_id}", help="Delete this answer"):
                                delete_answer(a_id)
                                st.warning("Answer deleted.")
                                st.rerun()

            # ---- Add answer ----
            already_answered = (
                not rel.empty and current_user in rel["responder"].astype(str).values
            )

            if already_answered and not is_admin:
                st.info("✏️ You have already answered this question.")
            else:
                st.markdown("**✍🏽 Add an Answer**")
                with st.form(f"answer_form_{q_id}"):
                    answer_text = st.text_area("Your Answer", key=f"answer_{q_id}")
                    verified    = (
                        st.checkbox("Mark as Instructor Verified", key=f"verify_{q_id}")
                        if is_admin else False
                    )
                    if st.form_submit_button("Post Answer"):
                        if not answer_text.strip():
                            st.error("Please enter an answer.")
                        else:
                            answers_ws = open_db().worksheet(ANSWERS_SHEET)
                            append_row(answers_ws, [
                                next_id(a_df, "id"), q_id, answer_text.strip(),
                                current_user, str(bool(verified)),
                                datetime.now().strftime("%Y-%m-%d %H:%M"),
                            ])
                            read_answers_df.clear()
                            st.success("Answer posted!")
                            st.rerun()


# ================================================================
#  TAB — ASK A QUESTION
# ================================================================
with tab_ask:
    st.markdown("### ✍🏽 Ask a Question")
    with st.form("ask_question_form"):
        title         = st.text_input("Question Title",
                                      placeholder="Example: Why is my code returning NaN?")
        course        = st.selectbox("Course", COURSES)
        level         = st.selectbox("Level", LEVELS, index=0)
        description   = st.text_area("Describe your problem",
                                     placeholder="Explain what you expected vs what you got.")
        code          = st.text_area("Code Snippet (optional)", height=150,
                                     placeholder="Paste your code here.")
        error_message = st.text_area("Error Message (optional)", height=100,
                                     placeholder="Paste the error message exactly as it appears.")
        submitted = st.form_submit_button("Submit Question")

    if submitted:
        if not title.strip() or not description.strip():
            st.error("Please provide a title and a description.")
        else:
            questions_ws = open_db().worksheet(QUESTIONS_SHEET)
            append_row(questions_ws, [
                next_id(questions_df, "id"),
                title.strip(), description.strip(),
                course, level,
                code.strip(), error_message.strip(),
                current_user,
                datetime.now().strftime("%Y-%m-%d %H:%M"),
            ])
            read_questions_df.clear()
            st.success("Question submitted! Head to Browse to see it.")
            st.rerun()


# ================================================================
#  TAB — BROWSE QUESTIONS
# ================================================================
with tab_browse:
    st.markdown("### 📚 Browse Questions")
    _, questions_df, answers_df = refresh_data()

    # Filters
    col1, col2, col3 = st.columns([3, 2, 1])
    with col1:
        search_query = st.text_input("Search", placeholder="Keyword in title or description…",
                                     label_visibility="collapsed")
    with col2:
        filter_course = st.selectbox("Course", ["All Courses"] + COURSES,
                                     label_visibility="collapsed")
    with col3:
        filter_level = st.selectbox("Level", ["All"] + [str(l) for l in LEVELS],
                                    label_visibility="collapsed")

    filter_status = st.radio(
        "Status", ["All", "🔴 Unanswered", "🟡 Answered", "✅ Verified"],
        horizontal=True, label_visibility="collapsed"
    )

    filtered = questions_df.copy() if not questions_df.empty else pd.DataFrame()

    if not filtered.empty:
        if filter_course != "All Courses":
            filtered = filtered[filtered["course"] == filter_course]
        if filter_level != "All":
            filtered = filtered[filtered["level"] == int(filter_level)]
        if search_query.strip():
            kw = search_query.strip().lower()
            mask = (
                filtered["title"].astype(str).str.lower().str.contains(kw, na=False) |
                filtered["description"].astype(str).str.lower().str.contains(kw, na=False)
            )
            filtered = filtered[mask]
        if filter_status != "All" and not answers_df.empty:
            answered_ids = set(answers_df["question_id"].dropna().astype(int))
            verified_ids = set(answers_df[answers_df["verified"]]["question_id"].dropna().astype(int))
            if filter_status == "🔴 Unanswered":
                filtered = filtered[~filtered["id"].isin(answered_ids)]
            elif filter_status == "🟡 Answered":
                filtered = filtered[filtered["id"].isin(answered_ids) & ~filtered["id"].isin(verified_ids)]
            elif filter_status == "✅ Verified":
                filtered = filtered[filtered["id"].isin(verified_ids)]
        elif filter_status != "All":
            # No answers at all — everything is unanswered
            if filter_status != "🔴 Unanswered":
                filtered = pd.DataFrame()

    st.caption(f"{len(filtered)} question(s) found")
    render_questions(filtered, answers_df, allow_delete_q=True)


# ================================================================
#  TAB — MY QUESTIONS
# ================================================================
with tab_mine:
    st.markdown("### 🙋 My Questions")
    _, questions_df, answers_df = refresh_data()
    my_q = questions_df[questions_df["author"] == current_user] if not questions_df.empty else pd.DataFrame()
    st.caption(f"{len(my_q)} question(s) asked by you")
    render_questions(my_q, answers_df, allow_delete_q=True)


# ================================================================
#  TAB — DASHBOARD  (instructors / admins only)
# ================================================================
if tab_stats is not None:
    with tab_stats:
        st.markdown("### 📊 Dashboard")
        _, questions_df, answers_df = refresh_data()

        if questions_df.empty:
            st.info("No data yet.")
        else:
            answered_ids = set(answers_df["question_id"].dropna().astype(int)) if not answers_df.empty else set()
            verified_ids = (
                set(answers_df[answers_df["verified"]]["question_id"].dropna().astype(int))
                if not answers_df.empty else set()
            )
            total_q    = len(questions_df)
            total_a    = len(answers_df) if not answers_df.empty else 0
            unanswered = total_q - len(questions_df[questions_df["id"].isin(answered_ids)])
            verified_q = len(questions_df[questions_df["id"].isin(verified_ids)])

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total Questions",      total_q)
            c2.metric("Total Answers",        total_a)
            c3.metric("Unanswered",           unanswered)
            c4.metric("Instructor Verified",  verified_q)

            st.markdown("---")

            col_l, col_r = st.columns(2)
            with col_l:
                st.markdown("**Questions per Course**")
                course_counts = questions_df["course"].value_counts().rename_axis("Course").reset_index(name="Questions")
                st.bar_chart(course_counts.set_index("Course"))

            with col_r:
                st.markdown("**Questions per Level**")
                level_counts = questions_df["level"].value_counts().sort_index().rename_axis("Level").reset_index(name="Questions")
                st.bar_chart(level_counts.set_index("Level"))

            st.markdown("---")
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("**Most Active Students (by questions)**")
                top_askers = questions_df["author"].value_counts().head(10).rename_axis("Student").reset_index(name="Questions Asked")
                st.dataframe(top_askers, use_container_width=True, hide_index=True)

            with col_b:
                st.markdown("**Most Helpful Peers (by answers)**")
                if not answers_df.empty:
                    top_helpers = answers_df["responder"].value_counts().head(10).rename_axis("Student").reset_index(name="Answers Given")
                    st.dataframe(top_helpers, use_container_width=True, hide_index=True)
                else:
                    st.info("No answers yet.")