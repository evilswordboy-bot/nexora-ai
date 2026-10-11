from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient

from app.main import app
from app.services.workflows.engine import WorkflowAutomationEngine

client = TestClient(app)


def test_stage15_health_and_metadata():
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    data = res.json()
    assert data["stage"] >= 15
    assert data["subsystems"]["workflow_automation"] == "operational"

    meta_res = client.get("/api/v1/workflows/metadata")
    assert meta_res.status_code == 200
    meta = meta_res.json()
    assert len(meta["available_agents"]) == 8
    assert len(meta["available_tools"]) >= 8
    assert "Asia/Kolkata" in meta["supported_timezones"]
    assert meta["notification_channels"]["in_app"] is True


def test_stage15_templates_duplicate_edit_and_delete():
    tpl_res = client.get("/api/v1/workflows/templates")
    assert tpl_res.status_code == 200
    templates = tpl_res.json()
    assert len(templates) >= 4
    tpl_id = templates[0]["workflow_id"]

    # Duplicate template
    dup_res = client.post(f"/api/v1/workflows/{tpl_id}/duplicate?user_id=test_user_15")
    assert dup_res.status_code == 200
    cloned = dup_res.json()
    assert cloned["is_template"] is False
    assert cloned["status"] == "DRAFT"
    wf_id = cloned["workflow_id"]

    # Edit workflow
    upd_res = client.put(
        f"/api/v1/workflows/{wf_id}",
        json={"name": "Custom Daily Tech Digest", "status": "ACTIVE"},
    )
    assert upd_res.status_code == 200
    assert upd_res.json()["name"] == "Custom Daily Tech Digest"
    assert upd_res.json()["status"] == "ACTIVE"
    assert upd_res.json()["schedule"]["next_run_at"] is not None

    # Pause and resume
    pause_res = client.post(f"/api/v1/workflows/{wf_id}/status", json={"status": "PAUSED"})
    assert pause_res.status_code == 200
    assert pause_res.json()["status"] == "PAUSED"
    assert pause_res.json()["schedule"]["next_run_at"] is None

    # Delete cloned workflow
    del_res = client.delete(f"/api/v1/workflows/{wf_id}")
    assert del_res.status_code == 200
    assert del_res.json()["deleted"] is True


def test_stage15_validation_cycles_backward_jumps_and_timezones():
    # 1. Dependency cycle
    cycle_res = client.post(
        "/api/v1/workflows/validate",
        json={
            "schedule": {"trigger_type": "scheduled", "timezone": "Invalid/Timezone_X"},
            "steps": [
                {
                    "step_id": "s1",
                    "name": "Step 1",
                    "action_type": "tool",
                    "tool_name": "calculator",
                    "tool_params": {"expression": "1+1"},
                    "depends_on": ["s2"],
                },
                {
                    "step_id": "s2",
                    "name": "Step 2",
                    "action_type": "tool",
                    "tool_name": "calculator",
                    "tool_params": {"expression": "2+2"},
                    "depends_on": ["s1"],
                },
            ],
        },
    )
    assert cycle_res.status_code == 200
    vdata = cycle_res.json()
    assert vdata["valid"] is False
    codes = {i["code"] for i in vdata["issues"]}
    assert "DEPENDENCY_CYCLE_DETECTED" in codes
    assert "INVALID_TIMEZONE" in codes

    # 2. Backward jump prevention
    jump_res = client.post(
        "/api/v1/workflows/validate",
        json={
            "steps": [
                {
                    "step_id": "s1",
                    "name": "Step 1",
                    "action_type": "tool",
                    "tool_name": "calculator",
                    "tool_params": {"expression": "10+5"},
                },
                {
                    "step_id": "s2",
                    "name": "Step 2",
                    "action_type": "tool",
                    "tool_name": "calculator",
                    "tool_params": {"expression": "20+5"},
                    "depends_on": ["s1"],
                    "condition_expression": "contains:999",
                    "on_condition_false": "jump_to_step",
                    "jump_to_step_id": "s1",
                },
            ]
        },
    )
    assert jump_res.status_code == 200
    jdata = jump_res.json()
    assert jdata["valid"] is False
    assert any(i["code"] == "BACKWARD_JUMP_LOOP" for i in jdata["issues"])


def test_stage15_sequential_execution_io_mapping_and_branching(tmp_path):
    # Create workflow with calculator -> condition branch -> transform
    create_res = client.post(
        "/api/v1/workflows",
        json={
            "user_id": "exec_user",
            "name": "Math & Branching Pipeline",
            "description": "Tests input/output mapping and conditional branching.",
            "status": "ACTIVE",
            "steps": [
                {
                    "step_id": "step_calc_1",
                    "name": "Calculate Base Value",
                    "action_type": "tool",
                    "tool_name": "calculator",
                    "tool_params": {"expression": "{{workflow.input.base_expr}}"},
                },
                {
                    "step_id": "step_skipped_branch",
                    "name": "Conditional Skip Step",
                    "action_type": "transform",
                    "prompt_template": "Should be skipped",
                    "depends_on": ["step_calc_1"],
                    "condition_expression": "contains:999999",
                    "on_condition_false": "skip",
                },
                {
                    "step_id": "step_final_transform",
                    "name": "Format Final Output",
                    "action_type": "transform",
                    "prompt_template": "Final verified result from step 1 -> {{steps.step_calc_1.output}}",
                    "depends_on": ["step_calc_1"],
                    "condition_expression": "contains:42",
                },
            ],
        },
    )
    assert create_res.status_code == 200
    wf_id = create_res.json()["workflow_id"]

    run_res = client.post(
        f"/api/v1/workflows/{wf_id}/run",
        json={
            "user_id": "exec_user",
            "runtime_inputs": {"base_expr": "40 + 2"},
        },
    )
    assert run_res.status_code == 200
    run_data = run_res.json()
    assert run_data["status"] == "SUCCEEDED"
    step_statuses = {s["step_id"]: s["status"] for s in run_data["step_results"]}
    assert step_statuses["step_calc_1"] == "SUCCEEDED"
    assert step_statuses["step_skipped_branch"] == "SKIPPED"
    assert step_statuses["step_final_transform"] == "SUCCEEDED"
    assert "42" in run_data["step_results"][2]["output_summary"]


def test_stage15_consequential_approval_gate_and_resume():
    # Create workflow with dispatch_external_message (consequential tool)
    create_res = client.post(
        "/api/v1/workflows",
        json={
            "user_id": "approval_user",
            "name": "Approved External Webhook Workflow",
            "status": "ACTIVE",
            "steps": [
                {
                    "step_id": "s1_prep",
                    "name": "Calculate Metric",
                    "action_type": "tool",
                    "tool_name": "calculator",
                    "tool_params": {"expression": "100 * 2"},
                },
                {
                    "step_id": "s2_send",
                    "name": "Send External Webhook",
                    "action_type": "tool",
                    "tool_name": "dispatch_external_message",
                    "tool_params": {
                        "recipient": "ops-channel",
                        "subject": "Metric Alert",
                        "body": "Metric is {{steps.s1_prep.output}}",
                    },
                    "depends_on": ["s1_prep"],
                },
            ],
        },
    )
    assert create_res.status_code == 200
    wf_id = create_res.json()["workflow_id"]

    # Trigger run -> should pause at s2_send in WAITING_FOR_APPROVAL
    run_res = client.post(f"/api/v1/workflows/{wf_id}/run", json={"user_id": "approval_user"})
    assert run_res.status_code == 200
    paused_run = run_res.json()
    assert paused_run["status"] == "WAITING_FOR_APPROVAL"
    assert paused_run["waiting_approval_step_id"] == "s2_send"
    run_id = paused_run["run_id"]

    # Approve step -> should resume and complete SUCCEEDED
    approve_res = client.post(
        f"/api/v1/workflows/runs/{run_id}/approve",
        json={"user_id": "approval_user", "step_id": "s2_send", "approved": True},
    )
    assert approve_res.status_code == 200
    completed_run = approve_res.json()
    assert completed_run["status"] == "SUCCEEDED"
    assert completed_run["step_results"][1]["status"] == "SUCCEEDED"
    assert "Approved external message dispatched" in completed_run["step_results"][1]["output_summary"]


def test_stage15_bounded_retries_failure_honesty_and_manual_retry():
    # Create workflow where step fails via __simulate_failure
    create_res = client.post(
        "/api/v1/workflows",
        json={
            "user_id": "retry_user",
            "name": "Bounded Retry & Failure Test",
            "status": "ACTIVE",
            "steps": [
                {
                    "step_id": "s1_fail",
                    "name": "Failing Tool Step",
                    "action_type": "tool",
                    "tool_name": "calculator",
                    "tool_params": {
                        "expression": "10 + 10",
                        "__simulate_failure": "{{workflow.input.should_fail}}",
                    },
                    "max_retries": 2,
                    "retry_delay_seconds": 0.01,
                }
            ],
        },
    )
    assert create_res.status_code == 200
    wf_id = create_res.json()["workflow_id"]

    # Run with failure enabled -> must attempt 1 + 2 retries = 3 attempts and end in FAILED (never SUCCEEDED)
    run_res = client.post(
        f"/api/v1/workflows/{wf_id}/run",
        json={"user_id": "retry_user", "runtime_inputs": {"should_fail": "true"}},
    )
    assert run_res.status_code == 200
    failed_run = run_res.json()
    assert failed_run["status"] == "FAILED"
    assert failed_run["step_results"][0]["attempt_count"] == 3
    assert failed_run["step_results"][0]["status"] == "FAILED"


def test_stage15_scheduler_timezones_duplicate_prevention_and_worker_recovery(tmp_path):
    import asyncio

    db_file = tmp_path / "test_wf.db"
    engine = WorkflowAutomationEngine(db_path=str(db_file))

    past_due = datetime.now(timezone.utc) - timedelta(minutes=5)
    wf = engine.create_workflow(
        req=client.app.dependency_overrides.get("noop", lambda: None)()
        or __import__("app.models.schemas", fromlist=["WorkflowCreateRequest"]).WorkflowCreateRequest(
            user_id="sched_user",
            name="Timezone Scheduled Task",
            status="ACTIVE",
            schedule={
                "trigger_type": "scheduled",
                "recurrence": "daily",
                "timezone": "Asia/Kolkata",
                "allow_concurrent_runs": False,
            },
            steps=[
                {
                    "step_id": "s1",
                    "name": "Quick Calc",
                    "action_type": "tool",
                    "tool_name": "calculator",
                    "tool_params": {"expression": "7 * 8"},
                }
            ],
        )
    )
    # Force next_run_at into the past so tick_scheduler fires it
    with engine._get_conn() as conn:
        wf.schedule.next_run_at = past_due
        engine._save_workflow_row(conn, wf)
        conn.commit()

    triggered = asyncio.run(engine.tick_scheduler())
    assert len(triggered) == 1
    assert triggered[0].status == "SUCCEEDED"

    # Calling tick_scheduler immediately again must not duplicate the run
    triggered_again = asyncio.run(engine.tick_scheduler())
    assert len(triggered_again) == 0

    # Simulate an interrupted RUNNING job in DB and verify worker restart recovery
    interrupted_run = triggered[0]
    interrupted_run.run_id = "wfrun_interrupted_test"
    interrupted_run.idempotency_key = "interrupted_key_1"
    interrupted_run.status = "RUNNING"
    interrupted_run.step_results[0].status = "RUNNING"
    engine._persist_run(interrupted_run)

    recovered = asyncio.run(engine.recover_interrupted_runs_on_startup())
    assert len(recovered) == 1
    assert recovered[0].run_id == "wfrun_interrupted_test"
    assert recovered[0].status == "FAILED"
    assert "worker restart" in (recovered[0].error_message or "").lower()

    # Check notifications and honest external delivery status
    notifs = engine.list_notifications(user_id="sched_user")
    assert len(notifs) >= 2
    assert all(n.external_delivery_confirmed is False for n in notifs)
