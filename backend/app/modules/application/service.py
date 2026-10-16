from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Application, ApplicationAssignment, ApplicationStatus, ApplicationStatusHistory, CountryResponsibility, Employee, MaterialRequirement, Role, User


def assign_country_delivery_owner(db: Session, application: Application, assigned_by_id: int | None = None) -> Employee | None:
    responsibility = db.scalar(select(CountryResponsibility).where(CountryResponsibility.country == application.country))
    employee_id = responsibility.delivery_employee_id if responsibility else None
    assignee = db.get(Employee, employee_id) if employee_id else None
    if not assignee or not assignee.active or assignee.role.code != "DELIVERY":
        assignee = db.scalar(select(Employee).join(Role).where(
            Role.code == "DELIVERY", Employee.active.is_(True)
        ).order_by(Employee.display_name))
    if not assignee:
        return None
    actor_id = assigned_by_id
    if actor_id is None:
        actor_id = db.scalar(select(Employee.id).join(Role).where(Role.code == "ADMIN", Employee.active.is_(True))) or assignee.id
    assignment = application.assignment
    if assignment:
        assignment.employee_id, assignment.assigned_by_id = assignee.id, actor_id
    else:
        application.assignment = ApplicationAssignment(employee_id=assignee.id, assigned_by_id=actor_id)
    return assignee


def reusable_file_for_requirement(application: Application, requirement: MaterialRequirement) -> tuple[str, str] | None:
    """Resolve files collected in earlier form steps for a matching material requirement."""
    name = requirement.material_name.replace(" ", "").upper()
    company = application.company
    if not company:
        return None
    legal = company.legal_person
    store = application.store
    candidates: list[tuple[bool, str | None, str]] = [
        ("企业信用报告" in name, company.credit_report_file, "企业信用报告"),
        ("NNC1" in name or "NAR1" in name, company.nnc1_file, "NNC1-NAR1"),
        ("董事索引" in name, company.director_index_file, "董事索引"),
        ("商业登记证" in name or name == "BR", company.br_file, "商业登记证-BR"),
        ("公司注册证明" in name or name == "CR", company.cr_file or company.license_file, "公司注册证明-CR"),
        ("营业执照" in name or "注册证明" in name, company.license_file or company.cr_file, "营业执照-注册证明"),
        ("法人身份证" in name or "法人证件" in name or "身份证/护照" in name, legal.front_file if legal else None, "法人身份证-护照"),
        ("法人签名" in name or name == "签名", legal.signature_file if legal else None, "法人签名"),
        ("店铺后台截图" in name or "店铺截图" in name, store.screenshot_file if store else None, "店铺后台截图"),
    ]
    for matched, file_url, label in candidates:
        if matched and file_url:
            suffix = file_url.rsplit(".", 1)[-1] if "." in file_url else "pdf"
            return file_url, f"{label}.{suffix}"
    return None


def get_owned_application(db: Session, user: User, application_id: int) -> Application:
    application = db.scalar(select(Application).where(Application.id == application_id, Application.user_id == user.id))
    if not application:
        raise HTTPException(status_code=404, detail="递单不存在")
    return application


def ensure_editable(application: Application) -> None:
    if application.status not in (ApplicationStatus.DRAFT, ApplicationStatus.NEED_FIX):
        raise HTTPException(status_code=409, detail="当前状态不允许修改资料")


def transition_application(
    db: Session,
    application: Application,
    to_status: ApplicationStatus,
    operator: User,
    note: str | None = None,
) -> None:
    from_status = application.status
    application.status = to_status
    if to_status == ApplicationStatus.SUBMITTED or (to_status == ApplicationStatus.REVIEWING and application.submitted_time is None):
        application.submitted_time = datetime.now(timezone.utc)
    if to_status == ApplicationStatus.COMPLETED:
        application.reviewed_time = datetime.now(timezone.utc)
    if note is not None:
        application.review_note = note
    db.add(ApplicationStatusHistory(
        application_id=application.id,
        from_status=from_status.value,
        to_status=to_status.value,
        note=note,
        operator_id=operator.id,
    ))


def validate_for_submission(application: Application) -> list[str]:
    missing: list[str] = []
    company = application.company
    if not company:
        return ["公司信息", "法人信息", "店铺信息", "产品信息", "必填材料"]

    common_company_fields = {
        "registration_region": "公司注册地", "company_type": "公司类型", "company_name": "公司名称",
        "register_number": "营业执照号/注册号", "established_date": "公司成立日期", "register_address": "注册地址",
    }
    for field, label in common_company_fields.items():
        if not getattr(company, field, None):
            missing.append(label)
    if company.registration_region == "MAINLAND_CHINA":
        if not company.license_file: missing.append("公司营业执照")
        if not company.credit_report_file: missing.append("企业信用报告")
    elif company.registration_region == "HONG_KONG":
        if not company.cr_file: missing.append("公司注册证明书 CR")
        if not company.br_file: missing.append("商业登记证 BR")
        if not company.nnc1_file: missing.append("NNC1/NAR1")
    elif company.registration_region in ("EU", "OTHER"):
        if not company.vat_number: missing.append("本国 VAT 税号")
        if not company.license_file: missing.append("公司注册证明")

    legal = company.legal_person
    if not legal:
        missing.append("法人信息")
    else:
        legal_fields = {
            "certificate_type": "法人证件类型", "gender": "法人性别", "name_cn": "法人中文名",
            "name_en": "法人拼音名", "contact_email": "联系人邮箱", "contact_phone": "联系人电话",
            "front_file": "法人证件资料", "signature_file": "法人签名",
        }
        for field, label in legal_fields.items():
            if not getattr(legal, field, None): missing.append(label)
        if legal.certificate_type == "ID_CARD" and not legal.back_file:
            missing.append("身份证国徽面")

    store = application.store
    store_fields = {
        "platform": "销售平台", "store_url": "店铺链接", "company_name_en": "英文公司名称",
        "register_city_en": "英文注册城市", "postal_code": "注册地邮编",
        "register_address_en": "英文注册地址", "screenshot_file": "店铺后台截图",
    }
    if not store:
        missing.append("店铺信息")
    else:
        for field, label in store_fields.items():
            if not getattr(store, field, None): missing.append(label)

    if not application.products:
        missing.append("至少一个产品")
    else:
        fields = sorted(application.template.form_fields, key=lambda item: item.sort) if application.template else []
        for index, product in enumerate(application.products, 1):
            for field in fields:
                value = product.product_data.get(field.field_name)
                if field.required and (value is None or value == ""):
                    missing.append(f"产品 {index}：{field.label}")

    uploaded = {item.requirement_id for item in application.material_files}
    requirements = application.template.material_requirements if application.template else []
    for requirement in requirements:
        if requirement.required and requirement.id not in uploaded and not reusable_file_for_requirement(application, requirement):
            missing.append(f"材料：{requirement.material_name}")
    return missing
