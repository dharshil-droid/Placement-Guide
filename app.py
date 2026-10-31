import os
import json
import streamlit as st

# Reuse the agent functions created in the earlier Colab cells.
# The deployed app imports them from agent_engine.py.
from agent_engine import (
    analyze_candidate,
    create_study_plan,
    generate_interview_question,
    evaluate_interview_answer,
    build_final_report,
)

st.set_page_config(
    page_title="AI Placement Coach",
    page_icon="🎯",
    layout="wide",
)

st.title("🎯 AI Placement Coach")
st.caption(
    "Your personalized placement preparation and adaptive interview assistant"
)

with st.sidebar:
    st.header("Your preparation")
    candidate_name = st.text_input("Your name", value="Candidate")
    hours_per_day = st.slider("Study hours per day", 1, 8, 2)
    plan_days = st.slider("Preparation plan duration (days)", 3, 30, 7)

    st.divider()
    st.info(
        "Upload your resume and add the target job description to begin."
    )

if "analysis" not in st.session_state:
    st.session_state.analysis = None
if "study_plan" not in st.session_state:
    st.session_state.study_plan = None
if "job_description" not in st.session_state:
    st.session_state.job_description = ""
if "interview_history" not in st.session_state:
    st.session_state.interview_history = []
if "current_question" not in st.session_state:
    st.session_state.current_question = None
if "final_report" not in st.session_state:
    st.session_state.final_report = None

tab1, tab2, tab3, tab4 = st.tabs([
    "📄 Resume Analysis",
    "📚 Study Plan",
    "🎤 Mock Interview",
    "📊 Performance Report",
])

with tab1:
    st.subheader("Resume and job analysis")

    uploaded_resume = st.file_uploader(
        "Upload your resume (PDF or TXT)",
        type=["pdf", "txt"],
        key="resume_upload",
    )
    job_description = st.text_area(
        "Paste the complete job description",
        value=st.session_state.job_description,
        height=220,
        placeholder="Paste the target role and its requirements...",
    )

    if st.button("Analyze my profile", type="primary"):
        if uploaded_resume is None:
            st.error("Please upload a PDF or TXT resume.")
        elif not job_description.strip():
            st.error("Please enter a job description.")
        else:
            try:
                if uploaded_resume.size > 5 * 1024 * 1024:
                    raise ValueError("Resume must be smaller than 5 MB.")

                if uploaded_resume.type == "application/pdf":
                    import fitz
                    pdf = fitz.open(
                        stream=uploaded_resume.getvalue(),
                        filetype="pdf",
                    )
                    resume_text = "\n".join(
                        page.get_text() for page in pdf
                    )
                    pdf.close()
                else:
                    resume_text = uploaded_resume.getvalue().decode(
                        "utf-8", errors="replace"
                    )

                if not resume_text.strip():
                    raise ValueError(
                        "No readable text found. Try a text-based PDF."
                    )

                with st.spinner("Analyzing your resume and job requirements..."):
                    analysis = analyze_candidate(
                        resume_text, job_description
                    )

                st.session_state.analysis = analysis
                st.session_state.job_description = job_description
                st.session_state.study_plan = None
                st.session_state.interview_history = []
                st.session_state.current_question = None
                st.session_state.final_report = None
                st.success("Analysis completed!")
            except Exception as e:
                st.error(f"Analysis failed: {e}")

    if st.session_state.analysis:
        a = st.session_state.analysis

        st.markdown("### Candidate analysis")
        st.write(a.get("candidate_summary", "No summary available."))

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Matched skills**")
            st.write(a.get("matched_skills", []))
            st.markdown("**Strengths**")
            st.write(a.get("strengths", []))
        with c2:
            st.markdown("**Missing skills**")
            st.write(a.get("missing_skills", []))
            st.markdown("**Partial matches**")
            st.write(a.get("partial_matches", []))

        st.markdown("**Recommended improvements**")
        st.write(a.get("improvement_areas", []))
        st.write(a.get("recommendations", []))

with tab2:
    st.subheader("Personalized preparation plan")

    if not st.session_state.analysis:
        st.info("Complete Resume Analysis first.")
    elif st.button("Generate my study plan", type="primary"):
        try:
            with st.spinner("Building your preparation roadmap..."):
                st.session_state.study_plan = create_study_plan(
                    st.session_state.analysis,
                    hours_per_day=hours_per_day,
                    days=plan_days,
                )
        except Exception as e:
            st.error(f"Could not generate the study plan: {e}")

    plan = st.session_state.study_plan
    if plan:
        st.markdown("### Your roadmap")
        st.write(plan.get("goal", ""))
        daily_plan = plan.get("daily_plan", [])

        for day in daily_plan:
            with st.expander(
                f"Day {day.get('day', '?')} — "
                f"{', '.join(day.get('topics', []))}"
            ):
                st.write("Activities:", day.get("activities", []))
                st.write("Practice task:", day.get("practice_task", ""))
                st.write("Estimated hours:", day.get("estimated_hours", ""))

        st.markdown("**Revision strategy**")
        st.write(plan.get("revision_strategy", ""))
        st.write("**Milestones:**", plan.get("milestones", []))

        st.download_button(
            "Download study plan (JSON)",
            data=json.dumps(plan, indent=2, ensure_ascii=False),
            file_name="placement_study_plan.json",
            mime="application/json",
        )

with tab3:
    st.subheader("Adaptive technical mock interview")

    if not st.session_state.analysis:
        st.info("Analyze your resume and job description first.")
    else:
        history = st.session_state.interview_history
        st.write(f"Questions completed: {len(history)} / 10")

        if len(history) < 10:
            if st.session_state.current_question is None:
                difficulty = (
                    history[-1]["evaluation"].get(
                        "recommended_difficulty", "Beginner"
                    )
                    if history else "Beginner"
                )

                if st.button("Generate next question", type="primary"):
                    try:
                        with st.spinner("Selecting your next question..."):
                            st.session_state.current_question = (
                                generate_interview_question(
                                    st.session_state.job_description,
                                    history=history,
                                    difficulty=difficulty,
                                    question_number=len(history) + 1,
                                )
                            )
                        st.rerun()
                    except Exception as e:
                        st.error(f"Question generation failed: {e}")

            q = st.session_state.current_question
            if q:
                st.markdown(f"### Question {len(history) + 1}")
                st.write(q.get("question", ""))
                st.caption(
                    f"Topic: {q.get('topic', 'General')} | "
                    f"Difficulty: {q.get('difficulty', 'Not specified')}"
                )

                answer = st.text_area(
                    "Your answer",
                    key=f"answer_{len(history)}",
                    height=160,
                    placeholder="Explain your answer in your own words...",
                )

                if st.button("Submit answer and get feedback", type="primary"):
                    if not answer.strip():
                        st.warning("Please enter your answer first.")
                    else:
                        try:
                            with st.spinner("Evaluating your answer..."):
                                evaluation = evaluate_interview_answer(
                                    q["question"],
                                    answer,
                                    q.get("evaluation_criteria", []),
                                )

                            history.append({
                                "question": q["question"],
                                "topic": q.get("topic", "General"),
                                "difficulty": q.get("difficulty", "Unknown"),
                                "answer": answer,
                                "evaluation": evaluation,
                            })
                            st.session_state.interview_history = history
                            st.session_state.current_question = None
                            st.session_state.final_report = None
                            st.rerun()
                        except Exception as e:
                            st.error(f"Answer evaluation failed: {e}")

        else:
            st.success("You've completed all 10 interview questions!")

        if history:
            st.markdown("### Previous answers")
            for i, item in enumerate(history, 1):
                ev = item["evaluation"]
                with st.expander(
                    f"Q{i}: {item['question']} — "
                    f"Score: {ev.get('score', 'N/A')}/100"
                ):
                    st.write("Your answer:", item["answer"])
                    st.write("Feedback:", ev.get("feedback", ""))
                    st.write("Strengths:", ev.get("strengths", []))
                    st.write(
                        "Missing concepts:", ev.get("missing_concepts", [])
                    )
                    st.write("Suggested answer:", ev.get("ideal_answer", ""))

with tab4:
    st.subheader("Interview performance")

    history = st.session_state.interview_history
    if not history:
        st.info("Complete at least one mock interview question first.")
    else:
        scores = [
            item["evaluation"]["score"] for item in history
        ]
        average = sum(scores) / len(scores)

        c1, c2, c3 = st.columns(3)
        c1.metric("Questions completed", len(history))
        c2.metric("Average score", f"{average:.1f}/100")
        c3.metric(
            "Strong answers",
            sum(score >= 75 for score in scores),
        )

        st.bar_chart({
            f"Question {i}": item["evaluation"]["score"]
            for i, item in enumerate(history, 1)
        })

        if st.button("Generate final coaching report", type="primary"):
            try:
                with st.spinner("Preparing your final report..."):
                    st.session_state.final_report = build_final_report(
                        candidate_name,
                        st.session_state.analysis.get("role", "Target role"),
                        history,
                    )
            except Exception as e:
                st.error(f"Report generation failed: {e}")

        if st.session_state.final_report:
            report = st.session_state.final_report
            st.markdown("### Your coaching report")
            st.metric(
                "Overall score",
                f"{report.get('overall_score', 'N/A')}/100",
            )
            st.write(report.get("summary", ""))
            st.write("**Strengths:**", report.get("strengths", []))
            st.write("**Weak topics:**", report.get("weak_topics", []))
            st.write("**Practice next:**", report.get("recommended_practice", []))
            st.write("**Next steps:**", report.get("next_steps", []))

            st.download_button(
                "Download final report (JSON)",
                data=json.dumps(report, indent=2, ensure_ascii=False),
                file_name="placement_coaching_report.json",
                mime="application/json",
            )

st.divider()
st.caption(
    "AI-generated guidance is for practice. Review important technical "
    "feedback and protect personal information in uploaded resumes."
)
