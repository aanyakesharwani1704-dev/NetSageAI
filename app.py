import streamlit as st
from pathlib import Path
import os

import pandas as pd

from engine import append_review_record, diagnose_case, ensure_review_log


ROOT = Path(__file__).resolve().parents[1]
CASES_PATH = ROOT / "data" / "cases.csv"
PROMPT_PATH = ROOT / "prompts" / "diagnose_prompt.md"
REVIEW_LOG_PATH = ROOT / "data" / "review_log.csv"
AUDIT_MD_PATH = ROOT / "docs" / "audit_logs.md"


def _decision_to_agreement(decision: str) -> bool:
    return decision == "Accepted"


def _bootstrap_llm_env_from_secrets() -> None:
    # Allow users to configure key/model in .streamlit/secrets.toml without shell exports.
    openai_key = st.secrets.get("OPENAI_API_KEY", "")
    openai_model = st.secrets.get("OPENAI_MODEL", "")
    if openai_key and not os.getenv("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = str(openai_key)
    if openai_model and not os.getenv("OPENAI_MODEL"):
        os.environ["OPENAI_MODEL"] = str(openai_model)


@st.cache_data
def load_cases(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def load_reviews(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path)
    if "agreement_flag" in df.columns:
        df["agreement_flag"] = (
            df["agreement_flag"].astype(str).str.lower().isin(["true", "1", "yes"])
        )
    return df


def seed_demo_corrections(cases_df: pd.DataFrame) -> int:
    existing = load_reviews(REVIEW_LOG_PATH)
    already_seeded = 0
    if not existing.empty and "reviewer_name" in existing.columns:
        already_seeded = int((existing["reviewer_name"] == "demo-seed").sum())
    if already_seeded >= 5:
        return 0

    selected = cases_df.head(5).copy()
    inserted = 0
    for idx, (_, row) in enumerate(selected.iterrows(), start=1):
        decision = "Edited" if idx % 2 else "Rejected"
        record = {
            "case_id": row["case_id"],
            "concept_tag": row["concept_tag"],
            "severity": row["severity"],
            "ai_root_cause": f"Draft AI diagnosis for {row['case_id']}",
            "ai_confidence": 0.55,
            "reviewer_decision": decision,
            "reviewer_name": "demo-seed",
            "reviewer_fix": row["expected_fault"],
            "reviewer_reason": "Seeded correction entry for Responsible AI evidence.",
            "agreement_flag": False,
        }
        append_review_record(record, REVIEW_LOG_PATH, AUDIT_MD_PATH)
        inserted += 1
    return inserted


def show_metrics(reviews_df: pd.DataFrame) -> None:
    st.subheader("Dashboard Summary")
    if reviews_df.empty:
        st.info("No review records yet. Submit at least one decision to populate metrics.")
        return

    total = len(reviews_df)
    accepted = int((reviews_df["reviewer_decision"] == "Accepted").sum())
    edited = int((reviews_df["reviewer_decision"] == "Edited").sum())
    rejected = int((reviews_df["reviewer_decision"] == "Rejected").sum())
    agreement_rate = float(reviews_df["agreement_flag"].mean()) if total else 0.0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Reviews", total)
    c2.metric("Accepted", accepted)
    c3.metric("Edited", edited)
    c4.metric("Rejected", rejected)
    st.metric("AI-Human Agreement Rate", f"{agreement_rate * 100:.1f}%")

    left, right = st.columns(2)
    with left:
        st.markdown("Severity Distribution")
        st.bar_chart(reviews_df["severity"].value_counts())
    with right:
        st.markdown("Issue Type Distribution")
        st.bar_chart(reviews_df["concept_tag"].value_counts())

    st.markdown("Recent Human Overrides")
    overrides = reviews_df[reviews_df["reviewer_decision"].isin(["Edited", "Rejected"])].copy()
    if overrides.empty:
        st.caption("No overrides yet.")
    else:
        display_cols = [
            "timestamp",
            "case_id",
            "reviewer_decision",
            "reviewer_name",
            "reviewer_reason",
        ]
        st.dataframe(overrides[display_cols].tail(10), use_container_width=True)


st.set_page_config(page_title="NetsageAi", layout="wide")
st.title("NetsageAi - Lab Network Troubleshooting Assistant")
st.caption("Hybrid deterministic + LLM diagnostics with mandatory Human-in-the-Loop review")

_bootstrap_llm_env_from_secrets()

ensure_review_log(REVIEW_LOG_PATH)
cases_df = load_cases(CASES_PATH)
reviews_df = load_reviews(REVIEW_LOG_PATH)

with st.sidebar:
    st.header("System Status")
    st.write(f"Cases loaded: {len(cases_df)}")
    st.write(f"Review records: {len(reviews_df)}")
    st.write(f"Prompt file: {PROMPT_PATH.name}")
    openai_key_present = bool(os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY", None))
    st.write("LLM key status: " + ("Configured" if openai_key_present else "Not configured"))
    st.write("LLM model: " + str(os.getenv("OPENAI_MODEL", st.secrets.get("OPENAI_MODEL", "gpt-4o-mini"))))

    if st.button("Seed 5 demo correction logs"):
        inserted_count = seed_demo_corrections(cases_df)
        if inserted_count:
            st.success(f"Inserted {inserted_count} seeded correction records.")
        else:
            st.info("Seed records already exist.")

st.subheader("Case Explorer")
selected_case_id = st.selectbox("Select case", options=cases_df["case_id"].tolist(), index=0)
selected_case = cases_df[cases_df["case_id"] == selected_case_id].iloc[0].to_dict()

c1, c2, c3 = st.columns(3)
c1.markdown(f"**Concept**: {selected_case['concept_tag']}")
c2.markdown(f"**Severity**: {selected_case['severity']}")
c3.markdown(f"**Expected OSI Layer**: {selected_case['osi_layer']}")

st.markdown("**Symptom**")
st.write(selected_case["symptom"])
st.markdown("**Topology Note**")
st.write(selected_case["topology_note"])
st.markdown("**Show Outputs**")
st.code(str(selected_case["show_outputs"]))

if st.button("Run Hybrid Diagnosis", type="primary"):
    with st.spinner("Running checker and LLM diagnosis..."):
        diagnosis = diagnose_case(selected_case, PROMPT_PATH)
    st.session_state["diagnosis"] = diagnosis

if "diagnosis" in st.session_state:
    diagnosis = st.session_state["diagnosis"]
    st.subheader("Diagnosis Results")

    left, right = st.columns(2)
    with left:
        st.markdown("**Deterministic Checker**")
        st.write(diagnosis["checker"]["summary"])
        findings_df = pd.DataFrame(diagnosis["checker"]["findings"])
        if findings_df.empty:
            st.caption("No rule match. LLM inference required.")
        else:
            st.dataframe(findings_df, use_container_width=True)

    with right:
        st.markdown("**Final Merged Diagnosis**")
        st.json(diagnosis["final"])
        note = diagnosis["engine_notes"].get("llm_error")
        if note:
            st.warning(f"LLM fallback activated: {note}")

    st.subheader("Human Review Gate (Mandatory)")
    decision = st.radio("Review Decision", ["Accepted", "Edited", "Rejected"], horizontal=True)
    reviewer_name = st.text_input("Reviewer Name", value="operator")
    reviewer_reason = st.text_area("Reviewer Reason / Notes", placeholder="Add why you accepted, edited, or rejected this diagnosis.")
    reviewer_fix = st.text_area(
        "Edited Fix / Approved CLI Steps",
        placeholder="If Edited, provide corrected fix commands. If Accepted, you can keep AI fix.",
        value="\n".join(diagnosis["final"].get("fix_steps", [])),
    )

    if decision == "Edited" and not reviewer_fix.strip():
        st.error("Edited decisions require corrected fix steps.")

    if st.button("Save Review Decision"):
        if decision == "Edited" and not reviewer_fix.strip():
            st.stop()

        review_record = {
            "case_id": selected_case["case_id"],
            "concept_tag": selected_case["concept_tag"],
            "severity": selected_case["severity"],
            "ai_root_cause": diagnosis["final"].get("root_cause", ""),
            "ai_confidence": diagnosis["final"].get("confidence", 0.0),
            "reviewer_decision": decision,
            "reviewer_name": reviewer_name,
            "reviewer_fix": reviewer_fix,
            "reviewer_reason": reviewer_reason,
            "agreement_flag": _decision_to_agreement(decision),
        }
        append_review_record(review_record, REVIEW_LOG_PATH, AUDIT_MD_PATH)
        st.success("Review decision saved to CSV and markdown audit log.")

reviews_df = load_reviews(REVIEW_LOG_PATH)
show_metrics(reviews_df)
