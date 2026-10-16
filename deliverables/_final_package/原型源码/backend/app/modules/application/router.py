from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models import Application, ApplicationStatus, ApplicationStatusHistory, ServiceTemplate, User
from app.modules.company.router import company_out
from app.modules.application.service import get_owned_application, reusable_file_for_requirement, transition_application, validate_for_submission
from app.modules.application.authorization import AuthorizationValidationError, generate_germany_weee_authorization
from app.modules.application.notifications import notify_staff_new_order, staff_review_recipients
from app.schemas import (
    ApplicationCreate, ApplicationFormOut, ApplicationList, ApplicationOut, FormFieldOut,
    MaterialFileOut, MaterialRequirementOut, ProductData, StatusHistoryOut, StoreData, TemplateOut,
)

router = APIRouter(prefix="/applications", tags=["递单"])


def to_out(application: Application) -> ApplicationOut:
    return ApplicationOut(
        id=application.id,
        application_no=application.application_no,
        purchase_order_id=application.purchase_order_id,
        instance_index=application.instance_index,
        company_name=application.company.company_name if application.company else None,
        registration_number=application.registration_number,
        certificate_file=application.certificate_file,
        invoice_file=application.invoice_file,
        result_file=application.result_file,
        service_expiry_date=application.service_expiry_date,
        agent_name=(application.user.customer_profile.name
                    if application.user.customer_profile and application.user.customer_profile.customer_type.value == "AGENT"
                    else None),
        country=application.country,
        service_type=application.service_type,
        status=application.status,
        created_time=application.created_time,
        submitted_time=application.submitted_time,
        reviewed_time=application.reviewed_time,
        review_note=application.review_note,
    )


@router.get("", response_model=ApplicationList)
def list_applications(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    base = select(Application).where(Application.user_id == user.id)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    items = db.scalars(base.order_by(Application.created_time.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return ApplicationList(items=[to_out(item) for item in items], total=total, page=page, page_size=page_size)


@router.post("", response_model=ApplicationOut, status_code=201)
def create_application(
    payload: ApplicationCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Service instances are commercial entitlements. Customers can only obtain
    # them from a paid order; direct draft creation would bypass payment.
    _ = (payload, db, user)
    raise HTTPException(status_code=409, detail="请先购买并完成付款，再从订单中的服务实例填写资料")


@router.get("/{application_id}", response_model=ApplicationOut)
def get_application(
    application_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    application = db.scalar(select(Application).where(Application.id == application_id, Application.user_id == user.id))
    if not application:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="递单不存在")
    return to_out(application)


@router.get("/{application_id}/form", response_model=ApplicationFormOut)
def get_application_form(
    application_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    application = db.scalar(select(Application).where(Application.id == application_id, Application.user_id == user.id))
    if not application:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="递单不存在")
    template = application.template or db.scalar(select(ServiceTemplate).where(
        ServiceTemplate.country == application.country,
        ServiceTemplate.service_type == application.service_type,
        ServiceTemplate.status == "ACTIVE",
    ).order_by(ServiceTemplate.version.desc()))
    if not template:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail="递单模板不存在")
    explicit_files = {item.requirement_id: MaterialFileOut.model_validate(item) for item in application.material_files}
    synced_files: list[MaterialFileOut] = []
    for requirement in template.material_requirements:
        if requirement.id in explicit_files:
            continue
        reusable = reusable_file_for_requirement(application, requirement)
        if reusable:
            file_url, original_name = reusable
            synced_files.append(MaterialFileOut(
                id=-requirement.id, requirement_id=requirement.id, file_url=file_url,
                original_name=original_name, file_size=0, upload_time=application.created_time, auto_synced=True,
            ))
    return ApplicationFormOut(
        application=to_out(application),
        template=TemplateOut(
            id=template.id, country=template.country, service_type=template.service_type, version=template.version,
            fields=[FormFieldOut.model_validate(field) for field in sorted(template.form_fields, key=lambda item: item.sort)],
            materials=[MaterialRequirementOut.model_validate(item) for item in sorted(template.material_requirements, key=lambda item: item.sort)],
        ),
        company=company_out(application.company) if application.company else None,
        store=StoreData.model_validate(application.store, from_attributes=True) if application.store else None,
        products=[ProductData(id=item.id, product_data=item.product_data) for item in application.products],
        material_files=[*explicit_files.values(), *synced_files],
    )


@router.post("/{application_id}/submit", response_model=ApplicationOut)
def submit_application(
    application_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    application = get_owned_application(db, user, application_id)
    if application.status not in (ApplicationStatus.DRAFT, ApplicationStatus.NEED_FIX):
        from fastapi import HTTPException
        raise HTTPException(status_code=409, detail="当前状态不能提交")
    missing_fields = validate_for_submission(application)
    if missing_fields:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail={"message": "资料不完整", "missing_fields": missing_fields})
    is_resubmission = application.status == ApplicationStatus.NEED_FIX
    target = ApplicationStatus.REVIEWING if is_resubmission else ApplicationStatus.SUBMITTED
    transition_application(db, application, target, user, "客户提交申请" if target == ApplicationStatus.SUBMITTED else "客户补件后重新提交")
    db.commit()
    db.refresh(application)
    recipients = staff_review_recipients(db, application)
    background_tasks.add_task(notify_staff_new_order, recipients, application.application_no, is_resubmission)
    return to_out(application)


@router.get("/{application_id}/status-history", response_model=list[StatusHistoryOut])
def status_history(
    application_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    application = get_owned_application(db, user, application_id)
    items = db.scalars(select(ApplicationStatusHistory).where(
        ApplicationStatusHistory.application_id == application.id
    ).order_by(ApplicationStatusHistory.created_time.desc())).all()
    return [StatusHistoryOut(
        id=item.id, from_status=item.from_status, to_status=item.to_status, note=item.note,
        operator_name=item.operator.username, created_time=item.created_time,
    ) for item in items]


@router.get("/{application_id}/authorization/germany-weee")
def download_germany_weee_authorization(
    application_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    application = get_owned_application(db, user, application_id)
    try:
        content = generate_germany_weee_authorization(application)
    except AuthorizationValidationError as error:
        raise HTTPException(
            status_code=422,
            detail={"message": "授权书资料不完整", "missing_fields": error.missing_fields},
        ) from error
    filename = f"{application.application_no}-Germany-WEEE-Authorization.docx"
    return StreamingResponse(
        content,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
