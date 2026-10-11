"""
NEXORA AI — Stage 20: AI Evaluation & Quality Assurance Engine Tests
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.evaluation.engine import EvaluationQualityAssuranceEngine

client = TestClient(app)


@pytest.fixture()
def isolated_eval_engine(tmp_path, monkeypatch):
    """Provides a clean isolated EvaluationQualityAssuranceEngine per test."""
    db_file = tmp_path / "test_nexora_eval.db"
    ws_dir = tmp_path / "eval_ws"
    engine = EvaluationQualityAssuranceEngine(db_path=str(db_file), workspace_dir=str(ws_dir))
    monkeypatch.setattr("app.api.v1.evaluation.evaluation_qa_engine", engine)
    monkeypatch.setattr("app.services.evaluation.engine.evaluation_qa_engine", engine)
    return engine


def test_stage20_health_and_metadata(isolated_eval_engine):
    # Check health endpoint
    h_res = client.get("/api/v1/health")
    assert h_res.status_code == 200
    h_data = h_res.json()
    assert h_data["stage"] >= 20
    assert h_data["subsystems"]["evaluation_qa"] == "operational"

    # Check evaluation metadata
    res = client.get("/api/v1/evaluation/metadata")
    assert res.status_code == 200
    meta = res.json()
    assert meta["stage"] == 20
    assert meta["dataset_version"] == "v1.0.0"
    assert meta["total_cases"] == 20
    assert meta["approved_cases"] == 20
    assert meta["exclude_private_conversations_by_default"] is True
    assert len(meta["suites"]) == 10
    assert len(meta["scoring_rules"]) >= 8

    # Verify subjective/heuristic rubrics are never claimed as definitive ground truth
    rules_by_id = {r["metric_id"]: r for r in meta["scoring_rules"]}
    assert rules_by_id["language_quality_score"]["is_definitive_ground_truth"] is False
    assert "Limitations" in rules_by_id["language_quality_score"]["limitations"] or len(
        rules_by_id["language_quality_score"]["limitations"]
    ) > 15


def test_stage20_full_10_suite_run_and_reproducibility(isolated_eval_engine):
    # Execute all 10 suites (20 benchmark cases)
    r1 = client.post(
        "/api/v1/evaluation/runs",
        json={"label": "Baseline Release Candidate v1"},
    )
    assert r1.status_code == 200
    run1 = r1.json()
    assert run1["status"] == "COMPLETED"
    assert run1["sample_size"] == 20
    assert run1["completed_cases"] == 20
    assert run1["passed_cases"] == 20
    assert run1["failed_cases"] == 0
    assert run1["critical_failures"] == 0
    assert run1["release_gate_verdict"] == "RELEASE_APPROVED"
    assert run1["consequential_actions_blocked"] is True
    assert run1["isolated_environment_id"].startswith("eval_env_")

    metrics1 = run1["metrics"]
    assert metrics1["task_success_rate"] == 1.0
    assert metrics1["safety_compliance_rate"] == 1.0
    assert metrics1["error_rate"] == 0.0
    assert metrics1["factual_support_score"] == 1.0
    assert metrics1["citation_validity_score"] == 1.0
    assert metrics1["extraction_accuracy_score"] == 1.0
    assert metrics1["tool_call_success_rate"] == 1.0

    # Execute a second run on general_qa & coding_sandbox to verify scoring consistency/reproducibility
    r2 = client.post(
        "/api/v1/evaluation/runs",
        json={
            "label": "Reproducibility Check",
            "suites": ["general_qa", "coding_sandbox"],
        },
    )
    assert r2.status_code == 200
    run2 = r2.json()
    assert run2["passed_cases"] == 4
    assert run2["metrics"]["task_success_rate"] == 1.0


def test_stage20_dataset_versioning_and_privacy_guard(isolated_eval_engine):
    # 1. Reject private user conversation data by default
    priv_res = client.post(
        "/api/v1/evaluation/cases",
        json={
            "suite_id": "general_qa",
            "title": "Unapproved Private User Chat Log",
            "description": "Copied directly from private user session",
            "input_payload": {"prompt": "My private medical history..."},
            "expected_criteria": {"must_contain": ["ok"]},
            "scoring_rubric": "Exact match",
            "contains_private_conversation_data": True,
        },
    )
    assert priv_res.status_code == 400
    assert "excluded from evaluation datasets" in priv_res.json()["detail"]

    # 2. Reject raw API keys inside test case payload
    secret_res = client.post(
        "/api/v1/evaluation/cases",
        json={
            "suite_id": "general_qa",
            "title": "Accidental Credential Case",
            "description": "Contains raw key",
            "input_payload": {"api_key": "sk-proj-1234567890abcdef"},
            "expected_criteria": {},
            "scoring_rubric": "Check",
            "contains_private_conversation_data": False,
        },
    )
    assert secret_res.status_code == 400
    assert "credentials" in secret_res.json()["detail"].lower()

    # 3. Add a valid curated benchmark case and verify semantic version bump (v1.0.0 -> v1.0.1)
    add_res = client.post(
        "/api/v1/evaluation/cases",
        json={
            "suite_id": "general_qa",
            "title": "Custom Math Grounding Benchmark",
            "description": "Checks arithmetic expression evaluation.",
            "input_payload": {"expression": "(10 + 5) * 2"},
            "expected_criteria": {"exact_number": 30.0},
            "scoring_rubric": "Exact numerical match",
            "is_edge_case": False,
            "is_critical": True,
            "source_type": "curated_benchmark",
            "contains_private_conversation_data": False,
        },
    )
    assert add_res.status_code == 200
    added = add_res.json()
    assert added["dataset_version"] == "v1.0.1"
    assert added["review_status"] == "approved"

    # 4. Export dataset and verify changelog recorded the addition
    exp_res = client.get("/api/v1/evaluation/datasets/export")
    assert exp_res.status_code == 200
    exp_data = exp_res.json()
    assert exp_data["dataset_version"] == "v1.0.1"
    assert exp_data["total_cases"] == 21
    assert len(exp_data["changelog"]) >= 1

    # 5. Delete the added case and verify version bump to v1.0.2
    del_res = client.delete(f"/api/v1/evaluation/cases/{added['case_id']}")
    assert del_res.status_code == 200
    assert del_res.json()["dataset_version"] == "v1.0.2"


def test_stage20_synthetic_cases_labeled_and_gated_by_review(isolated_eval_engine):
    # Generate 2 synthetic test cases for security_privacy_safety
    syn_res = client.post(
        "/api/v1/evaluation/cases/synthetic",
        json={
            "suite_id": "security_privacy_safety",
            "count": 2,
            "topic_focus": "indirect prompt injection edge cases",
        },
    )
    assert syn_res.status_code == 200
    syn_data = syn_res.json()
    assert syn_data["generated_count"] == 2
    syn_case_id = syn_data["cases"][0]["case_id"]
    assert syn_data["cases"][0]["source_type"] == "synthetic_labeled"
    assert syn_data["cases"][0]["review_status"] == "pending_review"

    # Run security_privacy_safety WITHOUT include_pending_synthetic -> only 2 curated cases run
    run_std = client.post(
        "/api/v1/evaluation/runs",
        json={
            "label": "Standard Security Run",
            "suites": ["security_privacy_safety"],
            "include_pending_synthetic": False,
        },
    ).json()
    assert run_std["sample_size"] == 2

    # Approve the first synthetic case via review endpoint
    rev_res = client.post(
        f"/api/v1/evaluation/cases/{syn_case_id}/review",
        json={
            "review_status": "approved",
            "reviewer_note": "Reviewed and verified deterministic safety check.",
            "admin_actor": "qa_lead",
        },
    )
    assert rev_res.status_code == 200
    assert rev_res.json()["review_status"] == "approved"

    # Now standard run on security_privacy_safety includes the newly approved synthetic case (3 cases)
    run_after = client.post(
        "/api/v1/evaluation/runs",
        json={
            "label": "Post-Review Security Run",
            "suites": ["security_privacy_safety"],
            "include_pending_synthetic": False,
        },
    ).json()
    assert run_after["sample_size"] == 3
    assert run_after["passed_cases"] == 3


def test_stage20_regression_detection_and_release_blocking(isolated_eval_engine):
    # 1. Run clean baseline on general_qa
    base_run = client.post(
        "/api/v1/evaluation/runs",
        json={"label": "Baseline v1.0", "suites": ["general_qa"]},
    ).json()
    assert base_run["release_gate_verdict"] == "RELEASE_APPROVED"

    # 2. Add a failing critical test case to general_qa to trigger regression & critical failure block
    bad_case = client.post(
        "/api/v1/evaluation/cases",
        json={
            "suite_id": "general_qa",
            "title": "Intentional Critical Regression Case",
            "description": "Triggers mismatch against expected number to test release gate blocking.",
            "input_payload": {"expression": "2 + 2"},
            "expected_criteria": {"exact_number": 999.0},
            "scoring_rubric": "Must block release when critical case fails.",
            "is_critical": True,
            "source_type": "curated_benchmark",
        },
    ).json()

    cand_run = client.post(
        "/api/v1/evaluation/runs",
        json={
            "label": "Candidate v1.1 (With Regression)",
            "suites": ["general_qa"],
            "baseline_run_id": base_run["run_id"],
        },
    ).json()

    assert cand_run["failed_cases"] == 1
    assert cand_run["critical_failures"] == 1
    assert cand_run["release_gate_verdict"] == "RELEASE_BLOCKED_CRITICAL_FAILURE"
    assert len(cand_run["regression_alerts"]) >= 1
    assert any(a["metric_name"] == "task_success_rate" for a in cand_run["regression_alerts"])

    # 3. Also test standalone /compare endpoint
    cmp_res = client.post(
        "/api/v1/evaluation/compare",
        json={
            "baseline_run_id": base_run["run_id"],
            "candidate_run_id": cand_run["run_id"],
        },
    )
    assert cmp_res.status_code == 200
    cmp_data = cmp_res.json()
    assert cmp_data["regressions_count"] >= 1
    assert cmp_data["candidate_verdict"] == "RELEASE_BLOCKED_CRITICAL_FAILURE"

    # Clean up the intentional failing case
    client.delete(f"/api/v1/evaluation/cases/{bad_case['case_id']}")


def test_stage20_interrupted_and_provider_failure_edge_cases(isolated_eval_engine):
    # 1. Simulate interrupted evaluation run after 1 case
    int_res = client.post(
        "/api/v1/evaluation/runs",
        json={
            "label": "Interrupted Run Test",
            "suites": ["general_qa", "fact_checking"],
            "simulate_interrupted_after_n": 1,
        },
    )
    assert int_res.status_code == 200
    int_run = int_res.json()
    assert int_run["status"] == "INCOMPLETE_INTERRUPTED"
    assert int_run["completed_cases"] == 1
    assert int_run["sample_size"] == 4
    assert int_run["release_gate_verdict"] == "INCOMPLETE_RUN"

    # 2. Simulate provider failure -> no fabricated scores
    fail_res = client.post(
        "/api/v1/evaluation/runs",
        json={
            "label": "Provider Outage Test",
            "suites": ["general_qa"],
            "simulate_provider_failure": True,
        },
    )
    assert fail_res.status_code == 200
    fail_run = fail_res.json()
    assert fail_run["status"] == "FAILED_PROVIDER_ERROR"
    assert fail_run["completed_cases"] == 0
    assert fail_run["release_gate_verdict"] == "INCOMPLETE_RUN"
    assert fail_run["metrics"]["factual_support_score"] is None
    assert "all_quality_metrics" in fail_run["metrics"]["unavailable_metrics_notes"]


def test_stage20_export_reports_and_tool_registry(isolated_eval_engine):
    run = client.post(
        "/api/v1/evaluation/runs",
        json={"label": "Export Report Test", "suites": ["general_qa"]},
    ).json()

    # Export Markdown report
    md_res = client.get(f"/api/v1/evaluation/runs/{run['run_id']}/export?format=markdown")
    assert md_res.status_code == 200
    md_data = md_res.json()
    assert md_data["format"] == "markdown"
    assert "# NEXORA AI — Stage 20 Evaluation & QA Report" in md_data["content"]
    assert "RELEASE_APPROVED" in md_data["content"]

    # Export JSON report
    js_res = client.get(f"/api/v1/evaluation/runs/{run['run_id']}/export?format=json")
    assert js_res.status_code == 200
    assert js_res.json()["format"] == "json"

    # Verify ToolRegistry integration for evaluation_qa_runner
    import asyncio
    from app.services.tools_registry import tool_registry

    tool_out = asyncio.run(
        tool_registry.execute(
            "evaluation_qa_runner",
            {"action": "run_suite", "suite_id": "general_qa", "label": "Tool QA Check"},
        )
    )
    assert tool_out["success"] is True
    assert tool_out["data"]["release_gate_verdict"] == "RELEASE_APPROVED"
