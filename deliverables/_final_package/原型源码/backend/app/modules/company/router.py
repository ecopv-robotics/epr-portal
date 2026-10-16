from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models import Application, Company, LegalPerson, User
from app.modules.application.service import ensure_editable, get_owned_application
from app.schemas import ApplicationOut, CompanyData, CompanyOut, CompanyProfileOut, LegalPersonData, UploadOut
from app.modules.company.license_translation import generate_translation

router = APIRouter(tags=["企业资料"])


def company_out(company: Company) -> CompanyOut:
    legal = None
    if company.legal_person:
        legal = LegalPersonData.model_validate(company.legal_person, from_attributes=True)
    return CompanyOut(
        id=company.id, company_name=company.company_name, company_name_en=company.company_name_en,
        registration_region=company.registration_region, company_type=company.company_type,
        register_number=company.register_number, established_date=company.established_date,
        vat_number=company.vat_number, register_address=company.register_address,
        license_file=company.license_file, license_translation_file=company.license_translation_file,
        credit_report_file=company.credit_report_file,
        br_file=company.br_file, cr_file=company.cr_file, nnc1_file=company.nnc1_file,
        director_index_file=company.director_index_file, created_time=company.created_time,
        legal_person=legal,
    )


def can_access_company(db: Session, user: User, company_id: int) -> bool:
    return db.scalar(select(Company.id).where(Company.id == company_id, Company.user_id == user.id)) is not None


def completeness(company: Company) -> int:
    values = [company.registration_region, company.company_type, company.company_name, company.register_number,
              company.established_date, company.register_address, company.license_file, company.legal_person]
    return round(sum(bool(value) for value in values) / len(values) * 100)


@router.get("/companies", response_model=list[CompanyProfileOut])
def list_companies(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.execute(
        select(Company, func.count(Application.id), func.max(Application.created_time))
        .outerjoin(Application, Application.company_id == Company.id)
        .where(Company.user_id == user.id)
        .group_by(Company.id)
        .order_by(Company.created_time.desc())
    ).all()
    return [CompanyProfileOut(**company_out(company).model_dump(), application_count=count,
                              completeness=completeness(company), last_application_time=last_time)
            for company, count, last_time in rows]


@router.post("/companies", response_model=CompanyOut, status_code=201)
def create_company(payload: CompanyData, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    company = Company(user_id=user.id, company_name=payload.company_name)
    db.add(company)
    db.flush()
    update_company_record(company, payload, db)
    db.commit()
    db.refresh(company)
    return company_out(company)


@router.get("/companies/{company_id}", response_model=CompanyOut)
def get_company(company_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    company = db.scalar(select(Company).where(Company.id == company_id, Company.user_id == user.id))
    if not company:
        raise HTTPException(status_code=404, detail="企业资料不存在")
    return company_out(company)


@router.get("/companies/{company_id}/applications", response_model=list[ApplicationOut])
def company_applications(company_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not can_access_company(db, user, company_id):
        raise HTTPException(status_code=404, detail="企业资料不存在")
    applications = db.scalars(select(Application).where(
        Application.company_id == company_id, Application.user_id == user.id
    ).order_by(Application.created_time.desc())).all()
    return [ApplicationOut(
        id=item.id, application_no=item.application_no, company_name=item.company.company_name if item.company else None,
        registration_number=item.registration_number, certificate_file=item.certificate_file,
        invoice_file=item.invoice_file, result_file=item.result_file, service_expiry_date=item.service_expiry_date,
        country=item.country, service_type=item.service_type, status=item.status, created_time=item.created_time,
        submitted_time=item.submitted_time, reviewed_time=item.reviewed_time, review_note=item.review_note,
    ) for item in applications]


@router.put("/companies/{company_id}", response_model=CompanyOut)
def update_company(company_id: int, payload: CompanyData, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    company = db.scalar(select(Company).where(Company.id == company_id, Company.user_id == user.id))
    if not company:
        raise HTTPException(status_code=404, detail="企业资料不存在")
    update_company_record(company, payload, db)
    db.commit()
    db.refresh(company)
    return company_out(company)


def update_company_record(company: Company, payload: CompanyData, db: Session) -> None:
    for field in (
        "company_name", "company_name_en", "registration_region", "company_type", "register_number",
        "established_date", "vat_number", "register_address", "license_file", "license_translation_file", "credit_report_file",
        "br_file", "cr_file", "nnc1_file", "director_index_file",
    ):
        setattr(company, field, getattr(payload, field))
    if payload.legal_person:
        legal = company.legal_person or LegalPerson(company_id=company.id)
        db.add(legal)
        for field, value in payload.legal_person.model_dump().items():
            setattr(legal, field, value)


@router.get("/company/history", response_model=list[CompanyOut])
def company_history(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    company_ids = select(Application.company_id).where(
        Application.user_id == user.id, Application.company_id.is_not(None)
    ).distinct()
    companies = db.scalars(select(Company).where(Company.id.in_(company_ids), Company.user_id == user.id).order_by(Company.created_time.desc())).all()
    return [company_out(company) for company in companies]


@router.put("/applications/{application_id}/company", response_model=CompanyOut)
def save_company(
    application_id: int,
    payload: CompanyData,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    application = get_owned_application(db, user, application_id)
    ensure_editable(application)
    if payload.id:
        if not can_access_company(db, user, payload.id):
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="历史企业资料不存在")
        company = db.get(Company, payload.id)
    elif application.company:
        company = application.company
    else:
        company = Company(user_id=user.id, company_name=payload.company_name)
        db.add(company)
        db.flush()
    update_company_record(company, payload, db)
    application.company_id = company.id
    db.commit()
    db.refresh(company)
    return company_out(company)


@router.put("/applications/{application_id}/legal-person", response_model=CompanyOut)
def save_legal_person(
    application_id: int,
    payload: LegalPersonData,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    application = get_owned_application(db, user, application_id)
    ensure_editable(application)
    if not application.company:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail="请先保存公司信息")
    legal = application.company.legal_person or LegalPerson(company_id=application.company.id)
    db.add(legal)
    for field, value in payload.model_dump().items():
        setattr(legal, field, value)
    db.commit()
    db.refresh(application.company)
    return company_out(application.company)


@router.post("/applications/{application_id}/company/license-translation", response_model=UploadOut)
def create_license_translation(
    application_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    application = get_owned_application(db, user, application_id)
    ensure_editable(application)
    company = application.company
    if not company or company.registration_region != "MAINLAND_CHINA":
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail="仅支持中国大陆公司营业执照翻译")
    if not company.license_file:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail="请先上传并保存营业执照")
    file_url, size = generate_translation(company.license_file)
    company.license_translation_file = file_url
    db.commit()
    return UploadOut(file_url=file_url, original_name="business-license-translation.pdf", file_size=size)
