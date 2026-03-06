import streamlit as st
import pandas as pd
from datetime import datetime
import bcrypt
import gspread
from google.oauth2.service_account import Credentials

# ================================================================
#  CONFIG
# ================================================================
st.set_page_config(page_title="AskSQI", layout="wide", page_icon="💬",
                   initial_sidebar_state="collapsed")

for key, default in [("user", None), ("role", "student"), ("show_welcome", False), ("auth_mode", "login")]:
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
#  THEME
# ================================================================
def inject_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&family=Fraunces:opsz,wght@9..144,700;9..144,900&display=swap');

    :root {
        --bg:             #0f1117;
        --surface:        #181c27;
        --surface-2:      #1e2333;
        --border:         #2a2f42;
        --border-light:   #333a52;
        --accent:         #4f7cff;
        --accent-dim:     #2a3f80;
        --accent-glow:    rgba(79,124,255,0.18);
        --green:          #22c55e;
        --green-dim:      #14532d;
        --amber:          #f59e0b;
        --amber-dim:      #451a03;
        --red:            #ef4444;
        --red-dim:        #450a0a;
        --text-primary:   #f0f2f8;
        --text-secondary: #8b93b0;
        --text-muted:     #555e7a;
        --radius:         12px;
        --radius-sm:      8px;
        --shadow:         0 4px 24px rgba(0,0,0,0.4);
        --shadow-sm:      0 2px 8px rgba(0,0,0,0.3);
    }

    html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
        background-color: var(--bg) !important;
        font-family: 'DM Sans', sans-serif !important;
        color: var(--text-primary) !important;
    }

    /* Hide ALL Streamlit chrome and sidebar toggle */
    #MainMenu, footer, [data-testid="stToolbar"],
    [data-testid="stDecoration"],
    [data-testid="collapsedControl"],
    [data-testid="stSidebarCollapseButton"],
    button[kind="header"] { display: none !important; }

    /* ── Sidebar (logged-in only) ── */
    [data-testid="stSidebar"] {
        background: var(--surface) !important;
        border-right: 1px solid var(--border) !important;
    }
    [data-testid="stSidebar"] * { color: var(--text-primary) !important; }
    [data-testid="stSidebar"] .stButton > button {
        background: var(--accent) !important;
        color: #fff !important;
        border: none !important;
        border-radius: var(--radius-sm) !important;
        font-weight: 600 !important;
    }

    /* ── Auth card (login/register page) ── */
    .auth-card {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: var(--radius);
        padding: 2rem 2.2rem;
        max-width: 420px;
        margin: 0 auto;
    }

    /* ── Tabs ── */
    [data-testid="stTabs"] [role="tablist"] {
        background: var(--surface) !important;
        border-radius: var(--radius) !important;
        padding: 4px !important;
        border: 1px solid var(--border) !important;
        gap: 2px !important;
    }
    [data-testid="stTabs"] [role="tab"] {
        color: var(--text-secondary) !important;
        border-radius: var(--radius-sm) !important;
        font-weight: 500 !important;
        font-size: 0.875rem !important;
        padding: 6px 16px !important;
        transition: all 0.2s !important;
        border: none !important;
        background: transparent !important;
    }
    [data-testid="stTabs"] [role="tab"][aria-selected="true"] {
        background: var(--accent) !important;
        color: #fff !important;
        font-weight: 600 !important;
    }
    [data-testid="stTabs"] [role="tab"]:hover:not([aria-selected="true"]) {
        background: var(--surface-2) !important;
        color: var(--text-primary) !important;
    }
    [data-testid="stTabs"] [role="tablist"]::before { display: none !important; }

    /* ── Inputs ── */
    .stTextInput input, .stTextArea textarea, .stSelectbox > div > div {
        background: var(--surface-2) !important;
        border: 1px solid var(--border) !important;
        color: var(--text-primary) !important;
        border-radius: var(--radius-sm) !important;
        font-family: 'DM Sans', sans-serif !important;
        transition: border-color 0.2s !important;
    }
    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: var(--accent) !important;
        box-shadow: 0 0 0 3px var(--accent-glow) !important;
        outline: none !important;
    }
    .stTextInput label, .stTextArea label, .stSelectbox label {
        color: var(--text-secondary) !important;
        font-size: 0.825rem !important;
        font-weight: 500 !important;
        letter-spacing: 0.02em !important;
        text-transform: uppercase !important;
    }

    /* ── Buttons ── */
    .stButton > button, .stFormSubmitButton > button {
        background: var(--accent) !important;
        color: #fff !important;
        border: none !important;
        border-radius: var(--radius-sm) !important;
        font-family: 'DM Sans', sans-serif !important;
        font-weight: 600 !important;
        font-size: 0.9rem !important;
        padding: 0.5rem 1.2rem !important;
        transition: all 0.2s !important;
        box-shadow: 0 2px 8px rgba(79,124,255,0.3) !important;
    }
    .stButton > button:hover, .stFormSubmitButton > button:hover {
        opacity: 0.88 !important;
        transform: translateY(-1px) !important;
    }
    .danger-btn .stButton > button {
        background: transparent !important;
        color: var(--red) !important;
        border: 1px solid var(--red-dim) !important;
        box-shadow: none !important;
        font-size: 0.78rem !important;
        padding: 3px 10px !important;
    }
    .danger-btn .stButton > button:hover {
        background: var(--red-dim) !important;
        transform: none !important;
    }

    /* ── Hero ── */
    .asksqi-hero {
        padding: 2rem 0 1.5rem;
        border-bottom: 1px solid var(--border);
        margin-bottom: 1.5rem;
    }
    .asksqi-hero h1 {
        font-family: 'Fraunces', serif !important;
        font-size: 2.4rem !important;
        font-weight: 900 !important;
        background: linear-gradient(135deg, #f0f2f8 0%, #4f7cff 100%);
        -webkit-background-clip: text !important;
        -webkit-text-fill-color: transparent !important;
        background-clip: text !important;
        line-height: 1.1 !important;
        margin-bottom: 0.4rem !important;
    }
    .asksqi-hero p { color: var(--text-secondary) !important; font-size: 0.95rem !important; margin: 0 !important; }
    .user-pill {
        display: inline-flex; align-items: center; gap: 6px;
        background: var(--surface-2); border: 1px solid var(--border);
        border-radius: 999px; padding: 4px 14px; font-size: 0.8rem;
        color: var(--text-secondary) !important; margin-top: 0.8rem;
    }
    .user-pill span { color: var(--accent) !important; font-weight: 600; }

    /* ── Expander ── */
    [data-testid="stExpander"] {
        background: var(--surface) !important;
        border: 1px solid var(--border) !important;
        border-radius: var(--radius) !important;
        margin-bottom: 0.6rem !important;
        overflow: hidden !important;
    }
    [data-testid="stExpander"]:hover { border-color: var(--border-light) !important; }
    [data-testid="stExpander"] summary {
        padding: 1rem 1.2rem !important;
        font-weight: 500 !important;
        font-size: 0.9rem !important;
        color: var(--text-primary) !important;
        background: var(--surface) !important;
    }
    [data-testid="stExpander"] summary:hover { background: var(--surface-2) !important; }
    [data-testid="stExpander"] > div > div {
        padding: 0 1.2rem 1.2rem !important;
        background: var(--surface) !important;
    }

    /* ── Badges ── */
    .badge {
        display: inline-flex; align-items: center; gap: 4px;
        padding: 2px 10px; border-radius: 999px;
        font-size: 0.72rem; font-weight: 600; letter-spacing: 0.03em;
    }
    .badge-blue  { background: var(--accent-dim);  color: #93b4ff; border: 1px solid #2a3f80; }
    .badge-green { background: var(--green-dim);   color: #86efac; border: 1px solid #166534; }
    .badge-amber { background: var(--amber-dim);   color: #fcd34d; border: 1px solid #78350f; }
    .badge-red   { background: var(--red-dim);     color: #fca5a5; border: 1px solid #7f1d1d; }
    .badge-muted { background: var(--surface-2);   color: var(--text-muted); border: 1px solid var(--border); }
    .q-card-meta { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }

    /* ── Answer cards ── */
    .answer-card {
        background: var(--surface-2); border: 1px solid var(--border);
        border-left: 3px solid var(--border-light);
        border-radius: var(--radius-sm); padding: 1rem 1.1rem; margin-bottom: 0.6rem;
    }
    .answer-card.verified {
        border-left-color: var(--green);
        background: linear-gradient(90deg, rgba(34,197,94,0.06) 0%, var(--surface-2) 60%);
    }
    .answer-text { color: var(--text-primary); font-size: 0.93rem; line-height: 1.65; }
    .answer-meta { color: var(--text-muted); font-size: 0.76rem; margin-top: 0.5rem; }

    .section-label {
        font-size: 0.72rem; font-weight: 700; letter-spacing: 0.1em;
        text-transform: uppercase; color: var(--text-muted);
        padding: 0.5rem 0 0.4rem; border-top: 1px solid var(--border);
        margin-top: 0.8rem; margin-bottom: 0.5rem;
    }
    .filter-bar {
        background: var(--surface); border: 1px solid var(--border);
        border-radius: var(--radius); padding: 0.85rem 1rem; margin-bottom: 1rem;
    }

    /* ── Metrics ── */
    [data-testid="stMetric"] {
        background: var(--surface) !important; border: 1px solid var(--border) !important;
        border-radius: var(--radius) !important; padding: 1rem 1.2rem !important;
    }
    [data-testid="stMetricLabel"] { color: var(--text-muted) !important; font-size: 0.78rem !important; }
    [data-testid="stMetricValue"] { color: var(--text-primary) !important; font-family: 'Fraunces', serif !important; }

    /* ── Radio pills ── */
    .stRadio > div { gap: 6px !important; }
    .stRadio label {
        background: var(--surface-2) !important; border: 1px solid var(--border) !important;
        border-radius: 999px !important; padding: 4px 14px !important;
        font-size: 0.82rem !important; font-weight: 500 !important;
        color: var(--text-secondary) !important; transition: all 0.15s !important; cursor: pointer !important;
    }
    .stRadio label:has(input:checked) {
        background: var(--accent) !important; border-color: var(--accent) !important; color: #fff !important;
    }
    .stRadio [data-testid="stWidgetLabel"] { display: none !important; }

    /* ── Code ── */
    .stCode, code, pre {
        background: #0a0d14 !important; border: 1px solid var(--border) !important;
        border-radius: var(--radius-sm) !important; font-family: 'DM Mono', monospace !important;
        font-size: 0.83rem !important; color: #a5b4fc !important;
    }

    /* ── Misc ── */
    [data-testid="stAlert"] { border-radius: var(--radius-sm) !important; border: none !important; }
    [data-testid="stDataFrame"] { border: 1px solid var(--border) !important; border-radius: var(--radius) !important; }
    .stCaption, [data-testid="stCaptionContainer"] { color: var(--text-muted) !important; font-size: 0.78rem !important; }
    hr { border-color: var(--border) !important; margin: 1.2rem 0 !important; }
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: var(--bg); }
    ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 999px; }
    </style>
    """, unsafe_allow_html=True)

inject_css()


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
    if len(password) < 8:
        return "Password must be at least 8 characters."
    if not any(c.isupper() for c in password):
        return "Password must contain at least one uppercase letter."
    if not any(c.isdigit() for c in password):
        return "Password must contain at least one number."
    return None


# ================================================================
#  AUTH PAGE  — full-screen, left branding / right forms
# ================================================================
def show_auth_page():
    # Style: strip container padding, colour the column backgrounds
    st.markdown("""
    <style>
    /* Remove all container padding */
    [data-testid="stAppViewContainer"] > .main > .block-container {
        padding: 0 !important;
        max-width: 100% !important;
    }
    [data-testid="stHorizontalBlock"] {
        gap: 0 !important;
        align-items: stretch !important;
    }
    /* Left column — dark gradient background */
    [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child {
        background: linear-gradient(150deg, #0d1021 0%, #111628 50%, #192040 100%);
        padding: 4rem 3rem !important;
        min-height: 100vh;
    }
    /* Right column — plain dark + left border */
    [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:last-child {
        background: #0f1117;
        border-left: 1px solid #2a2f42 !important;
        padding: 4rem 3.5rem !important;
        min-height: 100vh;
    }
    /* Feature rows */
    .feat {
        display:flex; align-items:flex-start; gap:14px;
        margin-bottom:1.6rem;
    }
    .feat-icon {
        width:42px; height:42px; flex-shrink:0;
        background:rgba(79,124,255,0.12);
        border:1px solid rgba(79,124,255,0.28);
        border-radius:10px;
        display:flex; align-items:center; justify-content:center;
        font-size:1.15rem; line-height:1;
    }
    .feat-title { font-weight:600; color:#f0f2f8; font-size:0.92rem; margin-bottom:2px; }
    .feat-body  { color:#555e7a; font-size:0.8rem; line-height:1.5; }
    </style>
    """, unsafe_allow_html=True)

    left, right = st.columns(2, gap="small")

    # ── LEFT PANEL ────────────────────────────────────────────
    with left:
        # Logo + tagline
        st.markdown(
            "<div style='font-family:Fraunces,serif;font-size:3rem;font-weight:900;"
            "background:linear-gradient(135deg,#f0f2f8 20%,#4f7cff 100%);"
            "-webkit-background-clip:text;-webkit-text-fill-color:transparent;"
            "line-height:1.05;margin-bottom:1rem;'>💬 AskSQI</div>",
            unsafe_allow_html=True
        )
        st.markdown(
            "<div style='color:#8b93b0;font-size:1rem;line-height:1.75;"
            "max-width:380px;margin-bottom:3rem;'>"
            "Your institution's peer support platform. Ask questions outside "
            "class hours, share code, and learn together — every course, every level."
            "</div>",
            unsafe_allow_html=True
        )

        # Feature rows — each as its own markdown call (safe)
        features = [
            ("🎓", "12 Courses Covered",
             "From Software Engineering to Data Science — every discipline in one place."),
            ("✅", "Instructor-Verified Answers",
             "Instructors mark trusted answers so you always know what to rely on."),
            ("🤝", "Peer-Powered Learning",
             "Help each other with code, errors, and concepts — any time of day."),
            ("🔍", "Search & Filter",
             "Find answers fast by course, level, or keyword."),
        ]
        for icon, title, body in features:
            st.markdown(
                f"<div class='feat'>"
                f"<div class='feat-icon'>{icon}</div>"
                f"<div><div class='feat-title'>{title}</div>"
                f"<div class='feat-body'>{body}</div></div>"
                f"</div>",
                unsafe_allow_html=True
            )

        st.markdown(
            "<div style='margin-top:2.5rem;padding-top:1.5rem;"
            "border-top:1px solid #2a2f42;color:#555e7a;font-size:0.72rem;'>"
            "SQI Institution · Peer Support Platform</div>",
            unsafe_allow_html=True
        )

    # ── RIGHT PANEL ───────────────────────────────────────────
    with right:
        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

        tab_login, tab_register = st.tabs(["  Log In  ", "  Register  "])

        # ── LOGIN ──
        with tab_login:
            st.markdown(
                "<div style='font-family:Fraunces,serif;font-size:1.9rem;font-weight:900;"
                "color:#f0f2f8;margin-bottom:0.3rem;line-height:1.2;'>Welcome back 👋</div>"
                "<div style='color:#555e7a;font-size:0.88rem;margin-bottom:1.8rem;'>"
                "Sign in to ask questions and help your peers.</div>",
                unsafe_allow_html=True
            )

            if st.session_state.pop("just_registered", False):
                st.success("✅ Account created! Log in below.")

            with st.form("login_form"):
                username  = st.text_input("Username", placeholder="Your username")
                password  = st.text_input("Password", type="password", placeholder="Your password")
                login_btn = st.form_submit_button("Log In →", use_container_width=True)

            if login_btn:
                u, p = username.strip(), password.strip()
                if not u or not p:
                    st.error("Please fill in both fields.")
                else:
                    users_df = read_users_df()
                    if users_df.empty:
                        st.error("No accounts yet — register first.")
                    else:
                        match = users_df[users_df["username"].astype(str) == u]
                        if match.empty:
                            st.error("Username not found.")
                        elif check_password(p, str(match.iloc[0]["password_hash"])):
                            st.session_state["user"]         = u
                            st.session_state["role"]         = str(match.iloc[0].get("role", "student"))
                            st.session_state["show_welcome"] = True
                            st.session_state["auth_mode"]    = "login"
                            st.rerun()
                        else:
                            st.error("Incorrect password.")

        # ── REGISTER ──
        with tab_register:
            st.markdown(
                "<div style='font-family:Fraunces,serif;font-size:1.9rem;font-weight:900;"
                "color:#f0f2f8;margin-bottom:0.3rem;line-height:1.2;'>Create an account</div>"
                "<div style='color:#555e7a;font-size:0.88rem;margin-bottom:1.8rem;'>"
                "Join your classmates on AskSQI — it's free.</div>",
                unsafe_allow_html=True
            )

            with st.form("register_form"):
                new_user = st.text_input("Choose a Username", placeholder="e.g. jane_doe",
                                          key="reg_user")
                new_pass = st.text_input("Choose a Password", type="password",
                                          placeholder="Min 8 chars", key="reg_pass")
                st.caption("Must include at least 1 uppercase letter and 1 number")
                reg_btn  = st.form_submit_button("Create Account →", use_container_width=True)

            if reg_btn:
                u, p = new_user.strip(), new_pass.strip()
                if not u or not p:
                    st.error("Both fields are required.")
                else:
                    users_df = read_users_df()
                    if not users_df.empty and u in users_df["username"].astype(str).values:
                        st.error("That username is already taken.")
                    else:
                        err = validate_password(p)
                        if err:
                            st.error(err)
                        else:
                            users_ws = open_db().worksheet(USERS_SHEET)
                            append_row(users_ws, [
                                u, hash_password(p), "student",
                                datetime.now().strftime("%Y-%m-%d %H:%M"),
                            ])
                            read_users_df.clear()
                            st.session_state["just_registered"] = True
                            st.session_state["auth_mode"]       = "login"
                            st.rerun()


# ================================================================
#  LOGGED-IN SIDEBAR  — user card + sign out only
# ================================================================
def render_sidebar():
    role       = st.session_state.get("role", "student")
    role_color = "#4f7cff" if role in ADMIN_ROLES else "#22c55e"

    with st.sidebar:
        st.markdown(
            "<div style='padding:1.2rem 0 0.8rem;font-family:Fraunces,serif;font-size:1.4rem;"
            "font-weight:900;background:linear-gradient(135deg,#f0f2f8,#4f7cff);"
            "-webkit-background-clip:text;-webkit-text-fill-color:transparent;'>"
            "💬 AskSQI</div>",
            unsafe_allow_html=True
        )
        st.markdown(
            f"<div style='background:#1e2333;border:1px solid #2a2f42;border-radius:10px;"
            f"padding:0.9rem 1rem;margin-bottom:1rem;'>"
            f"<div style='font-size:0.68rem;text-transform:uppercase;letter-spacing:0.08em;"
            f"color:#555e7a;margin-bottom:4px;'>Signed in as</div>"
            f"<div style='font-weight:600;font-size:0.95rem;color:#f0f2f8;'>"
            f"{st.session_state['user']}</div>"
            f"<div style='display:inline-block;background:{role_color}22;"
            f"color:{role_color};border:1px solid {role_color}44;"
            f"border-radius:999px;padding:1px 10px;font-size:0.7rem;font-weight:600;"
            f"margin-top:6px;'>{role.capitalize()}</div>"
            f"</div>",
            unsafe_allow_html=True
        )
        if st.button("Sign Out", key="signout_btn", use_container_width=True):
            st.session_state.update({
                "user": None, "role": "student",
                "show_welcome": False, "auth_mode": "login",
            })
            st.rerun()

        st.markdown("<hr style='border-color:#2a2f42;margin:1.2rem 0;'>", unsafe_allow_html=True)
        st.markdown(
            "<p style='font-size:0.72rem;color:#555e7a;line-height:1.6;'>"
            "Ask questions outside class hours · Share code &amp; errors · "
            "Get peer and instructor-verified answers</p>",
            unsafe_allow_html=True
        )


# ================================================================
#  BOOT — show auth page or main app
# ================================================================
if not st.session_state["user"]:
    show_auth_page()
    st.stop()

# Logged in from here down
render_sidebar()

if st.session_state.pop("show_welcome", False):
    st.success(f"👋 Welcome, **{st.session_state['user']}**! Ready to ask or help someone out?")

questions_df = read_questions_df()
answers_df   = read_answers_df()

current_user = st.session_state["user"]
current_role = st.session_state.get("role", "student")
is_admin     = current_role in ADMIN_ROLES


# ================================================================
#  HERO
# ================================================================
role_color = "#4f7cff" if is_admin else "#555e7a"
st.markdown(
    f"""<div class='asksqi-hero'>
        <h1>💬 AskSQI</h1>
        <p>A safe, inclusive space for questions across all courses and levels.</p>
        <div class='user-pill'>👤 <span>{current_user}</span>&nbsp;·&nbsp;{current_role.capitalize()}</div>
    </div>""",
    unsafe_allow_html=True
)


# ================================================================
#  TABS
# ================================================================
if is_admin:
    tab_browse, tab_ask, tab_mine, tab_stats = st.tabs(
        ["📚  Browse", "✍🏽  Ask", "🙋  My Questions", "📊  Dashboard"]
    )
else:
    tab_browse, tab_ask, tab_mine = st.tabs(
        ["📚  Browse", "✍🏽  Ask", "🙋  My Questions"]
    )
    tab_stats = None


# ================================================================
#  SHARED HELPERS
# ================================================================
def question_status(q_id, a_df):
    if a_df.empty:
        return "unanswered"
    rel = a_df[a_df["question_id"] == q_id]
    if rel.empty:
        return "unanswered"
    if rel["verified"].any():
        return "verified"
    return "answered"

STATUS_HTML = {
    "unanswered": "<span class='badge badge-red'>⬤ Unanswered</span>",
    "answered":   "<span class='badge badge-amber'>⬤ Answered</span>",
    "verified":   "<span class='badge badge-green'>⬤ Verified</span>",
}


# ================================================================
#  RENDERER
# ================================================================
def render_questions(q_subset: pd.DataFrame, a_df: pd.DataFrame,
                     allow_delete_q: bool = False, ns: str = ""):
    if q_subset.empty:
        st.markdown(
            "<div style='text-align:center;padding:2.5rem 1rem;color:#555e7a;font-size:0.9rem;'>"
            "No questions to show yet.</div>",
            unsafe_allow_html=True
        )
        return

    for _, q in q_subset.sort_values("id", ascending=False).iterrows():
        q_id   = int(pd.to_numeric(q.get("id", 0), errors="coerce") or 0)
        author = q.get("author", "Unknown")
        rel    = a_df[a_df["question_id"] == q_id] if not a_df.empty else pd.DataFrame()
        n_ans  = len(rel)
        status = question_status(q_id, a_df)

        expander_label = (
            f"{q.get('title', '(No title)')}  ·  {q.get('course', '?')}  ·  "
            f"Lv {q.get('level', 1)}  ·  "
            f"{'✅' if status=='verified' else '🟡' if status=='answered' else '🔴'}  ·  "
            f"👤 {author}  ·  💬 {n_ans}"
        )

        with st.expander(expander_label):
            st.markdown(
                f"<div class='q-card-meta' style='margin-bottom:0.8rem;'>"
                f"{STATUS_HTML[status]}"
                f"<span class='badge badge-blue'>{q.get('course','?')}</span>"
                f"<span class='badge badge-muted'>Level {q.get('level',1)}</span>"
                f"<span class='badge badge-muted'>💬 {n_ans} answer{'s' if n_ans!=1 else ''}</span>"
                f"<span class='badge badge-muted'>👤 {author}</span>"
                f"<span style='color:#555e7a;font-size:0.72rem;margin-left:auto;'>🕐 {q.get('created_at','')}</span>"
                f"</div>",
                unsafe_allow_html=True
            )
            st.markdown(
                f"<div style='color:#c8cce0;font-size:0.93rem;line-height:1.7;"
                f"padding:0.75rem 0;border-top:1px solid #2a2f42;'>{q.get('description','')}</div>",
                unsafe_allow_html=True
            )

            err = q.get("error_message", "")
            if isinstance(err, str) and err.strip():
                st.markdown("<div class='section-label'>🧯 Error Message</div>", unsafe_allow_html=True)
                st.code(err, language="text")

            snippet = q.get("code", "")
            if isinstance(snippet, str) and snippet.strip():
                st.markdown("<div class='section-label'>🧩 Code Snippet</div>", unsafe_allow_html=True)
                st.code(snippet, language="python")

            if allow_delete_q and (is_admin or author == current_user):
                st.markdown("<div class='danger-btn'>", unsafe_allow_html=True)
                if st.button("🗑️ Delete question", key=f"{ns}del_q_{q_id}",
                             help="Deletes this question and all its answers"):
                    delete_question(q_id)
                    st.warning("Question deleted.")
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

            st.markdown("<div class='section-label'>💡 Answers</div>", unsafe_allow_html=True)

            if rel.empty:
                st.markdown(
                    "<div style='color:#555e7a;font-size:0.85rem;padding:0.4rem 0;'>"
                    "No answers yet — be the first to help!</div>",
                    unsafe_allow_html=True
                )
            else:
                for _, a in rel.sort_values("verified", ascending=False).iterrows():
                    a_id      = int(pd.to_numeric(a.get("id", 0), errors="coerce") or 0)
                    responder = a.get("responder", "Unknown")
                    is_ver    = bool(a.get("verified", False))
                    card_cls  = "answer-card verified" if is_ver else "answer-card"
                    badge_html = (
                        "<span class='badge badge-green'>✅ Instructor Verified</span>"
                        if is_ver else
                        "<span class='badge badge-muted'>👤 Peer Answer</span>"
                    )
                    col_ans, col_del = st.columns([11, 1])
                    with col_ans:
                        st.markdown(
                            f"<div class='{card_cls}'>"
                            f"<div style='margin-bottom:0.4rem;'>{badge_html}</div>"
                            f"<div class='answer-text'>{a.get('answer','')}</div>"
                            f"<div class='answer-meta'>— {responder} · {a.get('created_at','')}</div>"
                            f"</div>",
                            unsafe_allow_html=True
                        )
                    with col_del:
                        if is_admin or responder == current_user:
                            st.markdown("<div class='danger-btn'>", unsafe_allow_html=True)
                            if st.button("🗑️", key=f"{ns}del_a_{a_id}", help="Delete answer"):
                                delete_answer(a_id)
                                st.warning("Answer deleted.")
                                st.rerun()
                            st.markdown("</div>", unsafe_allow_html=True)

            already_answered = (
                not rel.empty and current_user in rel["responder"].astype(str).values
            )
            if already_answered and not is_admin:
                st.markdown(
                    "<div style='background:#1e2333;border:1px solid #2a2f42;border-radius:8px;"
                    "padding:0.65rem 1rem;color:#8b93b0;font-size:0.83rem;margin-top:0.5rem;'>"
                    "✏️ You've already answered this question.</div>",
                    unsafe_allow_html=True
                )
            else:
                st.markdown("<div class='section-label'>✍🏽 Add an Answer</div>", unsafe_allow_html=True)
                with st.form(f"{ns}answer_form_{q_id}"):
                    answer_text = st.text_area(
                        "Your answer", key=f"{ns}answer_{q_id}",
                        placeholder="Write a clear, helpful answer…",
                        height=120, label_visibility="collapsed"
                    )
                    verified = (
                        st.checkbox("✅ Mark as Instructor Verified", key=f"{ns}verify_{q_id}")
                        if is_admin else False
                    )
                    if st.form_submit_button("Post Answer →"):
                        if not answer_text.strip():
                            st.error("Please write an answer before posting.")
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
#  TAB — ASK
# ================================================================
with tab_ask:
    st.markdown(
        "<h3 style='font-family:Fraunces,serif;font-size:1.4rem;font-weight:700;"
        "color:#f0f2f8;margin-bottom:0.5rem;'>✍🏽 Ask a Question</h3>"
        "<p style='color:#8b93b0;font-size:0.875rem;margin-bottom:1.2rem;line-height:1.6;'>"
        "Be specific — describe what you expected, what happened, and include any "
        "relevant code or error messages.</p>",
        unsafe_allow_html=True
    )
    with st.form("ask_question_form"):
        title = st.text_input("Question Title",
                               placeholder="e.g. Why does my loop skip the last element?")
        col_c, col_l = st.columns(2)
        with col_c:
            course = st.selectbox("Course", COURSES)
        with col_l:
            level = st.selectbox("Level", LEVELS, index=0)
        description = st.text_area("Describe your problem",
            placeholder="What did you expect? What happened? What have you tried?", height=140)
        code = st.text_area("Code Snippet (optional)", height=140,
                             placeholder="Paste relevant code here…")
        error_message = st.text_area("Error Message (optional)", height=90,
                                      placeholder="Paste the exact error message here…")
        submitted = st.form_submit_button("Submit Question →", use_container_width=True)

    if submitted:
        if not title.strip() or not description.strip():
            st.error("A title and description are required.")
        else:
            questions_ws = open_db().worksheet(QUESTIONS_SHEET)
            append_row(questions_ws, [
                next_id(questions_df, "id"),
                title.strip(), description.strip(), course, level,
                code.strip(), error_message.strip(),
                current_user, datetime.now().strftime("%Y-%m-%d %H:%M"),
            ])
            read_questions_df.clear()
            st.success("✅ Question submitted! Switch to Browse to see it.")
            st.rerun()


# ================================================================
#  TAB — BROWSE
# ================================================================
with tab_browse:
    _, questions_df, answers_df = refresh_data()

    st.markdown("<div class='filter-bar'>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([3, 2, 1])
    with col1:
        search_query = st.text_input("search", placeholder="🔍  Search by keyword…",
                                      label_visibility="collapsed")
    with col2:
        filter_course = st.selectbox("course", ["All Courses"] + COURSES,
                                      label_visibility="collapsed")
    with col3:
        filter_level = st.selectbox("level", ["All Lvl"] + [str(l) for l in LEVELS],
                                     label_visibility="collapsed")
    st.markdown("</div>", unsafe_allow_html=True)

    filter_status = st.radio(
        "filter_status", ["All", "🔴 Unanswered", "🟡 Answered", "✅ Verified"],
        horizontal=True, label_visibility="collapsed"
    )

    filtered = questions_df.copy() if not questions_df.empty else pd.DataFrame()
    if not filtered.empty:
        if filter_course != "All Courses":
            filtered = filtered[filtered["course"] == filter_course]
        if filter_level != "All Lvl":
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
            if filter_status != "🔴 Unanswered":
                filtered = pd.DataFrame()

    st.markdown(
        f"<div style='color:#555e7a;font-size:0.78rem;margin-bottom:0.8rem;'>"
        f"{len(filtered)} question{'s' if len(filtered) != 1 else ''} found</div>",
        unsafe_allow_html=True
    )
    render_questions(filtered, answers_df, allow_delete_q=True, ns="browse_")


# ================================================================
#  TAB — MY QUESTIONS
# ================================================================
with tab_mine:
    _, questions_df, answers_df = refresh_data()
    my_q = (
        questions_df[questions_df["author"] == current_user]
        if not questions_df.empty else pd.DataFrame()
    )
    st.markdown(
        f"<h3 style='font-family:Fraunces,serif;font-size:1.3rem;font-weight:700;"
        f"color:#f0f2f8;margin-bottom:0.3rem;'>🙋 My Questions</h3>"
        f"<p style='color:#555e7a;font-size:0.78rem;margin-bottom:1rem;'>"
        f"{len(my_q)} question{'s' if len(my_q) != 1 else ''} asked by you</p>",
        unsafe_allow_html=True
    )
    render_questions(my_q, answers_df, allow_delete_q=True, ns="mine_")


# ================================================================
#  TAB — DASHBOARD
# ================================================================
if tab_stats is not None:
    with tab_stats:
        _, questions_df, answers_df = refresh_data()
        st.markdown(
            "<h3 style='font-family:Fraunces,serif;font-size:1.3rem;font-weight:700;"
            "color:#f0f2f8;margin-bottom:1.2rem;'>📊 Platform Dashboard</h3>",
            unsafe_allow_html=True
        )

        if questions_df.empty:
            st.info("No data yet — questions will appear here once students start asking.")
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
            c1.metric("Total Questions",     total_q)
            c2.metric("Total Answers",       total_a)
            c3.metric("Unanswered",          unanswered,
                      delta=f"{round(unanswered/total_q*100)}% need help" if total_q else None,
                      delta_color="inverse")
            c4.metric("Instructor Verified", verified_q)

            st.markdown("<hr>", unsafe_allow_html=True)
            col_l, col_r = st.columns(2)
            with col_l:
                st.markdown(
                    "<div style='font-size:0.75rem;text-transform:uppercase;letter-spacing:0.08em;"
                    "color:#555e7a;font-weight:700;margin-bottom:0.6rem;'>Questions per Course</div>",
                    unsafe_allow_html=True
                )
                course_counts = questions_df["course"].value_counts().rename_axis("Course").reset_index(name="Questions")
                st.bar_chart(course_counts.set_index("Course"), color="#4f7cff")
            with col_r:
                st.markdown(
                    "<div style='font-size:0.75rem;text-transform:uppercase;letter-spacing:0.08em;"
                    "color:#555e7a;font-weight:700;margin-bottom:0.6rem;'>Questions per Level</div>",
                    unsafe_allow_html=True
                )
                level_counts = questions_df["level"].value_counts().sort_index().rename_axis("Level").reset_index(name="Questions")
                st.bar_chart(level_counts.set_index("Level"), color="#22c55e")

            st.markdown("<hr>", unsafe_allow_html=True)
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown(
                    "<div style='font-size:0.75rem;text-transform:uppercase;letter-spacing:0.08em;"
                    "color:#555e7a;font-weight:700;margin-bottom:0.6rem;'>Most Active Students</div>",
                    unsafe_allow_html=True
                )
                top_askers = questions_df["author"].value_counts().head(10).rename_axis("Student").reset_index(name="Questions Asked")
                st.dataframe(top_askers, use_container_width=True, hide_index=True)
            with col_b:
                st.markdown(
                    "<div style='font-size:0.75rem;text-transform:uppercase;letter-spacing:0.08em;"
                    "color:#555e7a;font-weight:700;margin-bottom:0.6rem;'>Most Helpful Peers</div>",
                    unsafe_allow_html=True
                )
                if not answers_df.empty:
                    top_helpers = answers_df["responder"].value_counts().head(10).rename_axis("Student").reset_index(name="Answers Given")
                    st.dataframe(top_helpers, use_container_width=True, hide_index=True)
                else:
                    st.markdown("<div style='color:#555e7a;font-size:0.85rem;'>No answers yet.</div>",
                                unsafe_allow_html=True)