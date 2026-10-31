"""AI Placement Coach engine."""
import json
import re
from datetime import datetime
from groq import Groq

MODEL = "openai/gpt-oss-20b"
client = Groq(api_key=__import__("os").environ["GROQ_API_KEY"])

def ask_ai(system_prompt, user_prompt, max_tokens=5000):
    """Generate structured JSON responses using Groq."""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.2,
        max_completion_tokens=max_tokens,
        reasoning_effort="low",
        include_reasoning=False,
        response_format={"type": "json_object"}
    )

    choice = response.choices[0]

    if choice.finish_reason == "length":
        raise RuntimeError(
            "AI response reached its token limit. "
            "Please reduce the input or increase the output limit."
        )

    result = choice.message.content

    if not result or not result.strip():
        raise ValueError("Groq returned an empty response.")

    return result.strip()


def extract_json(text):
    """Parse JSON even if the model wraps it in a code block."""
    cleaned = re.sub(r"^\s*```(?:json)?\s*", "", text)
    cleaned = re.sub(r"\s*```\s*$", "", cleaned)
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("The AI response did not contain valid JSON.")
    return json.loads(cleaned[start:end + 1])


def analyze_candidate(resume_text, job_description):
    """Compare candidate evidence against job requirements."""
    if not resume_text.strip() or not job_description.strip():
        raise ValueError("Resume and job description are both required.")

    prompt = f"""
Analyze this candidate for the target job. Use only the supplied evidence.
Do not invent experience, qualifications, or skills.

RESUME:
{resume_text[:12000]}

JOB DESCRIPTION:
{job_description[:8000]}

Return JSON with these keys:
role, candidate_summary, matched_skills, missing_skills,
partial_matches, strengths, improvement_areas, recommendations.
Use arrays of concise strings for the list fields. Identify uncertainty
when the resume does not provide enough evidence.
"""
    return extract_json(ask_ai(
        "You are a careful technical recruitment and skills-analysis assistant. "
        "Return valid JSON only.",
        prompt
    ))



def create_study_plan(analysis, hours_per_day=2, days=7):
    """Generate a concise, structured preparation plan."""

    if not 1 <= hours_per_day <= 12 or not 1 <= days <= 60:
        raise ValueError("Use 1–12 study hours and 1–60 days.")

    prompt = f"""
Create a practical placement preparation plan.

Duration: {days} days.
Available study time: {hours_per_day} hours daily.

Candidate analysis:
{json.dumps(analysis, ensure_ascii=False)[:7000]}

Return one valid JSON object with these keys:
goal: short string
daily_plan: array of objects containing:
day, topics (array), activities (array), practice_task (string),
estimated_hours (number).
revision_strategy: short string
milestones: array of short strings

IMPORTANT:
- Include exactly {days} daily entries.
- Keep each day's content concise.
- Prioritize missing skills and job requirements.
- Include coding practice, revision and mock interviews.
- Make daily activities fit the available study hours.
- Do not use Markdown or text outside the JSON object.
"""

    result = extract_json(ask_ai(
        "You are an expert placement preparation coach. "
        "Return a complete, valid JSON object only.",
        prompt,
        max_tokens=3500
    ))

    if not isinstance(result.get("daily_plan"), list):
        raise ValueError("The AI did not return a valid daily plan.")

    if len(result["daily_plan"]) != days:
        raise ValueError(
            f"Expected {days} study days, received "
            f"{len(result['daily_plan'])}."
        )

    return result


def generate_interview_question(job_description, history=None,
                                difficulty="Beginner", question_number=1):
    """Generate a question adapted to prior answers."""
    history = history or []

    prompt = f"""
Target job:
{job_description[:6000]}

Interview question number: {question_number}
Requested difficulty: {difficulty}

Previous interview history:
{json.dumps(history[-8:], ensure_ascii=False)}

Return JSON with:
question, topic, difficulty, evaluation_criteria (array of strings),
reason_for_selection.

Ask one question only. Cover relevant technical and job-specific topics.
Use earlier answers to choose a useful next question. Increase difficulty
after consistently strong answers; simplify or revisit a topic after weak
answers. Do not repeat previous questions unnecessarily.
"""
    return extract_json(ask_ai(
        "You are an adaptive technical interviewer. Return valid JSON only.",
        prompt,
        max_tokens=900
    ))


def evaluate_interview_answer(question, answer, criteria=None):
    """Score an answer and return actionable feedback."""
    if not answer.strip():
        raise ValueError("Submit an answer before requesting evaluation.")

    prompt = f"""
Question: {question}
Candidate answer: {answer[:6000]}
Evaluation criteria: {json.dumps(criteria or [], ensure_ascii=False)}

Assess technical correctness, completeness, reasoning, and clarity.
Do not reward keywords alone. Do not claim that unverified statements
are correct. Be constructive and distinguish factual errors from omissions.

Return JSON with:
score (integer 0–100), correctness, strengths (array),
missing_concepts (array), feedback, ideal_answer,
recommended_difficulty (Beginner, Intermediate, or Advanced),
topic_mastery (integer 0–100).
"""
    result = extract_json(ask_ai(
        "You are a fair technical interviewer and evaluator. "
        "Return valid JSON only.",
        prompt
    ))

    score = result.get("score")
    mastery = result.get("topic_mastery")
    if not isinstance(score, int) or not 0 <= score <= 100:
        raise ValueError("Invalid score returned by the AI.")
    if not isinstance(mastery, int) or not 0 <= mastery <= 100:
        raise ValueError("Invalid topic mastery score returned by the AI.")
    return result


def build_final_report(candidate_name, job_title, history):
    """Summarize completed interview answers and next steps."""
    if not history:
        raise ValueError("Complete at least one interview question first.")

    prompt = f"""
Candidate: {candidate_name}
Target role: {job_title}
Interview history:
{json.dumps(history, ensure_ascii=False)[:14000]}

Return JSON with:
overall_score (integer 0–100), strengths (array),
weak_topics (array), recommended_practice (array),
next_steps (array), summary.
Base conclusions on the supplied results. Do not invent scores or
claim that this report predicts whether a company will hire the candidate.
"""
    report = extract_json(ask_ai(
        "You are a placement coach preparing an evidence-based final report. "
        "Return valid JSON only.",
        prompt
    ))

    score = report.get("overall_score")
    if not isinstance(score, int) or not 0 <= score <= 100:
        raise ValueError("Invalid overall score returned by the AI.")
    report["generated_at"] = datetime.now().isoformat(timespec="minutes")
    return report


