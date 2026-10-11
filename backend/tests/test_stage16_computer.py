from fastapi.testclient import TestClient

from app.main import app
from app.services.tools_registry import tool_registry

client = TestClient(app)


def test_stage16_health_and_capabilities_disclosure():
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    data = res.json()
    assert data["stage"] >= 16
    assert data["subsystems"]["computer_control"] == "operational"

    cap_res = client.get("/api/v1/computer/capabilities")
    assert cap_res.status_code == 200
    caps = cap_res.json()
    assert "open_url" in caps["browser_capabilities"]
    assert "list_workspace_files" in caps["local_os_capabilities"]
    assert "separated" in caps["architecture_disclosure"].lower()


def test_stage16_browser_navigation_dom_interaction_secret_masking_and_screenshots():
    create_res = client.post(
        "/api/v1/computer/sessions",
        json={
            "user_id": "browser_user_16",
            "goal": "Open Example Domain, fill search and password, select category, scroll, and capture screenshot",
            "mode": "execute",
            "target_domain": "browser",
            "target_url": "https://example.com",
            "steps": [
                {
                    "step_id": "s1_open",
                    "title": "Open Example Portal",
                    "target_domain": "browser",
                    "action_type": "open_url",
                    "target_url_or_path": "https://example.com",
                    "checkpoint_name": "portal_opened",
                },
                {
                    "step_id": "s2_fill_query",
                    "title": "Enter Search Query",
                    "target_domain": "browser",
                    "action_type": "fill_text",
                    "selector": "#search-input",
                    "input_value": "Nexora Stage 16 Verification",
                },
                {
                    "step_id": "s3_fill_pass",
                    "title": "Enter Password (Must Redact)",
                    "target_domain": "browser",
                    "action_type": "fill_text",
                    "selector": "#user-password",
                    "input_value": "SuperSecretPassword123!",
                },
                {
                    "step_id": "s4_select",
                    "title": "Select Category",
                    "target_domain": "browser",
                    "action_type": "select_option",
                    "selector": "#category-select",
                    "input_value": "security",
                },
                {
                    "step_id": "s5_scroll",
                    "title": "Scroll Viewport Down",
                    "target_domain": "browser",
                    "action_type": "scroll",
                    "params": {"direction": "down", "pixels": 320},
                },
                {
                    "step_id": "s6_extract",
                    "title": "Extract Page Heading",
                    "target_domain": "browser",
                    "action_type": "extract_content",
                    "selector": "h1, p",
                },
                {
                    "step_id": "s7_click",
                    "title": "Click More Info Link",
                    "target_domain": "browser",
                    "action_type": "click",
                    "selector": "#more-info-link",
                    "checkpoint_name": "navigated_to_subpage",
                },
            ],
        },
    )
    assert create_res.status_code == 200
    session = create_res.json()
    assert session["status"] == "VERIFIED_COMPLETED"
    assert session["verified_completion"] is True
    assert "portal_opened" in session["checkpoints"]
    assert "navigated_to_subpage" in session["checkpoints"]
    assert session["latest_screenshot_base64"].startswith("data:image/png;base64,")

    # Verify password was redacted from step results and execution logs
    pass_step = session["step_results"][2]
    assert "SuperSecretPassword123!" not in pass_step["output_summary"]
    assert "[REDACTED_SECRET]" in pass_step["output_summary"]
    assert all("SuperSecretPassword123!" not in log for log in session["execution_logs"])

    # Verify untrusted webpage content isolation
    extract_step = session["step_results"][5]
    assert extract_step["untrusted_content_isolated"] is True
    assert "<untrusted_webpage_content" in extract_step["output_summary"]


def test_stage16_form_submission_approval_gate_and_rejection():
    create_res = client.post(
        "/api/v1/computer/sessions",
        json={
            "user_id": "form_user_16",
            "goal": "Open Example and submit form",
            "target_domain": "browser",
            "steps": [
                {
                    "step_id": "s1_open",
                    "title": "Open Page",
                    "target_domain": "browser",
                    "action_type": "open_url",
                    "target_url_or_path": "https://example.com",
                },
                {
                    "step_id": "s2_submit",
                    "title": "Submit Form",
                    "target_domain": "browser",
                    "action_type": "submit_form",
                    "selector": "#search-form",
                },
            ],
        },
    )
    assert create_res.status_code == 200
    paused = create_res.json()
    assert paused["status"] == "WAITING_FOR_APPROVAL"
    assert paused["waiting_approval_step_id"] == "s2_submit"
    assert paused["verified_completion"] is False
    sid = paused["session_id"]

    # Approve and verify completion
    app_res = client.post(
        f"/api/v1/computer/sessions/{sid}/approve",
        json={"user_id": "form_user_16", "step_id": "s2_submit", "approved": True},
    )
    assert app_res.status_code == 200
    done = app_res.json()
    assert done["status"] == "VERIFIED_COMPLETED"
    assert done["verified_completion"] is True


def test_stage16_blocked_urls_ssrf_and_captcha_mfa_boundaries():
    # 1. Block loopback / private LAN URL
    ssrf_res = client.post(
        "/api/v1/computer/sessions",
        json={
            "user_id": "sec_user",
            "goal": "Attempt internal loopback access",
            "target_domain": "browser",
            "steps": [
                {
                    "step_id": "s1_loopback",
                    "title": "Open Loopback",
                    "target_domain": "browser",
                    "action_type": "open_url",
                    "target_url_or_path": "http://127.0.0.1:8000/api/v1/health",
                }
            ],
        },
    )
    assert ssrf_res.status_code == 200
    sdata = ssrf_res.json()
    assert sdata["status"] == "BLOCKED_BY_SECURITY_BOUNDARY"
    assert sdata["verified_completion"] is False

    # 2. Block CAPTCHA wall without bypassing
    captcha_res = client.post(
        "/api/v1/computer/sessions",
        json={
            "user_id": "sec_user",
            "goal": "Open page with CAPTCHA challenge",
            "target_domain": "browser",
            "steps": [
                {
                    "step_id": "s1_captcha",
                    "title": "Open CAPTCHA Page",
                    "target_domain": "browser",
                    "action_type": "open_url",
                    "target_url_or_path": "https://example.com/captcha-wall",
                }
            ],
        },
    )
    assert captcha_res.status_code == 200
    cdata = captcha_res.json()
    assert cdata["status"] == "BLOCKED_BY_SECURITY_BOUNDARY"
    assert cdata["step_results"][0]["security_boundary_triggered"] == "CAPTCHA_OR_MFA_CHALLENGE"


def test_stage16_sandboxed_local_workspace_files_and_traversal_defense():
    # 1. Write, read, and delete inside sandbox (delete requires approval)
    res = client.post(
        "/api/v1/computer/sessions",
        json={
            "user_id": "local_user",
            "goal": "Create and read sandbox note, then delete with approval",
            "target_domain": "local_os",
            "steps": [
                {
                    "step_id": "s1_write",
                    "title": "Write Sandbox Note",
                    "target_domain": "local_os",
                    "action_type": "write_workspace_file",
                    "target_url_or_path": "stage16_note.txt",
                    "input_value": "Verified local sandbox file content.",
                },
                {
                    "step_id": "s2_read",
                    "title": "Read Sandbox Note",
                    "target_domain": "local_os",
                    "action_type": "read_workspace_file",
                    "target_url_or_path": "stage16_note.txt",
                },
                {
                    "step_id": "s3_delete",
                    "title": "Delete Sandbox Note",
                    "target_domain": "local_os",
                    "action_type": "delete_workspace_file",
                    "target_url_or_path": "stage16_note.txt",
                },
            ],
        },
    )
    assert res.status_code == 200
    paused = res.json()
    assert paused["status"] == "WAITING_FOR_APPROVAL"
    assert paused["waiting_approval_step_id"] == "s3_delete"
    assert "<untrusted_local_file_content" in paused["step_results"][1]["output_summary"]

    # Approve deletion
    app_res = client.post(
        f"/api/v1/computer/sessions/{paused['session_id']}/approve",
        json={"user_id": "local_user", "step_id": "s3_delete", "approved": True},
    )
    assert app_res.status_code == 200
    assert app_res.json()["status"] == "VERIFIED_COMPLETED"

    # 2. Block path traversal outside sandbox
    trav_res = client.post(
        "/api/v1/computer/sessions",
        json={
            "user_id": "local_user",
            "goal": "Attempt path traversal",
            "target_domain": "local_os",
            "steps": [
                {
                    "step_id": "s1_traverse",
                    "title": "Read Outside Sandbox",
                    "target_domain": "local_os",
                    "action_type": "read_workspace_file",
                    "target_url_or_path": "../../.env",
                }
            ],
        },
    )
    assert trav_res.status_code == 200
    assert trav_res.json()["status"] == "BLOCKED_BY_SECURITY_BOUNDARY"


def test_stage16_simulation_mode_session_isolation_and_tool_registry():
    import asyncio

    # 1. Simulation preview mode
    sim_res = client.post(
        "/api/v1/computer/sessions",
        json={
            "user_id": "sim_user",
            "goal": "Preview browser workflow without executing",
            "mode": "simulate_only",
            "target_domain": "browser",
            "target_url": "https://example.com",
        },
    )
    assert sim_res.status_code == 200
    sim_data = sim_res.json()
    assert sim_data["status"] == "SIMULATION_PREVIEW"
    assert sim_data["verified_completion"] is False

    # 2. ToolRegistry integration for Stage 11/14/15
    tool_names = {t.name for t in tool_registry.list_tools()}
    assert "browser_automation_step" in tool_names
    assert "computer_workspace_task" in tool_names

    b_out = asyncio.run(
        tool_registry.execute(
            "browser_automation_step",
            {"url": "https://example.com", "selector": "h1"},
        )
    )
    assert b_out["success"] is True
    assert b_out["data"]["verified"] is True
