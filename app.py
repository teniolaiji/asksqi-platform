import streamlit as st
import pandas as pd
from datetime import datetime
import os

# ---------------- CONFIG ----------------
st.set_page_config(page_title="AskSQI", layout="centered")

QUESTIONS_FILE = "questions.csv"
ANSWERS_FILE = "answers.csv"

COURSES = [
    "Software Engineering",
    "Product Management",
    "Web Design",
    "Cyber Security",
    "Java Programming",
    "Data Science",
    "Data Analysis",
    "Robotics Engineering",
    "Artificial Intelligence (AI)",
    "Networking",
    "Accounting Applications",
    "Hardware Engineering",
]

LEVELS = [1, 2, 3, 4, 5, 6]

# ---------------- DATA SETUP ----------------
if not os.path.exists(QUESTIONS_FILE):
    pd.DataFrame(columns=[
        "id", "title", "description", "course", "level",
        "code", "error_message", "timestamp"
    ]).to_csv(QUESTIONS_FILE, index=False)

if not os.path.exists(ANSWERS_FILE):
    pd.DataFrame(columns=[
        "question_id", "answer", "responder", "verified", "timestamp"
    ]).to_csv(ANSWERS_FILE, index=False)

questions_df = pd.read_csv(QUESTIONS_FILE)
answers_df = pd.read_csv(ANSWERS_FILE)

# ---------------- MIGRATION FOR OLD CSV ----------------
# If you had old questions before adding course/level/error_message,
# this makes sure the new columns exist so the app doesn't crash.

required_cols = ["id", "title", "description", "course", "level", "code", "error_message", "timestamp"]

# Add missing columns with safe defaults
for col in required_cols:
    if col not in questions_df.columns:
        if col == "course":
            questions_df[col] = "Software Engineering"  # default course
        elif col == "level":
            questions_df[col] = 1  # default level
        else:
            questions_df[col] = ""

# If older data used "category", try to carry it over into "course"
if "category" in questions_df.columns:
    # Only fill course where it's blank
    questions_df["course"] = questions_df["course"].replace("", pd.NA)
    questions_df["course"] = questions_df["course"].fillna(questions_df["category"].astype(str))
    # Optional: drop the old column to avoid confusion
    questions_df = questions_df.drop(columns=["category"])

# Ensure level is numeric and valid (1–6)
questions_df["level"] = pd.to_numeric(questions_df["level"], errors="coerce").fillna(1).astype(int)
questions_df["level"] = questions_df["level"].clip(1, 6)

# Save the migrated data so next load is clean
questions_df.to_csv(QUESTIONS_FILE, index=False)

# ---------------- HEADER ----------------
st.title("💬 AskSQI")
st.subheader("A safe, inclusive space for asking and answering questions across all courses")

st.markdown(
    """
Ask questions outside class hours, share code and error messages when needed,
and receive peer support with instructor-reviewed guidance when available.
"""
)

# ---------------- ASK QUESTION ----------------
st.markdown("## ✍🏽 Ask a Question")

with st.form("ask_question_form"):
    title = st.text_input("Question Title", placeholder="Example: Why is my code returning NaN?")
    course = st.selectbox("Course", COURSES)
    level = st.selectbox("Level", LEVELS, index=0)

    description = st.text_area("Describe your problem", placeholder="Explain what you expected vs what you got.")
    code = st.text_area("Code Snippet (optional)", height=150, placeholder="Paste your code here (if relevant).")

    error_message = st.text_area(
        "Error Message (optional)",
        height=100,
        placeholder="Paste the error message exactly as it appears (if any)."
    )

    submitted = st.form_submit_button("Submit Question")

    if submitted:
        if title.strip() == "" or description.strip() == "":
            st.error("Please provide a title and a description.")
        else:
            new_question = {
                "id": int(questions_df["id"].max() + 1) if not questions_df.empty else 1,
                "title": title.strip(),
                "description": description.strip(),
                "course": course,
                "level": level,
                "code": code.strip(),
                "error_message": error_message.strip(),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
            }

            questions_df = pd.concat([questions_df, pd.DataFrame([new_question])], ignore_index=True)
            questions_df.to_csv(QUESTIONS_FILE, index=False)
            st.success("Question submitted successfully!")

# ---------------- VIEW QUESTIONS ----------------
st.markdown("## 📚 Questions & Answers")

for _, q in questions_df.sort_values("id", ascending=False).iterrows():
    header = f"{q.get('title','(No title)')}  •  {q.get('course','Unknown Course')}  •  Level {q.get('level',1)}"
    with st.expander(header):
        st.write(q["description"])

        if isinstance(q.get("error_message", ""), str) and q["error_message"].strip():
            st.markdown("### 🧯 Error Message")
            st.code(q["error_message"], language="text")

        if isinstance(q.get("code", ""), str) and q["code"].strip():
            st.markdown("### 🧩 Code Snippet")
            st.code(q["code"], language="python")

        related_answers = answers_df[answers_df["question_id"] == q["id"]]

        st.markdown("### 💡 Answers")
        if related_answers.empty:
            st.info("No answers yet. Be the first to help!")
        else:
            for _, a in related_answers.iterrows():
                badge = "✅ Instructor Verified" if bool(a["verified"]) else "👤 Peer Answer"
                st.markdown(f"**{badge}**")
                st.write(a["answer"])
                st.caption(f"— {a['responder']} | {a['timestamp']}")

        # ---------------- ADD ANSWER ----------------
        with st.form(f"answer_form_{q['id']}"):
            answer = st.text_area("Your Answer", key=f"answer_{q['id']}")
            responder = st.text_input("Your Name", key=f"name_{q['id']}")
            verified = st.checkbox("Instructor Verified", key=f"verified_{q['id']}")
            submit_answer = st.form_submit_button("Post Answer")

            if submit_answer:
                if answer.strip() == "" or responder.strip() == "":
                    st.error("Please enter your name and answer.")
                else:
                    new_answer = {
                        "question_id": q["id"],
                        "answer": answer.strip(),
                        "responder": responder.strip(),
                        "verified": bool(verified),
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
                    }
                    answers_df = pd.concat([answers_df, pd.DataFrame([new_answer])], ignore_index=True)
                    answers_df.to_csv(ANSWERS_FILE, index=False)
                    st.success("Answer posted successfully!")