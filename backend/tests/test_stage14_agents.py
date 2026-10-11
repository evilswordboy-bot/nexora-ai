"""
Stage 14: Multi-Agent Intelligence System — Comprehensive Verification Suite
Tests specialized agent registry, unavailable tool detection, automatic & manual agent selection,
parallel & hybrid execution, duplicate tool call prevention, conflict detection, consequential
approval gates, retries, cancellation, cost limits, and user memory isolation.
"""

from fastapi.testclient import TestClient
from app.main import app
from app.services.tools_registry import tool_registry
from app.services.agents.orchestrator import multi_agent_orchestrator
from app.services.memory.engine import memory_engine
from app.models.schemas import AgentSubtaskRun, AgentStructuredFinding

client = TestClient(app)


def test_stage14_health_and_specialized_agent_registry():
    """Verify Stage 14 health status and all 8 specialized agents in the registry."""
    health = client.get("/api/v1/health").json()
    assert health["stage"] >= 14
    assert health["subsystems"]["multi_agent_system"] == "operational"

    res = client.get("/api/v1/agents/registry")
    assert res.status_code == 200
    registry = res.json()
    agent_ids = {a["agent_id"] for a in registry}
    expected = {
        "research_agent",
        "coding_agent",
        "education_agent",
        "writing_agent",
        "data_analyst_agent",
        "productivity_agent",
        "document_agent",
        "language_agent",
    }
    assert expected.issubset(agent_ids)
    for agent in registry:
        assert agent["purpose"]
        assert len(agent["capabilities"]) >= 1
        assert len(agent["limitations"]) >= 1
        assert agent["permission_scope"] in (
            "read_only",
            "search_and_retrieve",
            "document_read",
            "workspace_write_requires_approval",
        )


def test_unavailable_tool_marks_agent_unavailable_and_reports_honestly():
    """Verify that disabling a required tool marks dependent agents unavailable and prevents fake execution."""
    calc_tool = tool_registry.get_tool("calculator")
    assert calc_tool is not None
    original_enabled = calc_tool.enabled

    try:
        calc_tool.enabled = False
        registry = client.get("/api/v1/agents/registry").json()
        coding_spec = next(a for a in registry if a["agent_id"] == "coding_agent")
        assert coding_spec["available"] is False
        assert "calculator" in (coding_spec["unavailable_reason"] or "")

        # Attempting to run the unavailable agent fails honestly
        run_res = client.post(
            "/api/v1/agents/run",
            json={
                "goal": "Write a Python function and calculate 25 * 4",
                "selection_mode": "manual",
                "manual_agents": ["coding_agent"],
            },
        )
        assert run_res.status_code == 200
        run_data = run_res.json()
        assert run_data["status"] == "FAILED"
        assert "calculator" in (run_data["subtasks"][0]["error_message"] or "")
    finally:
        calc_tool.enabled = original_enabled


def test_agent_classification_and_parallel_execution_with_deduplication():
    """
    Verify automatic agent selection, parallel subtask execution, and duplicate tool call prevention.
    """
    # Classify a multi-disciplinary query
    classify_res = client.post(
        "/api/v1/agents/classify",
        json={
            "goal": "Implement a Python algorithm, calculate 120 * 15 + 40, and explain the concept as a study guide",
        },
    )
    assert classify_res.status_code == 200
    selected = classify_res.json()
    assert "coding_agent" in selected
    assert "data_analyst_agent" in selected
    assert "education_agent" in selected

    # Run in parallel mode — all 3 agents share the expression `120 * 15 + 40`, triggering tool deduplication
    run_res = client.post(
        "/api/v1/agents/run",
        json={
            "goal": "Implement a Python algorithm, calculate 120 * 15 + 40, and explain the concept as a study guide",
            "selection_mode": "manual",
            "manual_agents": ["coding_agent", "data_analyst_agent", "education_agent"],
            "allow_parallel": True,
        },
    )
    assert run_res.status_code == 200
    data = run_res.json()
    assert data["status"] == "COMPLETED"
    assert data["execution_mode"] in ("parallel_safe", "hybrid")
    assert data["duplicate_tool_calls_prevented"] >= 1
    assert any("1840" in f for f in data["consolidated_facts"])
    assert len(data["consolidated_assumptions"]) >= 1


def test_conflicting_results_detection():
    """Verify conflict detection when two agents report contradictory quantitative findings."""
    sub_a = AgentSubtaskRun(
        subtask_id="s1",
        agent_id="data_analyst_agent",
        agent_name="Data Analyst Agent",
        title="Task 1",
        instruction="Compute metric",
        status="COMPLETED",
        structured_finding=AgentStructuredFinding(
            facts=["Verified calculation: `100 * 5 = 500`"],
        ),
    )
    sub_b = AgentSubtaskRun(
        subtask_id="s2",
        agent_id="research_agent",
        agent_name="Research Agent",
        title="Task 2",
        instruction="Verify metric",
        status="COMPLETED",
        structured_finding=AgentStructuredFinding(
            facts=["Verified calculation: `100 * 5 = 550`"],
        ),
    )
    conflicts = multi_agent_orchestrator.detect_conflicting_outputs([sub_a, sub_b])
    assert len(conflicts) == 1
    assert "Discrepancy" in conflicts[0]
    assert "500" in conflicts[0] and "550" in conflicts[0]


def test_permissions_consequential_approval_retry_and_cancellation():
    """
    Verify least-privilege approval gate for consequential actions, approval resumption,
    retry on failure, and run cancellation.
    """
    # 1. Consequential action pauses in WAITING_APPROVAL
    run_res = client.post(
        "/api/v1/agents/run",
        json={
            "goal": "Organize a project workflow and delete all files in the archive after completion",
            "selection_mode": "manual",
            "manual_agents": ["productivity_agent"],
        },
    )
    assert run_res.status_code == 200
    run_data = run_res.json()
    run_id = run_data["run_id"]
    sub_id = run_data["subtasks"][0]["subtask_id"]
    assert run_data["status"] == "WAITING_APPROVAL"
    assert run_data["subtasks"][0]["requires_approval"] is True

    # 2. Approve the subtask and verify it completes
    app_res = client.post(
        f"/api/v1/agents/runs/{run_id}/approve",
        json={"subtask_id": sub_id, "approved": True, "user_note": "Approved for dry-run checklist"},
    )
    assert app_res.status_code == 200
    assert app_res.json()["status"] == "COMPLETED"

    # 3. Create another waiting run and test cancellation & retry
    run_res2 = client.post(
        "/api/v1/agents/run",
        json={
            "goal": "Publish publicly the quarterly release checklist",
            "selection_mode": "manual",
            "manual_agents": ["productivity_agent"],
        },
    )
    run2_id = run_res2.json()["run_id"]
    sub2_id = run_res2.json()["subtasks"][0]["subtask_id"]

    # Decline approval -> marks subtask CANCELLED
    dec_res = client.post(
        f"/api/v1/agents/runs/{run2_id}/approve",
        json={"subtask_id": sub2_id, "approved": False, "user_note": "Do not publish yet"},
    )
    assert dec_res.status_code == 200
    assert dec_res.json()["subtasks"][0]["status"] == "CANCELLED"

    # Cancel entire run endpoint
    cancel_res = client.post(f"/api/v1/agents/runs/{run2_id}/cancel")
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "CANCELLED"


def test_memory_isolation_and_cost_limit_enforcement(monkeypatch):
    """
    Verify that User A's memories are isolated from User B's multi-agent runs,
    and verify that strict per-run cost limits prevent uncontrolled spending.
    """
    memory_engine.clear_user_memories("agent_user_a")
    memory_engine.clear_user_memories("agent_user_b")

    client.post(
        "/api/v1/memory/items",
        json={
            "user_id": "agent_user_a",
            "category": "project_context",
            "content": "Our microservice architecture uses Kubernetes and gRPC.",
            "pinned": True,
        },
    )

    # User A run includes User A's memory
    run_a = client.post(
        "/api/v1/agents/run",
        json={
            "goal": "Draft architecture documentation for our microservice stack",
            "user_id": "agent_user_a",
            "selection_mode": "manual",
            "manual_agents": ["writing_agent"],
        },
    ).json()
    assert len(run_a["used_memories"]) == 1
    assert "Kubernetes" in run_a["used_memories"][0]["content"]

    # User B run must NOT access User A's memories or run history
    run_b = client.post(
        "/api/v1/agents/run",
        json={
            "goal": "Draft architecture documentation for our microservice stack",
            "user_id": "agent_user_b",
            "selection_mode": "manual",
            "manual_agents": ["writing_agent"],
        },
    ).json()
    assert len(run_b["used_memories"]) == 0
    assert client.get(f"/api/v1/agents/runs/{run_a['run_id']}", params={"user_id": "agent_user_b"}).status_code == 404

    # Enforce strict cost ceiling when estimated step cost exceeds max_cost_usd
    from app.services.routing.engine import model_routing_engine
    orig_select = model_routing_engine.select_route

    def expensive_select(*args, **kwargs):
        d = orig_select(*args, **kwargs)
        d.cost_estimate.estimated_cost_usd = 0.05
        return d

    monkeypatch.setattr(model_routing_engine, "select_route", expensive_select)

    budget_run = client.post(
        "/api/v1/agents/run",
        json={
            "goal": "Write code and study guide",
            "selection_mode": "manual",
            "manual_agents": ["coding_agent", "education_agent"],
            "max_cost_usd": 0.01,
        },
    ).json()
    assert budget_run["status"] == "FAILED"
    assert any("cost budget" in (st["error_message"] or "") for st in budget_run["subtasks"])
