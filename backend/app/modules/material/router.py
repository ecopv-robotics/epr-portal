from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.storage import storage
from app.dependencies import get_current_user
from app.models import MaterialFile, MaterialRequirement, User
from app.modules.application.service import ensure_editable, get_owned_application
from app.modules.material.ocr import recognition_token, recognize_document, stored_file
from app.schemas import DocumentRecognitionOut, DocumentRecognitionRequest, MaterialFileOut, UploadOut

router = APIRouter(tags=["文件与材料"])
UPLOAD_RULES = {
    "document": ({".pdf", ".jpg", ".jpeg", ".png"}, 20),
    "identity": ({".pdf", ".jpg", ".jpeg", ".png", ".webp", ".doc", ".docx"}, 20),
    "signature": ({".jpg", ".jpeg", ".png", ".webp"}, 20),
    "store_screenshot": ({".jpg", ".jpeg", ".png", ".webp"}, 2),
}


def save_checked(file: UploadFile, purpose: str = "document") -> tuple[str, int]:
    if purpose not in UPLOAD_RULES:
        raise HTTPException(status_code=422, detail="未知文件用途")
    allowed_extensions, max_size_mb = UPLOAD_RULES[purpose]
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in allowed_extensions:
        formats = "、".join(sorted(value.removeprefix(".").upper() for value in allowed_extensions))
        raise HTTPException(status_code=422, detail=f"该文件仅支持 {formats} 格式")
    file_url, size = storage.save(file.file, file.filename or "upload")
    if size > max_size_mb * 1024 * 1024:
        storage.delete_url(file_url)  # type: ignore[attr-defined]
        raise HTTPException(status_code=413, detail=f"单个文件不能超过 {max_size_mb}MB")
    return file_url, size


@router.post("/files/upload", response_model=UploadOut)
def upload_file(
    file: UploadFile = File(...),
    purpose: str = Form("document"),
    _: User = Depends(get_current_user),
):
    file_url, size = save_checked(file, purpose)
    return UploadOut(
        file_url=file_url,
        original_name=file.filename or "upload",
        file_size=size,
        recognition_token=recognition_token(file_url),
    )


@router.post("/files/recognize", response_model=DocumentRecognitionOut)
def recognize_uploaded_file(
    payload: DocumentRecognitionRequest,
    _: User = Depends(get_current_user),
):
    source = stored_file(payload.file_url, payload.recognition_token)
    fields, warnings = recognize_document(source, payload.document_type)
    if not fields:
        warnings = ["未识别到可回填字段，请确认图片清晰、完整且证件类型正确。", *warnings]
    return DocumentRecognitionOut(document_type=payload.document_type, fields=fields, warnings=warnings)


@router.post("/material/upload", response_model=MaterialFileOut)
def upload_material(
    application_id: int = Form(...),
    requirement_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    application = get_owned_application(db, user, application_id)
    ensure_editable(application)
    requirement = db.scalar(select(MaterialRequirement).where(
        MaterialRequirement.id == requirement_id,
        MaterialRequirement.template_id == application.template_id,
    ))
    if not requirement:
        raise HTTPException(status_code=422, detail="材料要求与当前递单模板不匹配")
    file_url, size = save_checked(file)
    record = db.scalar(select(MaterialFile).where(
        MaterialFile.application_id == application.id,
        MaterialFile.requirement_id == requirement.id,
    ))
    if record:
        storage.delete_url(record.file_url)  # type: ignore[attr-defined]
    else:
        record = MaterialFile(application_id=application.id, requirement_id=requirement.id, file_url="", original_name="")
        db.add(record)
    record.file_url = file_url
    record.original_name = file.filename or "upload"
    record.file_size = size
    db.commit()
    db.refresh(record)
    return record
