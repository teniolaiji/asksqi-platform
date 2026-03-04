import streamlit as st
import pandas as pd
from datetime import datetime
import os

# ---------------- CONFIG ----------------
st.set_page_config(page_title="AskSQI", layout="centered")

QUESTIONS_FILE = "questions.csv"
ANSWERS_FILE = "answers.csv"

COURSES = [
    "Digital Workplace Proficiency",
    "Software Engineering",
    "Product Management",
    "Web Design",
    "Cyber Security",
    "Java Programming",
    "Data Science & Analysis",
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
    header = f"{q['title']}  •  {q['course']}  •  Level {q['level']}"
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