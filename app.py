import streamlit as st
import pandas as pd
from datetime import datetime
import os

# ---------------- CONFIG ----------------
st.set_page_config(page_title="AskSQI", layout="centered")

QUESTIONS_FILE = "questions.csv"
ANSWERS_FILE = "answers.csv"

# ---------------- DATA SETUP ----------------
if not os.path.exists(QUESTIONS_FILE):
    pd.DataFrame(columns=[
        "id", "title", "description", "code", "category", "timestamp"
    ]).to_csv(QUESTIONS_FILE, index=False)

if not os.path.exists(ANSWERS_FILE):
    pd.DataFrame(columns=[
        "question_id", "answer", "responder", "verified", "timestamp"
    ]).to_csv(ANSWERS_FILE, index=False)

questions_df = pd.read_csv(QUESTIONS_FILE)
answers_df = pd.read_csv(ANSWERS_FILE)

# ---------------- HEADER ----------------
st.title("💬 AskSQI")
st.subheader("A safe, inclusive space for asking and answering questions related to your course")

st.markdown(
    """
This platform allows students to ask questions outside class hours, 
share code snippets, and learn collaboratively through peer and instructor support.
"""
)

# ---------------- ASK QUESTION ----------------
st.markdown("## ✍🏽 Ask a Question")

with st.form("ask_question_form"):
    title = st.text_input("Question Title")
    description = st.text_area("Describe your problem")
    code = st.text_area("Code Snippet (optional)", height=150)
    category = st.selectbox("Category", ["Python", "NumPy", "Pandas", "Other"])
    submitted = st.form_submit_button("Submit Question")

    if submitted:
        if title.strip() == "" or description.strip() == "":
            st.error("Please provide a title and description.")
        else:
            new_question = {
                "id": len(questions_df) + 1,
                "title": title,
                "description": description,
                "code": code,
                "category": category,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
            }
            questions_df = pd.concat([questions_df, pd.DataFrame([new_question])])
            questions_df.to_csv(QUESTIONS_FILE, index=False)
            st.success("Question submitted successfully!")

# ---------------- VIEW QUESTIONS ----------------
st.markdown("## 📚 Questions & Answers")

for _, q in questions_df[::-1].iterrows():
    with st.expander(f"{q['title']}  •  {q['category']}"):
        st.write(q["description"])

        if q["code"]:
            st.code(q["code"], language="python")

        related_answers = answers_df[answers_df["question_id"] == q["id"]]

        st.markdown("### 💡 Answers")
        if related_answers.empty:
            st.info("No answers yet. Be the first to help!")
        else:
            for _, a in related_answers.iterrows():
                badge = "✅ Instructor Verified" if a["verified"] else "👤 Peer Answer"
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
                        "answer": answer,
                        "responder": responder,
                        "verified": verified,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
                    }
                    answers_df = pd.concat([answers_df, pd.DataFrame([new_answer])])
                    answers_df.to_csv(ANSWERS_FILE, index=False)
                    st.success("Answer posted successfully!")
