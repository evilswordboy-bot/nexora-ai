import uuid
import logging
from typing import List
from fastapi import APIRouter, HTTPException, status

from app.models.schemas import (
    VisionAnalyzeRequest,
    VisionAnalyzeResponse,
    OCRRequest,
    OCRResponse,
    ImageCompareRequest,
    ImageCompareResponse,
    ChatRequest,
    Message,
)
from app.services.vision.engine import vision_engine
from app.services.ai_service import ai_service

logger = logging.getLogger("nexora.api.vision")

router = APIRouter(prefix="/vision", tags=["Vision Intelligence"])


@router.post("/analyze", response_model=VisionAnalyzeResponse)
async def analyze_images(req: VisionAnalyzeRequest):
    """
    Multimodal visual understanding endpoint for single or multiple images.
    Performs format verification, metadata extraction, optional OCR pre-extraction,
    and structured visual reasoning via configured LLM.
    """
    if not req.images:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one image is required for visual analysis."
        )

    if len(req.images) > 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum permitted images per request is 5."
        )

    meta_list = []
    ocr_list = []

    for idx, img_b64 in enumerate(req.images):
        try:
            raw_bytes, mime = vision_engine.parse_base64_image(img_b64)
            meta = vision_engine.extract_image_metadata(raw_bytes, f"image_{idx+1}.png")
            
            # OCR inspection
            ocr_text, has_text, _ = vision_engine.perform_ocr(raw_bytes)
            meta.has_text = has_text
            if ocr_text:
                meta.ocr_preview = ocr_text[:120] + ("..." if len(ocr_text) > 120 else "")
                ocr_list.append(ocr_text)
            else:
                ocr_list.append("")
                
            meta_list.append(meta)
        except ValueError as ve:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(ve)
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error inspecting image {idx+1}: {str(e)}"
            )

    # Build prompt
    prompt_str = req.prompt or "Provide a comprehensive, high-detail analysis of visual elements."
    multimodal_prompt = vision_engine.prepare_multimodal_vision_prompt(
        user_prompt=prompt_str,
        image_metadata_list=meta_list,
        ocr_texts=ocr_list,
        analysis_type=req.analysis_type or "general",
    )

    # Dispatch to configured AI provider
    chat_req = ChatRequest(
        messages=[
            Message(
                id=f"vis-prompt-{uuid.uuid4().hex[:8]}",
                role="user",
                content=prompt_str,
                images=req.images,
            )
        ],
        system_prompt=multimodal_prompt,
        provider=req.provider or "auto",
        model=req.model or "gemini-1.5-flash",
        client_api_key=req.client_api_key,
        images=req.images,
    )

    ai_resp = await ai_service.generate_response(chat_req)

    combined_ocr = "\n\n---\n\n".join([t for t in ocr_list if t.strip()]) if any(ocr_list) else None

    return VisionAnalyzeResponse(
        id=f"vis-{uuid.uuid4().hex[:8]}",
        prompt=prompt_str,
        analysis=ai_resp.content,
        extracted_text=combined_ocr,
        image_metadata=meta_list,
        model=ai_resp.model,
        provider=ai_resp.provider,
    )


@router.post("/ocr", response_model=OCRResponse)
async def extract_ocr_text(req: OCRRequest):
    """
    Dedicated OCR endpoint that parses text from an image with prompt-injection quarantining.
    """
    try:
        return vision_engine.process_ocr_request(req)
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OCR processing failed: {str(e)}"
        )


@router.post("/compare", response_model=ImageCompareResponse)
async def compare_images(req: ImageCompareRequest):
    """
    Side-by-side visual comparison of two images (e.g. UI diff, layout updates, document revisions).
    """
    try:
        raw_b1, _ = vision_engine.parse_base64_image(req.image1)
        raw_b2, _ = vision_engine.parse_base64_image(req.image2)

        meta1 = vision_engine.extract_image_metadata(raw_b1, f"{req.image1_label or 'Image_1'}.png")
        meta2 = vision_engine.extract_image_metadata(raw_b2, f"{req.image2_label or 'Image_2'}.png")

        ocr1, _, _ = vision_engine.perform_ocr(raw_b1)
        ocr2, _, _ = vision_engine.perform_ocr(raw_b2)
        meta1.has_text = bool(ocr1)
        meta2.has_text = bool(ocr2)
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Image inspection error: {str(e)}"
        )

    comp_prompt = (
        f"Compare {req.image1_label} and {req.image2_label}.\n"
        f"Focus: {req.comparison_focus or 'general'}.\n"
        f"Analyze visual layout changes, element additions/removals, color scheme variances, and text alterations."
    )

    multimodal_prompt = vision_engine.prepare_multimodal_vision_prompt(
        user_prompt=comp_prompt,
        image_metadata_list=[meta1, meta2],
        ocr_texts=[ocr1, ocr2],
        analysis_type="comparison",
    )

    chat_req = ChatRequest(
        messages=[
            Message(
                id=f"vis-comp-{uuid.uuid4().hex[:8]}",
                role="user",
                content=comp_prompt,
                images=[req.image1, req.image2],
            )
        ],
        system_prompt=multimodal_prompt,
        provider=req.provider or "auto",
        model=req.model or "gemini-1.5-flash",
        client_api_key=req.client_api_key,
        images=[req.image1, req.image2],
    )

    ai_resp = await ai_service.generate_response(chat_req)

    # Derive quick structured differences and similarities
    similarities = [
        f"Format consistency: {meta1.format.upper()} vs {meta2.format.upper()}",
        f"Resolution baseline: {meta1.width}x{meta1.height} vs {meta2.width}x{meta2.height}",
    ]
    differences = []
    if meta1.width != meta2.width or meta1.height != meta2.height:
        differences.append(f"Dimension variance: {meta1.width}x{meta1.height} vs {meta2.width}x{meta2.height}")
    if meta1.size_bytes != meta2.size_bytes:
        differences.append(f"Payload size delta: {abs(meta1.size_bytes - meta2.size_bytes) // 1024} KB")
    if meta1.has_text != meta2.has_text:
        differences.append(f"Textual presence disparity: '{req.image1_label}' has text={meta1.has_text}, '{req.image2_label}' has text={meta2.has_text}")

    if not differences:
        differences.append("Both images have matched technical container specifications; visual nuances detailed in synthesis.")

    return ImageCompareResponse(
        id=f"comp-{uuid.uuid4().hex[:8]}",
        comparison_summary=ai_resp.content,
        similarities=similarities,
        differences=differences,
        metadata_image1=meta1,
        metadata_image2=meta2,
        model=ai_resp.model,
        provider=ai_resp.provider,
    )
