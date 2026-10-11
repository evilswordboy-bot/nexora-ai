"""
NEXORA AI — Stage 20: AI Evaluation & Quality Assurance API Router
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import (
    EvalCaseCreateRequest,
    EvalCaseReviewRequest,
    EvalCompareRunsRequest,
    EvalRunCreateRequest,
    EvalSuiteId,
    EvalSyntheticGenerateRequest,
)
from app.services.evaluation.engine import evaluation_qa_engine

router = APIRouter(prefix="/evaluation", tags=["Evaluation & Quality Assurance (Stage 20)"])


@router.get("/metadata")
async def get_evaluation_metadata():
    """
    Returns Stage 20 evaluation suites, dataset version, metric scoring rules
    (with explicit limitations), and default release acceptance thresholds.
    """
    return evaluation_qa_engine.get_metadata()


@router.get("/cases")
async def list_evaluation_cases(
    suite_id: Optional[EvalSuiteId] = Query(default=None),
    include_rejected: bool = Query(default=False),
):
    """Lists evaluation benchmark and synthetic test cases."""
    cases = evaluation_qa_engine.list_cases(suite_id=suite_id, include_rejected=include_rejected)
    return {
        "dataset_version": evaluation_qa_engine.get_dataset_version(),
        "total": len(cases),
        "cases": [c.model_dump(mode="json") for c in cases],
    }


@router.post("/cases")
async def create_evaluation_case(req: EvalCaseCreateRequest):
    """
    Adds a new benchmark or synthetic test case and bumps the dataset semantic version.
    Rejects private conversation data by default and blocks raw credentials.
    """
    try:
        tc = evaluation_qa_engine.add_case(req)
        return tc.model_dump(mode="json")
    except PermissionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/cases/synthetic")
async def generate_synthetic_cases(req: EvalSyntheticGenerateRequest):
    """
    Generates clearly labeled synthetic evaluation test cases (`source_type='synthetic_labeled'`,
    `review_status='pending_review'`) requiring human review before release-gate inclusion.
    """
    created = evaluation_qa_engine.generate_synthetic_cases(req)
    return {
        "dataset_version": evaluation_qa_engine.get_dataset_version(),
        "generated_count": len(created),
        "cases": [c.model_dump(mode="json") for c in created],
    }


@router.post("/cases/{case_id}/review")
async def review_evaluation_case(case_id: str, req: EvalCaseReviewRequest):
    """Approves or rejects a test case (e.g. reviewing a synthetic test case)."""
    try:
        tc = evaluation_qa_engine.review_case(case_id=case_id, req=req)
        return tc.model_dump(mode="json")
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/cases/{case_id}")
async def delete_evaluation_case(case_id: str, admin_actor: str = Query(default="admin")):
    """Removes a test case from the dataset and bumps the dataset version."""
    try:
        return evaluation_qa_engine.delete_case(case_id=case_id, admin_actor=admin_actor)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/datasets/export")
async def export_evaluation_dataset():
    """Exports the versioned evaluation dataset and its modification changelog."""
    return evaluation_qa_engine.export_dataset()


@router.post("/runs")
async def execute_evaluation_run(req: EvalRunCreateRequest):
    """
    Executes an isolated evaluation run across selected test suites (Stages 1–19),
    computes recorded metrics, checks baseline regressions, and determines the release-gate verdict.
    """
    run_rec = await evaluation_qa_engine.execute_run(req)
    return run_rec.model_dump(mode="json")


@router.get("/runs")
async def list_evaluation_runs(limit: int = Query(default=25, ge=1, le=100)):
    """Lists recent evaluation runs."""
    runs = evaluation_qa_engine.list_runs(limit=limit)
    return {
        "total": len(runs),
        "runs": [r.model_dump(mode="json") for r in runs],
    }


@router.get("/runs/{run_id}")
async def get_evaluation_run(run_id: str):
    """Retrieves full details of a recorded evaluation run."""
    try:
        run_rec = evaluation_qa_engine.get_run(run_id)
        return run_rec.model_dump(mode="json")
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/compare")
async def compare_evaluation_runs(req: EvalCompareRunsRequest):
    """Compares a baseline evaluation run against a candidate run for quality/latency regressions."""
    try:
        return evaluation_qa_engine.compare_runs(
            baseline_run_id=req.baseline_run_id,
            candidate_run_id=req.candidate_run_id,
            thresholds=req.thresholds,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/runs/{run_id}/export")
async def export_evaluation_run_report(
    run_id: str,
    format: str = Query(default="markdown", pattern="^(markdown|json)$"),
):
    """Exports an evaluation run report in Markdown or JSON format."""
    try:
        return evaluation_qa_engine.export_run_report(run_id=run_id, fmt=format)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
