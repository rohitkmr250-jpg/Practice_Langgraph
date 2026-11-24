import streamlit as st
from typing import TypedDict
from langgraph.graph import StateGraph, START, END

# ------------------------------------------------------------------
# 1. STATE
# ------------------------------------------------------------------
class State(TypedDict, total=False):
    application: str
    experience_level: str
    skill_match: str
    response: str


# ------------------------------------------------------------------
# 2. NODES
# Replace the bodies below with YOUR original node logic (LLM calls etc.).
# Keep the node names and the returned state keys the same.
# ------------------------------------------------------------------
def categorize_experience(state: State) -> State:
    text = state["application"].lower()
    if any(w in text for w in ["senior", "lead", "8 years", "10 years", "manager"]):
        level = "Senior-level"
    elif any(w in text for w in ["3 years", "4 years", "5 years", "mid"]):
        level = "Mid-level"
    else:
        level = "Entry-level"
    return {"experience_level": level}


def assess_skillset(state: State) -> State:
    text = state["application"].lower()
    skills = ["python", "sql", "machine learning", "langchain", "streamlit", "aws"]
    hits = sum(1 for s in skills if s in text)
    match = "Match" if hits >= 3 else "No Match"
    return {"skill_match": match}


def schedule_hr_interview(state: State) -> State:
    return {"response": "Candidate shortlisted. HR interview will be scheduled."}


def escalate_to_recruiter(state: State) -> State:
    return {"response": "Candidate is senior-level but lacks skill match. Escalated to a recruiter."}


def reject_application(state: State) -> State:
    return {"response": "Application rejected. Skills do not match the requirements."}


def route_app(state: State) -> str:
    if state["skill_match"] == "Match":
        return "schedule_hr_interview"
    if state["experience_level"] == "Senior-level":
        return "escalate_to_recruiter"
    return "reject_application"


# ------------------------------------------------------------------
# 3. GRAPH
# ------------------------------------------------------------------
@st.cache_resource
def build_graph():
    workflow = StateGraph(State)

    workflow.add_node("categorize_experience", categorize_experience)
    workflow.add_node("assess_skillset", assess_skillset)
    workflow.add_node("schedule_hr_interview", schedule_hr_interview)
    workflow.add_node("escalate_to_recruiter", escalate_to_recruiter)
    workflow.add_node("reject_application", reject_application)

    workflow.add_edge(START, "categorize_experience")
    workflow.add_edge("categorize_experience", "assess_skillset")

    workflow.add_conditional_edges(
        "assess_skillset",
        route_app,
        {
            "schedule_hr_interview": "schedule_hr_interview",
            "escalate_to_recruiter": "escalate_to_recruiter",
            "reject_application": "reject_application",
        },
    )

    workflow.add_edge("schedule_hr_interview", END)
    workflow.add_edge("escalate_to_recruiter", END)
    workflow.add_edge("reject_application", END)

    return workflow.compile()


# ------------------------------------------------------------------
# 4. STREAMLIT UI
# ------------------------------------------------------------------
st.set_page_config(page_title="Hiring Workflow", page_icon="🧑‍💼", layout="wide")

st.title("🧑‍💼 AI Hiring Workflow")
st.caption("Categorize experience → assess skills → route the application")

app = build_graph()

with st.sidebar:
    st.header("About")
    st.write(
        "Paste a candidate's application. The workflow will categorize their "
        "experience, assess their skillset, then either schedule an HR interview, "
        "escalate to a recruiter, or reject."
    )
    show_graph = st.checkbox("Show workflow graph", value=False)

if show_graph:
    try:
        st.image(app.get_graph().draw_mermaid_png(), caption="Workflow graph")
    except Exception:
        st.code(app.get_graph().draw_mermaid(), language="mermaid")

col_in, col_out = st.columns(2)

with col_in:
    st.subheader("Candidate application")
    application = st.text_area(
        "Resume / application text",
        height=300,
        placeholder="e.g. Senior engineer with 8 years of experience in Python, SQL and machine learning...",
    )
    run = st.button("Run workflow", type="primary", use_container_width=True)

with col_out:
    st.subheader("Result")

    if run:
        if not application.strip():
            st.warning("Please enter an application first.")
        else:
            final_state = {"application": application}
            with st.status("Running workflow...", expanded=True) as status:
                try:
                    for step in app.stream({"application": application}):
                        for node_name, update in step.items():
                            st.write(f"✅ **{node_name}** → {update}")
                            final_state.update(update)
                    status.update(label="Workflow complete", state="complete")
                except Exception as e:
                    status.update(label="Workflow failed", state="error")
                    st.error(f"Error: {e}")
                    st.stop()

            m1, m2 = st.columns(2)
            m1.metric("Experience level", final_state.get("experience_level", "-"))
            m2.metric("Skill match", final_state.get("skill_match", "-"))

            outcome = final_state.get("response", "")
            if "rejected" in outcome.lower():
                st.error(outcome)
            elif "escalated" in outcome.lower():
                st.warning(outcome)
            else:
                st.success(outcome)
    else:
        st.info("Results will appear here after you run the workflow.")
