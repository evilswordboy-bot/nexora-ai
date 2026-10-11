import asyncio
import uuid
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.services.documents.storage import document_storage
from app.services.files.engine import file_workspace_engine
from app.services.tools_registry import tool_registry

client = TestClient(app)


def test_stage17_health_and_capabilities_disclosure():
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    data = res.json()
    assert data["stage"] >= 17
    assert data["subsystems"]["file_workspace"] == "operational"

    cap_res = client.get("/api/v1/files/capabilities", params={"user_id": "cap_test_user"})
    assert cap_res.status_code == 200
    caps = cap_res.json()
    assert caps["stage"] == 17
    assert ".docx" in caps["allowed_extensions"]
    assert ".xlsx" in caps["allowed_extensions"]
    assert any("symlink" in b.lower() for b in caps["security_boundaries"])
    assert any("untrusted_file_content" in b for b in caps["security_boundaries"])


def test_stage17_path_traversal_permission_failures_and_symlink_escapes():
    uid = f"sec_user_{uuid.uuid4().hex[:8]}"

    # 1. Parent directory traversal '..' blocked
    for bad_path in ["../secret.txt", "notes/../../etc/passwd", "..\\..\\Windows\\win.ini"]:
        r = client.get("/api/v1/files/read", params={"user_id": uid, "path": bad_path})
        assert r.status_code == 403
        assert "traversal" in r.json()["detail"].lower() or "boundary" in r.json()["detail"].lower()

    # 2. Absolute paths and drive letters blocked
    for abs_path in ["C:\\Windows\\System32\\cmd.exe", "/etc/shadow", "\\\\server\\share\\file.txt"]:
        r = client.get("/api/v1/files/read", params={"user_id": uid, "path": abs_path})
        assert r.status_code == 403

    # 3. Internal protected folders (.nexora_trash, .nexora_versions) and credential files (.env, id_rsa) blocked
    for protected in [".nexora_trash/item.txt", ".nexora_versions/v1.txt", ".env", "keys/id_rsa"]:
        r = client.post(
            "/api/v1/files/write",
            json={"user_id": uid, "relative_path": protected, "content": "test"},
        )
        assert r.status_code == 403

    # 4. Forbidden executable extensions (.exe, .ps1, .bat) blocked
    for bad_ext in ["malware.exe", "script.ps1", "runner.bat"]:
        r = client.post(
            "/api/v1/files/write",
            json={"user_id": uid, "relative_path": bad_ext, "content": "echo hi"},
        )
        assert r.status_code == 403

    # 5. Symbolic link escape detection
    user_root = file_workspace_engine.get_user_workspace_root(uid)
    dummy_target = user_root / "symlink_probe.txt"
    dummy_target.write_text("probe", encoding="utf-8")
    with patch.object(Path, "is_symlink", return_value=True):
        try:
            file_workspace_engine.resolve_safe_path(uid, "symlink_probe.txt")
            assert False, "Expected PermissionError for symbolic link escape"
        except PermissionError as exc:
            assert "symbolic link" in str(exc).lower()


def test_stage17_file_creation_editing_version_history_and_backup_restoration():
    uid = f"version_user_{uuid.uuid4().hex[:8]}"

    # Create a new Markdown file
    create_res = client.post(
        "/api/v1/files/write",
        json={
            "user_id": uid,
            "relative_path": "docs/architecture.md",
            "content": "# Version 1 Architecture\nInitial verified content.",
            "overwrite": False,
        },
    )
    assert create_res.status_code == 200
    op1 = create_res.json()
    assert op1["status"] == "VERIFIED_SUCCEEDED"
    assert op1["verified"] is True
    v1_sha = op1["result_data"]["sha256_hash"]

    # Attempting to write again with overwrite=False must fail with 409 Conflict
    conflict_res = client.post(
        "/api/v1/files/write",
        json={
            "user_id": uid,
            "relative_path": "docs/architecture.md",
            "content": "Unapproved overwrite",
            "overwrite": False,
        },
    )
    assert conflict_res.status_code == 409

    # Attempting to overwrite with overwrite=True, confirmed_overwrite=False must enter WAITING_FOR_APPROVAL
    pending_res = client.post(
        "/api/v1/files/write",
        json={
            "user_id": uid,
            "relative_path": "docs/architecture.md",
            "content": "# Version 2 Architecture\nUpdated content after approval.",
            "overwrite": True,
            "confirmed_overwrite": False,
        },
    )
    assert pending_res.status_code == 200
    pending_op = pending_res.json()
    assert pending_op["status"] == "WAITING_FOR_APPROVAL"
    assert pending_op["requires_approval"] is True

    # Original file must still have Version 1 content while waiting for approval
    read_before = client.get("/api/v1/files/read", params={"user_id": uid, "path": "docs/architecture.md"}).json()
    assert "Version 1 Architecture" in read_before["content"]
    assert "<untrusted_file_content" in read_before["quarantined_content"]

    # Approve the overwrite operation
    approve_res = client.post(
        f"/api/v1/files/operations/{pending_op['operation_id']}/approve",
        json={"user_id": uid, "approved": True, "user_note": "Approved v2 update"},
    )
    assert approve_res.status_code == 200
    approved_op = approve_res.json()
    assert approved_op["status"] == "VERIFIED_SUCCEEDED"
    assert approved_op["result_data"]["backup_version_number"] == 1
    backup_ver_id = approved_op["result_data"]["backup_version_id"]

    # Read updated file and verify version history has 1 backup snapshot
    read_after = client.get("/api/v1/files/read", params={"user_id": uid, "path": "docs/architecture.md"}).json()
    assert "Version 2 Architecture" in read_after["content"]
    assert len(read_after["versions"]) == 1
    assert read_after["versions"][0]["sha256_hash"] == v1_sha

    # Restore Version 1 from backup snapshot and verify SHA-256 matches original v1_sha
    restore_res = client.post(
        f"/api/v1/files/versions/{backup_ver_id}/restore",
        json={"user_id": uid, "relative_path": "docs/architecture.md"},
    )
    assert restore_res.status_code == 200
    restored_op = restore_res.json()
    assert restored_op["status"] == "VERIFIED_SUCCEEDED"
    assert restored_op["result_data"]["sha256_hash"] == v1_sha

    read_restored = client.get("/api/v1/files/read", params={"user_id": uid, "path": "docs/architecture.md"}).json()
    assert "Version 1 Architecture" in read_restored["content"]


def test_stage17_format_conversions_and_content_search():
    uid = f"convert_user_{uuid.uuid4().hex[:8]}"

    # 1. Create a CSV dataset
    csv_content = "feature,owner,priority\nFile Engine,Alice,High\nDuplicate Scanner,Bob,Medium\n"
    r1 = client.post(
        "/api/v1/files/write",
        json={
            "user_id": uid,
            "relative_path": "data/roadmap.csv",
            "content": csv_content,
            "overwrite": True,
            "confirmed_overwrite": True,
        },
    )
    assert r1.status_code == 200

    # 2. Convert CSV -> JSON
    conv_json = client.post(
        "/api/v1/files/convert",
        json={
            "user_id": uid,
            "source_path": "data/roadmap.csv",
            "target_format": "json",
            "overwrite": True,
            "confirmed_overwrite": True,
        },
    )
    assert conv_json.status_code == 200
    assert conv_json.json()["verified"] is True
    json_read = client.get("/api/v1/files/read", params={"user_id": uid, "path": "data/roadmap.json"}).json()
    assert "Duplicate Scanner" in json_read["content"]

    # 3. Convert CSV -> XLSX spreadsheet
    conv_xlsx = client.post(
        "/api/v1/files/convert",
        json={
            "user_id": uid,
            "source_path": "data/roadmap.csv",
            "target_format": "xlsx",
            "overwrite": True,
            "confirmed_overwrite": True,
        },
    )
    assert conv_xlsx.status_code == 200
    assert conv_xlsx.json()["verified"] is True

    # 4. Create Markdown and convert MD -> DOCX -> TXT
    client.post(
        "/api/v1/files/write",
        json={
            "user_id": uid,
            "relative_path": "notes/handbook.md",
            "content": "# Security Handbook\nUniqueTokenAlpha992 is documented inside this DOCX file.",
            "overwrite": True,
            "confirmed_overwrite": True,
        },
    )
    conv_docx = client.post(
        "/api/v1/files/convert",
        json={
            "user_id": uid,
            "source_path": "notes/handbook.md",
            "target_format": "docx",
            "overwrite": True,
            "confirmed_overwrite": True,
        },
    )
    assert conv_docx.status_code == 200

    conv_txt = client.post(
        "/api/v1/files/convert",
        json={
            "user_id": uid,
            "source_path": "notes/handbook.docx",
            "target_format": "txt",
            "overwrite": True,
            "confirmed_overwrite": True,
        },
    )
    assert conv_txt.status_code == 200

    # 5. Search inside indexed DOCX / TXT content
    search_res = client.post(
        "/api/v1/files/search",
        json={
            "user_id": uid,
            "query": "UniqueTokenAlpha992",
            "extensions": [".docx"],
            "search_content": True,
        },
    )
    assert search_res.status_code == 200
    s_data = search_res.json()
    assert s_data["total_matches"] == 1
    assert s_data["items"][0]["relative_path"] == "notes/handbook.docx"


def test_stage17_duplicate_detection_trash_recovery_and_large_file_limits():
    uid = f"dup_user_{uuid.uuid4().hex[:8]}"
    identical_payload = "Identical report content for SHA-256 deduplication test.\n" * 10

    for rel_p in ["reports/orig.txt", "reports/copy_1.txt", "archive/copy_2.txt"]:
        client.post(
            "/api/v1/files/write",
            json={
                "user_id": uid,
                "relative_path": rel_p,
                "content": identical_payload,
                "overwrite": True,
                "confirmed_overwrite": True,
            },
        )

    dups_res = client.get("/api/v1/files/duplicates", params={"user_id": uid})
    assert dups_res.status_code == 200
    groups = dups_res.json()
    assert len(groups) >= 1
    grp = groups[0]
    assert grp["duplicate_count"] == 2
    assert grp["wasted_bytes"] == grp["size_bytes"] * 2

    # Unconfirmed cleanup must pause for approval
    cleanup_pending = client.post(
        "/api/v1/files/duplicates/cleanup",
        json={"user_id": uid, "confirmed": False},
    ).json()
    assert cleanup_pending["status"] == "WAITING_FOR_APPROVAL"

    # Approve duplicate cleanup
    cleanup_approved = client.post(
        f"/api/v1/files/operations/{cleanup_pending['operation_id']}/approve",
        json={"user_id": uid, "approved": True},
    ).json()
    assert cleanup_approved["status"] == "VERIFIED_SUCCEEDED"
    assert cleanup_approved["result_data"]["duplicates_removed"] == 2

    # Verify duplicates are now in Recoverable Trash and can be restored
    trash_list = client.get("/api/v1/files/trash", params={"user_id": uid}).json()
    assert len(trash_list) >= 2
    first_trash_id = trash_list[0]["trash_id"]

    restore_trash_res = client.post(
        f"/api/v1/files/trash/{first_trash_id}/restore",
        params={"user_id": uid},
    )
    assert restore_trash_res.status_code == 200
    assert restore_trash_res.json()["verified"] is True

    # Test large file rejection when exceeding configured limit
    with patch.object(settings, "file_workspace_max_file_size_bytes", 64):
        large_res = client.post(
            "/api/v1/files/write",
            json={
                "user_id": uid,
                "relative_path": "too_large.txt",
                "content": "X" * 200,
            },
        )
        assert large_res.status_code == 400
        assert "exceeds workspace limit" in large_res.json()["detail"].lower()


def test_stage17_bulk_organization_preview_approval_and_rollback():
    uid = f"org_user_{uuid.uuid4().hex[:8]}"

    # Seed root files of different categories
    client.post(
        "/api/v1/files/write",
        json={
            "user_id": uid,
            "relative_path": "helper.py",
            "content": "def add(a, b):\n    return a + b\n",
            "overwrite": True,
            "confirmed_overwrite": True,
        },
    )

    # 1. Preview organization without moving files
    preview_res = client.post(
        "/api/v1/files/organize",
        json={"user_id": uid, "strategy": "by_category", "preview_only": True},
    )
    assert preview_res.status_code == 200
    assert preview_res.json()["status"] == "SIMULATED"
    assert preview_res.json()["preview"]["affected_count"] >= 3

    # 2. Request organization without confirmation -> WAITING_FOR_APPROVAL
    org_pending = client.post(
        "/api/v1/files/organize",
        json={"user_id": uid, "strategy": "by_category", "preview_only": False, "confirmed": False},
    ).json()
    assert org_pending["status"] == "WAITING_FOR_APPROVAL"

    # 3. Execute confirmed organization
    org_exec = client.post(
        "/api/v1/files/organize",
        json={"user_id": uid, "strategy": "by_category", "preview_only": False, "confirmed": True},
    ).json()
    assert org_exec["status"] == "VERIFIED_SUCCEEDED"
    assert org_exec["rollback_supported"] is True

    # Verify helper.py moved to Code/helper.py
    code_read = client.get("/api/v1/files/read", params={"user_id": uid, "path": "Code/helper.py"})
    assert code_read.status_code == 200

    # 4. Rollback the bulk organization and verify helper.py is back at root
    rb_res = client.post(
        f"/api/v1/files/operations/{org_exec['operation_id']}/rollback",
        params={"user_id": uid},
    )
    assert rb_res.status_code == 200
    assert rb_res.json()["status"] == "ROLLED_BACK"
    assert rb_res.json()["rolled_back"] is True

    root_read = client.get("/api/v1/files/read", params={"user_id": uid, "path": "helper.py"})
    assert root_read.status_code == 200


def test_stage17_stage4_vault_sync_stage16_browser_import_and_tool_registry():
    uid = f"bridge_user_{uuid.uuid4().hex[:8]}"

    # 1. Sync a workspace file into Stage 4 Document Intelligence Vault
    sync_res = client.post(
        "/api/v1/files/sync-stage4",
        json={"user_id": uid, "relative_path": "quarterly_metrics.csv"},
    )
    assert sync_res.status_code == 200
    sync_data = sync_res.json()
    assert sync_data["verified"] is True
    synced_doc_id = sync_data["result_data"]["doc_id"]
    assert synced_doc_id.startswith("doc_")
    document_storage.delete_document(synced_doc_id)

    # 2. Create a Stage 16 Browser Session and import it into Stage 17 File Workspace
    b_sess = client.post(
        "/api/v1/computer/sessions",
        json={
            "user_id": uid,
            "goal": "Open Example Domain for Stage 17 import",
            "target_domain": "browser",
            "target_url": "https://example.com",
            "steps": [
                {
                    "step_id": "s1",
                    "title": "Open Example",
                    "target_domain": "browser",
                    "action_type": "open_url",
                    "target_url_or_path": "https://example.com",
                }
            ],
        },
    ).json()

    imp_res = client.post(
        "/api/v1/files/import-browser-session",
        json={
            "user_id": uid,
            "session_id": b_sess["session_id"],
            "target_filename": "captures/example_capture.md",
        },
    )
    assert imp_res.status_code == 200
    assert imp_res.json()["verified"] is True

    # 3. Verify Stage 17 tools in ToolRegistry
    mgr_res = asyncio.run(
        tool_registry.execute(
            "workspace_file_manager",
            {"action": "list", "user_id": uid},
        )
    )
    assert mgr_res["success"] is True
    assert mgr_res["untrusted_content_quarantined"] is True

    # Consequential bulk tool must raise PermissionError without approval_granted=True
    try:
        asyncio.run(
            tool_registry.execute(
                "workspace_bulk_organizer",
                {"action": "cleanup_duplicates", "user_id": uid},
                approval_granted=False,
            )
        )
        assert False, "Expected PermissionError when approval_granted=False"
    except PermissionError:
        pass

    bulk_res = asyncio.run(
        tool_registry.execute(
            "workspace_bulk_organizer",
            {"action": "cleanup_duplicates", "user_id": uid},
            approval_granted=True,
        )
    )
    assert bulk_res["success"] is True
