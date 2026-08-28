from __future__ import annotations

import csv
from datetime import datetime
import json
import os
from pathlib import Path
import re
from typing import Dict, List, Mapping, Optional

import requests

from checker import diagnose_with_rules


REQUIRED_OUTPUT_FIELDS = [
    "root_cause",
    "osi_layer",
    "confidence",
    "evidence",
    "next_command",
    "fix_steps",
]


REVIEW_LOG_FIELDS = [
    "timestamp",
    "case_id",
    "concept_tag",
    "severity",
    "ai_root_cause",
    "ai_confidence",
    "reviewer_decision",
    "reviewer_name",
    "reviewer_fix",
    "reviewer_reason",
    "agreement_flag",
]


def _safe_text(value: object) -> str:
    if value is None:
        return ""
    return str(value)


def _coerce_fix_steps(value: object) -> List[str]:
    if isinstance(value, list):
        return [str(step).strip() for step in value if str(step).strip()]
    if isinstance(value, str):
        lines = [line.strip("- *\t ") for line in value.splitlines()]
        compact = [line for line in lines if line]
        if compact:
            return compact
        return [_safe_text(value).strip()] if _safe_text(value).strip() else []
    return []


def load_prompt(prompt_path: Path) -> str:
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
    return prompt_path.read_text(encoding="utf-8")


def _extract_json_object(text: str) -> Dict[str, object]:
    raw = text.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    code_block_match = re.search(r"```json\s*(\{.*?\})\s*```", raw, flags=re.DOTALL | re.IGNORECASE)
    if code_block_match:
        return json.loads(code_block_match.group(1))

    object_match = re.search(r"(\{.*\})", raw, flags=re.DOTALL)
    if object_match:
        return json.loads(object_match.group(1))

    raise ValueError("Model output did not contain a parseable JSON object.")


def _validate_diagnosis(payload: Mapping[str, object]) -> Dict[str, object]:
    missing = [field for field in REQUIRED_OUTPUT_FIELDS if field not in payload]
    if missing:
        raise ValueError(f"Missing required diagnosis field(s): {', '.join(missing)}")

    confidence = payload.get("confidence", 0.5)
    try:
        confidence_value = float(confidence)
    except (TypeError, ValueError):
        confidence_value = 0.5
    confidence_value = max(0.0, min(1.0, confidence_value))

    evidence_value = payload.get("evidence", [])
    if isinstance(evidence_value, str):
        evidence_list = [evidence_value.strip()] if evidence_value.strip() else []
    elif isinstance(evidence_value, list):
        evidence_list = [str(item).strip() for item in evidence_value if str(item).strip()]
    else:
        evidence_list = []

    return {
        "root_cause": _safe_text(payload.get("root_cause")).strip(),
        "osi_layer": _safe_text(payload.get("osi_layer")).strip(),
        "confidence": round(confidence_value, 2),
        "evidence": evidence_list,
        "next_command": _safe_text(payload.get("next_command")).strip(),
        "fix_steps": _coerce_fix_steps(payload.get("fix_steps")),
    }


def call_llm(system_prompt: str, user_payload: str) -> Dict[str, object]:
    """Call an OpenAI-compatible chat completions endpoint for the LLM diagnosis pass."""
    api_key = os.getenv("OPENAI_API_KEY")
    model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set.")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    payload = {
        "model": model_name,
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_payload},
        ],
    }

    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=60,
    )
    response.raise_for_status()
    body = response.json()

    choices = body.get("choices", [])
    if not choices:
        raise ValueError(f"OpenAI returned no choices: {body}")

    content = _safe_text(choices[0].get("message", {}).get("content"))
    parsed = _extract_json_object(content)
    return _validate_diagnosis(parsed)


def _fallback_from_checker(case: Mapping[str, object], checker_result: Mapping[str, object]) -> Dict[str, object]:
    primary = checker_result["primary_finding"]
    return {
        "root_cause": _safe_text(primary.get("root_cause")),
        "osi_layer": _safe_text(primary.get("osi_layer")) or _safe_text(case.get("osi_layer")) or "Unknown",
        "confidence": float(primary.get("confidence", 0.5)),
        "evidence": [_safe_text(primary.get("evidence"))],
        "next_command": _safe_text(primary.get("next_command")) or "show run",
        "fix_steps": [str(step) for step in primary.get("fix_steps", [])],
    }


def _build_user_payload(case: Mapping[str, object], checker_result: Mapping[str, object]) -> str:
    compact = {
        "case_id": case.get("case_id"),
        "symptom": case.get("symptom"),
        "topology_note": case.get("topology_note"),
        "show_outputs": case.get("show_outputs"),
        "checker_status": checker_result.get("status"),
        "checker_primary": checker_result.get("primary_finding"),
    }
    return json.dumps(compact, indent=2)


def _merge_final_diagnosis(
    case: Mapping[str, object],
    checker_result: Mapping[str, object],
    llm_result: Mapping[str, object],
) -> Dict[str, object]:
    primary = checker_result["primary_finding"]
    checker_confidence = float(primary.get("confidence", 0.0))

    if checker_confidence >= 0.9:
        merged_evidence = list(dict.fromkeys([_safe_text(primary.get("evidence"))] + list(llm_result.get("evidence", []))))
        return {
            "root_cause": _safe_text(primary.get("root_cause")),
            "osi_layer": _safe_text(primary.get("osi_layer")),
            "confidence": checker_confidence,
            "evidence": [item for item in merged_evidence if item],
            "next_command": _safe_text(primary.get("next_command")) or _safe_text(llm_result.get("next_command")),
            "fix_steps": list(primary.get("fix_steps", [])) or list(llm_result.get("fix_steps", [])),
            "source": "checker-priority",
            "expected_fault": _safe_text(case.get("expected_fault")),
        }

    return {
        "root_cause": _safe_text(llm_result.get("root_cause")),
        "osi_layer": _safe_text(llm_result.get("osi_layer")),
        "confidence": float(llm_result.get("confidence", 0.5)),
        "evidence": list(llm_result.get("evidence", [])),
        "next_command": _safe_text(llm_result.get("next_command")),
        "fix_steps": list(llm_result.get("fix_steps", [])),
        "source": "llm-priority",
        "expected_fault": _safe_text(case.get("expected_fault")),
    }


def diagnose_case(case: Mapping[str, object], prompt_path: Path) -> Dict[str, object]:
    checker_result = diagnose_with_rules(case)
    prompt = load_prompt(prompt_path)

    llm_result: Optional[Dict[str, object]] = None
    llm_error: Optional[str] = None

    try:
        llm_result = call_llm(prompt, _build_user_payload(case, checker_result))
    except Exception as exc:  # noqa: BLE001
        llm_error = str(exc)

    if llm_result is None:
        llm_result = _fallback_from_checker(case, checker_result)
        final = {
            **llm_result,
            "source": "deterministic-fallback",
            "expected_fault": _safe_text(case.get("expected_fault")),
        }
    else:
        final = _merge_final_diagnosis(case, checker_result, llm_result)

    return {
        "case_id": _safe_text(case.get("case_id")),
        "checker": checker_result,
        "llm": llm_result,
        "final": final,
        "engine_notes": {
            "used_llm": llm_error is None,
            "llm_error": llm_error,
            "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        },
    }


def ensure_review_log(log_csv_path: Path) -> None:
    log_csv_path.parent.mkdir(parents=True, exist_ok=True)
    if log_csv_path.exists():
        return
    with log_csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=REVIEW_LOG_FIELDS)
        writer.writeheader()


def _ensure_audit_markdown(audit_md_path: Path) -> None:
    audit_md_path.parent.mkdir(parents=True, exist_ok=True)
    if audit_md_path.exists() and audit_md_path.stat().st_size > 0:
        return
    starter = "# NetsageAi Audit Log\n\nThis file records human review decisions for AI diagnoses.\n\n"
    audit_md_path.write_text(starter, encoding="utf-8")


def append_review_record(record: Mapping[str, object], log_csv_path: Path, audit_md_path: Path) -> Dict[str, object]:
    ensure_review_log(log_csv_path)
    _ensure_audit_markdown(audit_md_path)

    normalized: Dict[str, object] = {}
    for key in REVIEW_LOG_FIELDS:
        normalized[key] = record.get(key, "")

    if not normalized["timestamp"]:
        normalized["timestamp"] = datetime.utcnow().isoformat(timespec="seconds") + "Z"

    with log_csv_path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=REVIEW_LOG_FIELDS)
        writer.writerow(normalized)

    entry = (
        f"## {normalized['timestamp']} - {normalized['case_id']}\n"
        f"- Decision: {normalized['reviewer_decision']}\n"
        f"- Reviewer: {normalized['reviewer_name'] or 'anonymous'}\n"
        f"- AI Root Cause: {normalized['ai_root_cause']}\n"
        f"- AI Confidence: {normalized['ai_confidence']}\n"
        f"- Agreement: {normalized['agreement_flag']}\n"
        f"- Reviewer Fix: {normalized['reviewer_fix']}\n"
        f"- Reviewer Reason: {normalized['reviewer_reason']}\n\n"
    )
    with audit_md_path.open("a", encoding="utf-8") as handle:
        handle.write(entry)

    return {key: _safe_text(value) for key, value in normalized.items()}
