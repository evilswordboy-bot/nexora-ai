"""
NEXORA AI — Stage 11: Advanced Reasoning Engine Test Suite
Tests:
- Simple queries answered directly vs. complex multi-step problem decomposition
- Dependency-ordered subtasks (PLANNED -> IN PROGRESS -> REVIEWING -> COMPLETE)
- Real tool execution (AST Calculator, Document Vault retrieval, Web Search, Telemetry)
- Safe AST math evaluator security (no eval(), rejects code injection)
- Tool failure and retry recovery within configurable limits
- Plan inspection, revision, and cancellation
- Approval-required consequential actions pausing in BLOCKED state until explicit user approval
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.tools_registry import safe_eval_math, tool_registry

client = TestClient(app)


def test_safe_ast_calculator_evaluation_and_security():
    """Verify safe_eval_math evaluates real expressions and blocks unsafe code execution."""
    assert safe_eval_math("(125 * 4) + sqrt(144)") == 512.0
    assert safe_eval_math("2 ^ 10") == 1024.0
    assert safe_eval_math("round(100 / 3, 2)") == 33.33

    with pytest.raises(ValueError):
        safe_eval_math("__import__('os').system('echo hacked')")

    with pytest.raises(ValueError):
        safe_eval_math("2 ** 5000")


def test_list_registered_tools_endpoint():
    """Verify /api/v1/reasoning/tools lists registered Stage 1-11 tools with schemas and risk levels."""
    res = client.get("/api/v1/reasoning/tools")
    assert res.status_code == 200
    tools = res.json()
    tool_names = {t["name"] for t in tools}
    assert "calculator" in tool_names
    assert "web_search" in tool_names
    assert "document_retrieval" in tool_names
    assert "fact_check" in tool_names
    assert "translation" in tool_names
    assert "delete_document" in tool_names


def test_simple_query_direct_response_without_unnecessary_planning():
    """Verify simple conversational/conceptual queries are answered directly without subtask overhead."""
    res = client.post(
        "/api/v1/reasoning/analyze",
        json={
            "query": "What is the capital of France?",
            "auto_execute": True,
            "force_plan": False,
        },
    )
    assert res.status_code == 200
    plan = res.json()
    assert plan["classification"]["complexity"] == "simple"
    assert plan["classification"]["requires_planning"] is False
    assert plan["status"] == "COMPLETE"
    assert plan["subtasks"] == []
    assert plan["final_answer"] is not None


def test_complex_multistep_calculation_and_document_plan():
    """Verify complex multi-tool request decomposes into dependent subtasks and executes real tools."""
    res = client.post(
        "/api/v1/reasoning/analyze",
        json={
            "query": "First calculate (450 * 12) + sqrt(625) and then check my uploaded document for budget notes.",
            "auto_execute": True,
        },
    )
    assert res.status_code == 200
    plan = res.json()
    assert plan["classification"]["complexity"] == "complex"
    assert plan["classification"]["requires_planning"] is True
    assert "calculator" in plan["classification"]["required_tools"]
    assert "document_retrieval" in plan["classification"]["required_tools"]
    assert plan["status"] == "COMPLETE"
    assert len(plan["subtasks"]) == 3  # calculator -> document_retrieval -> synthesis

    calc_step = plan["subtasks"][0]
    doc_step = plan["subtasks"][1]
    synth_step = plan["subtasks"][2]

    assert calc_step["tool_name"] == "calculator"
    assert calc_step["status"] == "COMPLETE"
    assert calc_step["verification_passed"] is True
    assert "5425" in calc_step["result_summary"]

    # Check dependency chain
    assert doc_step["depends_on"] == [calc_step["id"]]
    assert doc_step["status"] == "COMPLETE"
    assert synth_step["depends_on"] == [doc_step["id"]]
    assert synth_step["status"] == "COMPLETE"
    assert plan["total_tool_calls"] >= 2


def test_consequential_action_blocks_for_user_approval_and_resumes():
    """Verify high-risk consequential actions enter BLOCKED state until explicit user approval is granted."""
    res = client.post(
        "/api/v1/reasoning/analyze",
        json={
            "query": "Please delete document doc_test999 from the document vault.",
            "auto_execute": True,
        },
    )
    assert res.status_code == 200
    plan = res.json()
    plan_id = plan["id"]
    assert plan["classification"]["has_consequential_actions"] is True
    assert plan["classification"]["risk_level"] == "high"
    assert plan["status"] == "BLOCKED"

    blocked_step = plan["subtasks"][0]
    assert blocked_step["tool_name"] == "delete_document"
    assert blocked_step["requires_approval"] is True
    assert blocked_step["status"] == "BLOCKED"

    # Now grant explicit user approval
    approve_res = client.post(
        f"/api/v1/reasoning/plans/{plan_id}/approve",
        json={
            "subtask_id": blocked_step["id"],
            "approved": True,
            "user_note": "Confirmed deletion of test document.",
            "auto_resume": True,
        },
    )
    assert approve_res.status_code == 200
    resumed_plan = approve_res.json()
    assert resumed_plan["status"] == "COMPLETE"
    assert resumed_plan["subtasks"][0]["status"] == "COMPLETE"
    assert resumed_plan["subtasks"][0]["approval_granted"] is True


def test_plan_revision_and_cancellation():
    """Verify plans can be inspected, revised with new parameters, and cancelled."""
    # Create a planned (not yet executed) task
    res = client.post(
        "/api/v1/reasoning/analyze",
        json={
            "query": "Calculate (100 * 5) + 50",
            "auto_execute": False,
            "force_plan": True,
        },
    )
    assert res.status_code == 200
    plan = res.json()
    plan_id = plan["id"]
    assert plan["status"] == "PLANNED"

    # Revise the plan's mathematical goal and execute
    rev_res = client.post(
        f"/api/v1/reasoning/plans/{plan_id}/revise",
        json={
            "revised_goal": "Calculate (200 * 5) + 50",
            "auto_execute": True,
        },
    )
    assert rev_res.status_code == 200
    revised_plan = rev_res.json()
    assert revised_plan["status"] == "COMPLETE"
    assert "1050" in revised_plan["subtasks"][0]["result_summary"]
    assert len(revised_plan["revision_history"]) >= 1

    # Cancel a new planned task
    res2 = client.post(
        "/api/v1/reasoning/analyze",
        json={
            "query": "Calculate 50 * 50",
            "auto_execute": False,
            "force_plan": True,
        },
    )
    plan2_id = res2.json()["id"]
    cancel_res = client.post(f"/api/v1/reasoning/plans/{plan2_id}/cancel")
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "CANCELLED"


def test_tool_failure_and_retry_recovery():
    """Verify recoverable tool failure triggers automatic retry recovery within configured limits."""
    call_counter = {"attempts": 0}

    async def flaky_handler(params):
        call_counter["attempts"] += 1
        if call_counter["attempts"] == 1:
            raise RuntimeError("Transient network timeout on attempt 1")
        return {"summary": "Recovered on attempt 2", "status": "ok"}

    from app.services.tools_registry import ToolDefinition
    tool_registry.register(
        ToolDefinition(
            name="flaky_diagnostic_tool",
            description="Test tool that fails once then succeeds on retry.",
            parameters_schema={"type": "object", "properties": {}},
            stage_introduced=11,
        ),
        handler=flaky_handler,
    )

    # Create a plan and inject the flaky tool into step 1
    res = client.post(
        "/api/v1/reasoning/analyze",
        json={
            "query": "Calculate 10 + 10",
            "auto_execute": False,
            "max_retries": 2,
        },
    )
    plan_id = res.json()["id"]
    from app.services.reasoning.engine import reasoning_engine
    plan_obj = reasoning_engine.get_plan(plan_id)
    assert plan_obj is not None
    plan_obj.subtasks[0].tool_name = "flaky_diagnostic_tool"
    plan_obj.subtasks[0].tool_input = {}

    exec_res = client.post(f"/api/v1/reasoning/plans/{plan_id}/execute")
    assert exec_res.status_code == 200
    completed_plan = exec_res.json()
    assert completed_plan["status"] == "COMPLETE"
    step_execs = completed_plan["subtasks"][0]["tool_executions"]
    assert len(step_execs) == 2
    assert step_execs[0]["success"] is False
    assert step_execs[1]["success"] is True
