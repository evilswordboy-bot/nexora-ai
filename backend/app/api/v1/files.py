"""
NEXORA AI — Stage 17 File Management & Workspace Automation REST API
"""

from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.models.schemas import (
    DuplicateFileGroup,
    FileBrowserImportRequest,
    FileConvertRequest,
    FileCreateFolderRequest,
    FileDeleteRequest,
    FileDuplicateCleanupRequest,
    FileOperationApproveRequest,
    FileOperationRecord,
    FileOrganizeRequest,
    FileSearchRequest,
    FileTransferRequest,
    FileWriteRequest,
    WorkspaceFileItem,
    WorkspaceFileReadResponse,
    WorkspaceFileVersion,
    WorkspaceTrashItem,
)
from app.services.files.engine import file_workspace_engine

router = APIRouter(prefix="/files", tags=["Stage 17: File Management & Workspace Automation"])


class FilePathActionRequest(BaseModel):
    user_id: str = "default_user"
    relative_path: str


@router.get("/capabilities")
async def get_file_workspace_capabilities(
    user_id: str = Query(default="default_user"),
) -> Dict[str, Any]:
    return file_workspace_engine.get_capabilities_summary(user_id=user_id)


@router.get("/list", response_model=List[WorkspaceFileItem])
async def list_workspace_files(
    user_id: str = Query(default="default_user"),
    directory: str = Query(default=""),
    recursive: bool = Query(default=True),
):
    try:
        return file_workspace_engine.list_items(
            user_id=user_id, directory=directory, recursive=recursive
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/search")
async def search_workspace_files(req: FileSearchRequest) -> Dict[str, Any]:
    try:
        return file_workspace_engine.search_items(req)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/read", response_model=WorkspaceFileReadResponse)
async def read_workspace_file(
    path: str = Query(..., description="Relative file path inside workspace"),
    user_id: str = Query(default="default_user"),
):
    try:
        return file_workspace_engine.read_file(user_id=user_id, relative_path=path)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/folders", response_model=FileOperationRecord)
async def create_workspace_folder(req: FileCreateFolderRequest):
    try:
        return file_workspace_engine.create_folder(req)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/write", response_model=FileOperationRecord)
async def write_workspace_file(req: FileWriteRequest):
    try:
        return file_workspace_engine.write_file(req)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except FileExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/transfer", response_model=FileOperationRecord)
async def transfer_workspace_item(req: FileTransferRequest):
    try:
        return file_workspace_engine.transfer_item(req)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FileExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/convert", response_model=FileOperationRecord)
async def convert_workspace_file(req: FileConvertRequest):
    try:
        return file_workspace_engine.convert_file(req)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FileExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/duplicates", response_model=List[DuplicateFileGroup])
async def find_duplicate_files(
    user_id: str = Query(default="default_user"),
    directory: str = Query(default=""),
):
    try:
        return file_workspace_engine.find_duplicates(user_id=user_id, directory=directory)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/duplicates/cleanup", response_model=FileOperationRecord)
async def cleanup_duplicate_files(req: FileDuplicateCleanupRequest):
    try:
        return file_workspace_engine.cleanup_duplicates(req)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/organize", response_model=FileOperationRecord)
async def organize_workspace_files(req: FileOrganizeRequest):
    try:
        return file_workspace_engine.organize_workspace(req)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/delete", response_model=FileOperationRecord)
async def delete_workspace_items_to_trash(req: FileDeleteRequest):
    try:
        return file_workspace_engine.delete_to_trash(req)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/trash", response_model=List[WorkspaceTrashItem])
async def list_trash_items(user_id: str = Query(default="default_user")):
    return file_workspace_engine.list_trash(user_id=user_id)


@router.post("/trash/{trash_id}/restore", response_model=FileOperationRecord)
async def restore_trash_item(
    trash_id: str,
    user_id: str = Query(default="default_user"),
):
    try:
        return file_workspace_engine.restore_from_trash(user_id=user_id, trash_id=trash_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/versions", response_model=List[WorkspaceFileVersion])
async def list_file_versions(
    path: str = Query(...),
    user_id: str = Query(default="default_user"),
):
    try:
        return file_workspace_engine.list_file_versions(user_id=user_id, relative_path=path)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/versions/{version_id}/restore", response_model=FileOperationRecord)
async def restore_file_version(
    version_id: str,
    req: FilePathActionRequest,
):
    try:
        return file_workspace_engine.restore_version(
            user_id=req.user_id, relative_path=req.relative_path, version_id=version_id
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/operations", response_model=List[FileOperationRecord])
async def list_file_operations(
    user_id: str = Query(default="default_user"),
    limit: int = Query(default=50, ge=1, le=200),
):
    return file_workspace_engine.list_operations(user_id=user_id, limit=limit)


@router.post("/operations/{operation_id}/approve", response_model=FileOperationRecord)
async def approve_or_reject_file_operation(
    operation_id: str,
    req: FileOperationApproveRequest,
):
    try:
        return file_workspace_engine.approve_or_reject_operation(operation_id=operation_id, req=req)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/operations/{operation_id}/rollback", response_model=FileOperationRecord)
async def rollback_file_operation(
    operation_id: str,
    user_id: str = Query(default="default_user"),
):
    try:
        return file_workspace_engine.rollback_operation(
            user_id=user_id, operation_id=operation_id
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/sync-stage4", response_model=FileOperationRecord)
async def sync_workspace_file_to_stage4(req: FilePathActionRequest):
    try:
        return file_workspace_engine.sync_to_stage4_vault(
            user_id=req.user_id, relative_path=req.relative_path
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/import-browser-session", response_model=FileOperationRecord)
async def import_stage16_browser_session(req: FileBrowserImportRequest):
    try:
        return file_workspace_engine.import_from_browser_session(req)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
