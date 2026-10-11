"""
NEXORA AI — Stage 19: Git & Version Control Engine Tests
Tests:
1. Repository initialization, clean & dirty worktree detection, .gitignore recommendations
2. Staging, unstaging, unified & side-by-side diff generation
3. Commit confirmation gate (WAITING_FOR_APPROVAL -> approve_operation) & commit history
4. Secret & .env file commit blocking (prevent committing secrets or .env files)
5. Branch creation, dirty-worktree branch switch guard, and clean branch switching
6. Branch comparison & merge conflict detection with safe automatic abort
7. Missing Git installation graceful handling (_git_binary_override = "__MISSING__")
8. Remote configuration validation (SSRF/disallowed host blocking) & missing auth token handling on push
9. AI-powered code review distinguishing verified_defect from possible_concern + Stage 18 test integration
10. Collaboration & Pull Request draft preparation (LOCAL_DRAFT_ONLY honesty)
11. ToolRegistry integration (git_repository_inspector & git_safe_commit_and_branch)
"""

import uuid
from fastapi.testclient import TestClient

from app.main import app
from app.services.git.engine import git_version_control_engine

client = TestClient(app)


def _create_isolated_project(label: str = "git_test") -> tuple[str, str]:
    uid = f"user_git_{uuid.uuid4().hex[:8]}"
    resp = client.post(
        "/api/v1/terminal/projects",
        json={
            "user_id": uid,
            "name": f"Repo {label}",
            "template": "python",
            "description": "Stage 19 Git test workspace",
        },
    )
    assert resp.status_code == 200
    pid = resp.json()["project_id"]
    return uid, pid


def _write_file(uid: str, pid: str, relative_path: str, content: str) -> None:
    res = client.post(
        f"/api/v1/terminal/projects/{pid}/files",
        json={
            "user_id": uid,
            "relative_path": relative_path,
            "content": content,
            "create_backup": False,
        },
    )
    assert res.status_code == 200


def test_git_capabilities_and_health():
    res = client.get("/api/v1/git/capabilities")
    assert res.status_code == 200
    data = res.json()
    assert data["stage"] == 19
    assert data["git_installed"] is True
    assert "github.com" in data["allowed_remote_hosts"]

    health = client.get("/api/v1/health").json()
    assert health["stage"] >= 19
    assert health["subsystems"]["git_version_control"] == "operational"


def test_init_clean_and_dirty_repository_and_staging():
    uid, pid = _create_isolated_project("clean_dirty")

    # Before git init
    status_before = client.get("/api/v1/git/status", params={"user_id": uid, "project_id": pid}).json()
    assert status_before["is_initialized"] is False
    assert "__pycache__/" in status_before["recommended_gitignore_entries"]

    # Initialize git repository with initial commit and default .gitignore
    init_res = client.post(
        "/api/v1/git/init",
        json={
            "user_id": uid,
            "project_id": pid,
            "default_branch": "main",
            "create_gitignore": True,
            "initial_commit": True,
        },
    )
    assert init_res.status_code == 200
    init_data = init_res.json()
    assert init_data["status"] == "SUCCEEDED"
    assert init_data["verified"] is True

    # Status should now be clean
    status_clean = client.get("/api/v1/git/status", params={"user_id": uid, "project_id": pid}).json()
    assert status_clean["is_initialized"] is True
    assert status_clean["is_clean"] is True
    assert status_clean["current_branch"] == "main"
    assert len(status_clean["recent_commits"]) == 1

    # Modify main.py to make repository dirty
    _write_file(
        uid,
        pid,
        "main.py",
        'def add(a: int, b: int) -> int:\n    return a + b\n\n\nif __name__ == "__main__":\n    print(add(10, 20))\n',
    )

    status_dirty = client.get("/api/v1/git/status", params={"user_id": uid, "project_id": pid}).json()
    assert status_dirty["is_clean"] is False
    assert any(f["path"] == "main.py" and f["unstaged"] is True for f in status_dirty["changed_files"])

    # Inspect working tree diff (unified + side-by-side)
    diff_res = client.get(
        "/api/v1/git/diff",
        params={"user_id": uid, "project_id": pid, "scope": "all_working"},
    )
    assert diff_res.status_code == 200
    diff_data = diff_res.json()
    assert len(diff_data["files"]) == 1
    assert diff_data["files"][0]["file_path"] == "main.py"
    assert diff_data["total_additions"] >= 1
    assert len(diff_data["files"][0]["side_by_side_lines"]) > 0

    # Stage main.py and verify staged status, then unstage
    stage_res = client.post(
        "/api/v1/git/stage",
        json={"user_id": uid, "project_id": pid, "paths": ["main.py"]},
    ).json()
    assert stage_res["status"] == "SUCCEEDED"

    status_staged = client.get("/api/v1/git/status", params={"user_id": uid, "project_id": pid}).json()
    assert status_staged["staged_count"] >= 1
    assert any(f["path"] == "main.py" and f["staged"] is True for f in status_staged["changed_files"])

    unstage_res = client.post(
        "/api/v1/git/unstage",
        json={"user_id": uid, "project_id": pid, "paths": ["main.py"]},
    ).json()
    assert unstage_res["status"] == "SUCCEEDED"


def test_commit_confirmation_gate_and_secret_blocking():
    uid, pid = _create_isolated_project("commit_gate")
    client.post("/api/v1/git/init", json={"user_id": uid, "project_id": pid})

    # 1. Attempting to stage/commit a secret must be BLOCKED
    _write_file(
        uid,
        pid,
        "config_secret.py",
        'OPENAI_API_KEY = "sk-1234567890abcdefghijklmnopqrstuvwx"\n',
    )
    blocked_commit = client.post(
        "/api/v1/git/commit",
        json={
            "user_id": uid,
            "project_id": pid,
            "message": "feat: add config",
            "stage_all": True,
            "confirmed": True,
        },
    ).json()
    assert blocked_commit["status"] == "BLOCKED"
    assert blocked_commit["verified"] is False
    assert "secret" in (blocked_commit["error_message"] or "").lower()

    # Overwrite with safe content
    _write_file(
        uid,
        pid,
        "config_secret.py",
        'import os\nAPI_KEY = os.getenv("API_KEY", "")\n',
    )

    # 2. Request commit with confirmed=False -> WAITING_FOR_APPROVAL
    pending_commit = client.post(
        "/api/v1/git/commit",
        json={
            "user_id": uid,
            "project_id": pid,
            "message": "feat: add safe env config",
            "stage_all": True,
            "confirmed": False,
        },
    ).json()
    assert pending_commit["status"] == "WAITING_FOR_APPROVAL"
    assert pending_commit["requires_approval"] is True
    op_id = pending_commit["operation_id"]

    # 3. Approve operation -> SUCCEEDED with verified commit hash
    approved = client.post(
        f"/api/v1/git/operations/{op_id}/approve",
        json={"user_id": uid, "approved": True},
    ).json()
    assert approved["status"] == "SUCCEEDED"
    assert approved["verified"] is True
    assert approved["result_data"].get("commit_hash") is not None

    commits_res = client.get("/api/v1/git/commits", params={"user_id": uid, "project_id": pid}).json()
    assert commits_res["total"] >= 2
    assert commits_res["commits"][0]["subject"] == "feat: add safe env config"


def test_branch_creation_dirty_switch_guard_and_merge_conflict():
    uid, pid = _create_isolated_project("branches_merge")
    client.post("/api/v1/git/init", json={"user_id": uid, "project_id": pid, "default_branch": "main"})

    # Create and switch to feature/calc
    b_create = client.post(
        "/api/v1/git/branches",
        json={
            "user_id": uid,
            "project_id": pid,
            "action": "create",
            "branch_name": "feature/calc",
            "checkout_on_create": True,
            "confirmed": True,
        },
    ).json()
    assert b_create["status"] == "SUCCEEDED"

    # Dirty the working tree and attempt to switch back to main -> BLOCKED
    _write_file(
        uid,
        pid,
        "main.py",
        'def add(a: int, b: int) -> int:\n    return a + b + 100\n',
    )
    dirty_switch = client.post(
        "/api/v1/git/branches",
        json={
            "user_id": uid,
            "project_id": pid,
            "action": "switch",
            "branch_name": "main",
            "confirmed": True,
        },
    ).json()
    assert dirty_switch["status"] == "BLOCKED"
    assert "uncommitted" in (dirty_switch["error_message"] or "").lower()

    # Commit the change on feature/calc
    client.post(
        "/api/v1/git/commit",
        json={
            "user_id": uid,
            "project_id": pid,
            "message": "feat: update add on feature branch",
            "stage_all": True,
            "confirmed": True,
        },
    )

    # Switch back to main cleanly
    clean_switch = client.post(
        "/api/v1/git/branches",
        json={
            "user_id": uid,
            "project_id": pid,
            "action": "switch",
            "branch_name": "main",
            "confirmed": True,
        },
    ).json()
    assert clean_switch["status"] == "SUCCEEDED"

    # Modify the exact same file on main to create a merge conflict
    _write_file(
        uid,
        pid,
        "main.py",
        'def add(a: int, b: int) -> int:\n    return a + b + 999\n',
    )
    client.post(
        "/api/v1/git/commit",
        json={
            "user_id": uid,
            "project_id": pid,
            "message": "feat: conflicting change on main",
            "stage_all": True,
            "confirmed": True,
        },
    )

    # Compare branches -> should detect divergence
    comp = client.get(
        "/api/v1/git/compare",
        params={
            "user_id": uid,
            "project_id": pid,
            "base_branch": "main",
            "compare_branch": "feature/calc",
        },
    ).json()
    assert comp["ahead_count"] == 1
    assert comp["behind_count"] == 1

    # Attempt merge -> should detect merge conflict and safely abort so worktree stays clean
    merge_res = client.post(
        "/api/v1/git/branches",
        json={
            "user_id": uid,
            "project_id": pid,
            "action": "merge",
            "branch_name": "feature/calc",
            "confirmed": True,
        },
    ).json()
    assert merge_res["status"] == "FAILED"
    assert "conflict" in (merge_res["error_message"] or "").lower()

    status_after_conflict = client.get("/api/v1/git/status", params={"user_id": uid, "project_id": pid}).json()
    assert status_after_conflict["is_clean"] is True


def test_missing_git_installation_simulation():
    uid, pid = _create_isolated_project("missing_git")
    git_version_control_engine._git_binary_override = "__MISSING__"
    try:
        caps = client.get("/api/v1/git/capabilities").json()
        assert caps["git_installed"] is False

        status = client.get("/api/v1/git/status", params={"user_id": uid, "project_id": pid}).json()
        assert status["git_installed"] is False
        assert status["is_initialized"] is False

        init_op = client.post("/api/v1/git/init", json={"user_id": uid, "project_id": pid}).json()
        assert init_op["status"] == "FAILED"
        assert "not installed" in (init_op["error_message"] or "").lower()
    finally:
        git_version_control_engine._git_binary_override = None


def test_remote_validation_and_missing_auth_token():
    uid, pid = _create_isolated_project("remote_sync")
    client.post("/api/v1/git/init", json={"user_id": uid, "project_id": pid})

    # 1. Invalid/SSRF remote host is rejected
    bad_remote = client.post(
        "/api/v1/git/remotes",
        json={
            "user_id": uid,
            "project_id": pid,
            "name": "origin",
            "url": "http://169.254.169.254/latest/meta-data",
            "provider": "custom",
        },
    )
    assert bad_remote.status_code == 400

    # 2. Valid GitHub remote URL succeeds
    good_remote = client.post(
        "/api/v1/git/remotes",
        json={
            "user_id": uid,
            "project_id": pid,
            "name": "origin",
            "url": "https://github.com/nexora-ai/demo-repo.git",
            "provider": "github",
        },
    ).json()
    assert good_remote["status"] == "SUCCEEDED"

    # 3. Force push is strictly BLOCKED
    force_push = client.post(
        "/api/v1/git/sync",
        json={
            "user_id": uid,
            "project_id": pid,
            "action": "push",
            "remote_name": "origin",
            "branch": "main",
            "force": True,
            "confirmed": True,
        },
    ).json()
    assert force_push["status"] == "BLOCKED"
    assert "force-push" in (force_push["error_message"] or "").lower()

    # 4. Push without configured GIT_PROVIDER_TOKEN fails with clear auth message
    no_token_push = client.post(
        "/api/v1/git/sync",
        json={
            "user_id": uid,
            "project_id": pid,
            "action": "push",
            "remote_name": "origin",
            "branch": "main",
            "confirmed": True,
        },
    ).json()
    assert no_token_push["status"] == "FAILED"
    assert "token" in (no_token_push["error_message"] or "").lower()


def test_ai_code_review_and_local_pr_draft_honesty():
    uid, pid = _create_isolated_project("review_pr")
    client.post("/api/v1/git/init", json={"user_id": uid, "project_id": pid})

    # Write a file with an eval security defect + TODO marker (while keeping starter functions so unit tests pass)
    status_before = client.get("/api/v1/git/status", params={"user_id": uid, "project_id": pid}).json()
    assert status_before["is_initialized"] is True

    # Read existing main.py and append a function with eval() and a TODO comment
    proj_info = client.get(f"/api/v1/terminal/projects/{pid}", params={"user_id": uid}).json()
    orig_main = next(f["content"] for f in proj_info["files"] if f["relative_path"] == "main.py")
    _write_file(
        uid,
        pid,
        "main.py",
        orig_main
        + "\n\ndef unsafe_helper(expr: str):\n    # TODO: remove dynamic eval\n    return eval(expr)\n",
    )

    review_res = client.post(
        "/api/v1/git/review",
        json={
            "user_id": uid,
            "project_id": pid,
            "run_stage18_tests": True,
        },
    )
    assert review_res.status_code == 200
    rev_data = review_res.json()
    assert rev_data["verified_defects_count"] >= 1
    assert rev_data["possible_concerns_count"] >= 1
    finding_types = {f["finding_type"] for f in rev_data["findings"]}
    assert "verified_defect" in finding_types
    assert "possible_concern" in finding_types
    assert rev_data["tests_executed"] is True
    assert rev_data["tests_passed"] is True

    # Create a local Pull Request draft (honestly labeled LOCAL_DRAFT_ONLY)
    pr_res = client.post(
        "/api/v1/git/pull-requests",
        json={
            "user_id": uid,
            "project_id": pid,
            "title": "feat: calculation engine improvements",
            "description": "Adds helper and review summary",
            "source_branch": "main",
            "target_branch": "main",
            "issue_references": ["#19", "NEX-101"],
            "submit_to_remote": False,
        },
    )
    assert pr_res.status_code == 200
    pr_data = pr_res.json()
    assert pr_data["status"] == "LOCAL_DRAFT_ONLY"
    assert pr_data["local_draft_only"] is True
    assert pr_data["remote_confirmed"] is False
    assert "#19" in pr_data["issue_references"]


def test_stage19_tools_in_tool_registry():
    import asyncio
    from app.services.tools_registry import tool_registry

    uid, pid = _create_isolated_project("tools_reg")
    client.post("/api/v1/git/init", json={"user_id": uid, "project_id": pid})

    tools = client.get("/api/v1/reasoning/tools").json()
    tool_names = {t["name"] for t in tools}
    assert "git_repository_inspector" in tool_names
    assert "git_safe_commit_and_branch" in tool_names

    res_status = asyncio.run(
        tool_registry.execute(
            "git_repository_inspector",
            {"action": "status", "user_id": uid, "project_id": pid},
        )
    )
    assert res_status["success"] is True
    assert res_status["data"]["is_initialized"] is True

    res_branch = asyncio.run(
        tool_registry.execute(
            "git_safe_commit_and_branch",
            {"action": "create_branch", "user_id": uid, "project_id": pid, "branch_name": "feature/tool-branch"},
            approval_granted=True,
        )
    )
    assert res_branch["success"] is True
    assert res_branch["data"]["status"] == "SUCCEEDED"

