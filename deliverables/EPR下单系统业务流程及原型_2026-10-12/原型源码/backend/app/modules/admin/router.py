from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import hash_password
from app.dependencies import get_current_admin
from app.models import (
    Application, ApplicationAssignment, ApplicationStatus, ApplicationStatusHistory, AuditRecord,
    Company, CustomerProfile, CustomerType, Employee, FormField, MaterialRequirement, PurchaseOrder,
    PurchaseOrderStatus, Role, ServiceTemplate, User, UserRole,
)
from app.modules.application.router import to_out
from app.modules.portal.router import activate_paid_order, purchase_order_out
from app.modules.application.service import reusable_file_for_requirement, transition_application
from app.modules.application.notifications import notify_customer_update
from app.modules.company.router import company_out
from app.portal_catalog import PORTAL_SERVICE_BY_ID
from app.schemas import (
    AdminContractUpdate, AdminOrderCreate, AdminPackageDiscount, AdminPaymentReview, AdminPurchaseOrderOut, AdminStatusUpdate, ApplicationFormOut, ApplicationList,
    ApplicationOut, AssignmentOut, AssignmentUpdate,
    AuditRecordOut, DashboardOut, EmployeeOut, FormFieldOut, MaterialFileOut, MaterialRequirementOut,
    CompanyProfileOut, CustomerAccountCreate, CustomerAccountDetailOut, CustomerAccountOut, CustomerAccountUpdate, ProductData, StatusHistoryOut, StoreData,
    TemplateConfigUpdate, TemplateOut,
)

router = APIRouter(prefix="/admin", tags=["后台审核"])


def admin_purchase_order_out(order: PurchaseOrder) -> AdminPurchaseOrderOut:
    base = purchase_order_out(order).model_dump()
    profile = order.user.customer_profile
    return AdminPurchaseOrderOut(
        **base,
        customer_name=profile.name if profile else order.user.username,
        customer_account=order.user.email or order.user.phone or order.user.username,
    )


def get_employee(db: Session, user: User) -> Employee:
    employee = db.scalar(select(Employee).where(Employee.user_id == user.id, Employee.active.is_(True)))
    if not employee:
        raise HTTPException(status_code=403, detail="员工账号未启用")
    return employee


def require_permission(employee: Employee, permission: str) -> None:
    if permission not in (employee.role.permissions or []):
        raise HTTPException(status_code=403, detail="当前员工没有此操作权限")


def require_any_permission(employee: Employee, *permissions: str) -> None:
    if not any(permission in (employee.role.permissions or []) for permission in permissions):
        raise HTTPException(status_code=403, detail="当前员工没有此操作权限")


def get_application_or_404(db: Session, application_id: int) -> Application:
    application = db.scalar(select(Application).where(
        Application.id == application_id,
        Application.status != ApplicationStatus.DRAFT,
    ))
    if not application:
        raise HTTPException(status_code=404, detail="递单不存在")
    return application


@router.get("/orders", response_model=list[AdminPurchaseOrderOut])
def list_purchase_orders(
    status: PurchaseOrderStatus | None = None,
    keyword: str | None = Query(None, max_length=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_admin),
):
    require_any_permission(
        get_employee(db, user), "order.create", "discount.approve", "contract.manage", "payment.review"
    )
    query = select(PurchaseOrder).join(User, PurchaseOrder.user_id == User.id).outerjoin(CustomerProfile)
    if status:
        query = query.where(PurchaseOrder.status == status)
    if keyword:
        pattern = f"%{keyword.strip()}%"
        query = query.where(or_(
            PurchaseOrder.order_no.ilike(pattern),
            User.username.ilike(pattern),
            User.email.ilike(pattern),
            CustomerProfile.name.ilike(pattern),
        ))
    orders = db.scalars(query.order_by(PurchaseOrder.created_time.desc())).unique().all()
    return [admin_purchase_order_out(order) for order in orders]


@router.get("/orders/{order_id}", response_model=AdminPurchaseOrderOut)
def get_purchase_order(order_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_admin)):
    require_any_permission(
        get_employee(db, user), "order.create", "discount.approve", "contract.manage", "payment.review"
    )
    order = db.get(PurchaseOrder, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    return admin_purchase_order_out(order)


@router.post("/orders", response_model=AdminPurchaseOrderOut, status_code=201)
def create_order_for_customer(
    payload: AdminOrderCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_admin),
):
    employee = get_employee(db, user)
    require_permission(employee, "order.create")
    customer = db.get(User, payload.user_id)
    if not customer or customer.role != UserRole.CUSTOMER:
        raise HTTPException(status_code=404, detail="客户账号不存在")
    service = PORTAL_SERVICE_BY_ID.get(payload.service_id)
    if not service:
        raise HTTPException(status_code=404, detail="服务不存在或已下架")
    if payload.service_year not in service["service_years"]:
        raise HTTPException(status_code=422, detail="商品服务年度无效")
    standard_amount = service["price"] * payload.quantity
    order = PurchaseOrder(
        order_no="PENDING", user_id=customer.id, service_id=payload.service_id,
        service_year=payload.service_year, subject_type="", package_type="",
        quantity=payload.quantity, unit_price=service["price"], standard_amount=standard_amount,
        discount_amount=0, total_amount=standard_amount,
    )
    db.add(order)
    db.flush()
    order.order_no = f"ORD{datetime.now(timezone.utc).year}{order.id:08d}"
    db.add(AuditRecord(employee_id=employee.id, action="ORDER_CREATED_FOR_CUSTOMER", detail={"order_id": order.id, "customer_id": customer.id}))
    db.commit()
    db.refresh(order)
    return admin_purchase_order_out(order)


@router.post("/orders/package-discount", response_model=list[AdminPurchaseOrderOut])
def approve_package_discount(
    payload: AdminPackageDiscount,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_admin),
):
    employee = get_employee(db, user)
    require_permission(employee, "discount.approve")
    orders = db.scalars(select(PurchaseOrder).where(PurchaseOrder.id.in_(payload.order_ids)).with_for_update()).all()
    if len(orders) != len(set(payload.order_ids)):
        raise HTTPException(status_code=404, detail="存在无效订单")
    if any(order.status != PurchaseOrderStatus.PENDING for order in orders):
        raise HTTPException(status_code=409, detail="仅待付款订单可以调整优惠")
    if len({order.user_id for order in orders}) != 1:
        raise HTTPException(status_code=422, detail="打包优惠只能应用于同一客户")
    standards = [order.standard_amount or order.unit_price * order.quantity for order in orders]
    standard_total = sum(standards)
    if payload.package_total > standard_total:
        raise HTTPException(status_code=422, detail="打包价不能高于标准总价")
    allocated = 0
    batch_no = orders[0].batch_no or f"BAT{datetime.now(timezone.utc).year}{min(order.id for order in orders):08d}"
    for index, (order, standard) in enumerate(zip(orders, standards)):
        final_amount = payload.package_total - allocated if index == len(orders) - 1 else round(payload.package_total * standard / standard_total)
        allocated += final_amount
        order.batch_no = batch_no
        order.standard_amount = standard
        order.discount_amount = standard - final_amount
        order.total_amount = final_amount
        order.discount_reason = payload.reason
    db.add(AuditRecord(employee_id=employee.id, action="PACKAGE_DISCOUNT_APPROVED", detail={"order_ids": payload.order_ids, "standard_total": standard_total, "package_total": payload.package_total, "reason": payload.reason}))
    db.commit()
    for order in orders:
        db.refresh(order)
    return [admin_purchase_order_out(order) for order in orders]


@router.put("/orders/{order_id}/contract", response_model=AdminPurchaseOrderOut)
def upload_order_contract(
    order_id: int,
    payload: AdminContractUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_admin),
):
    employee = get_employee(db, user)
    require_permission(employee, "contract.manage")
    order = db.get(PurchaseOrder, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    order.contract_no = payload.contract_no
    order.contract_file = payload.contract_file
    order.contract_version = payload.contract_version
    db.add(AuditRecord(employee_id=employee.id, action="ORDER_CONTRACT_UPDATED", detail={"order_id": order.id, "contract_no": payload.contract_no, "version": payload.contract_version}))
    db.commit()
    db.refresh(order)
    return admin_purchase_order_out(order)


@router.post("/orders/{order_id}/payment-review", response_model=AdminPurchaseOrderOut)
def review_offline_payment(
    order_id: int,
    payload: AdminPaymentReview,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_admin),
):
    employee = get_employee(db, user)
    require_permission(employee, "payment.review")
    order = db.scalar(select(PurchaseOrder).where(PurchaseOrder.id == order_id).with_for_update())
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    if order.status != PurchaseOrderStatus.PAYMENT_CONFIRMING:
        raise HTTPException(status_code=409, detail="订单不在付款待确认状态")
    if payload.approved:
        if payload.actual_paid_amount is None or not payload.finance_receipt:
            raise HTTPException(status_code=422, detail="确认到账必须填写实际到账金额并上传财务收款凭证")
        if payload.actual_paid_amount != order.total_amount:
            raise HTTPException(status_code=422, detail="实际到账金额与订单应付金额不一致")
        order.actual_paid_amount = payload.actual_paid_amount
        order.finance_receipt = payload.finance_receipt
        order.finance_note = payload.note
        activate_paid_order(db, order, order.user)
        action = "OFFLINE_PAYMENT_APPROVED"
    else:
        order.status = PurchaseOrderStatus.PAYMENT_FAILED
        action = "OFFLINE_PAYMENT_REJECTED"
    db.add(AuditRecord(employee_id=employee.id, action=action, detail={"order_id": order.id, "note": payload.note}))
    db.commit()
    db.refresh(order)
    return admin_purchase_order_out(order)


@router.get("/applications", response_model=ApplicationList)
def list_for_review(
    status: ApplicationStatus | None = None,
    keyword: str | None = Query(None, max_length=100),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_admin),
):
    require_any_permission(get_employee(db, user), "application.review", "application.deliver", "application.assign")
    query = (select(Application).outerjoin(Company).outerjoin(User, Application.user_id == User.id)
             .outerjoin(CustomerProfile, CustomerProfile.user_id == User.id)
             .where(Application.status != ApplicationStatus.DRAFT))
    if status:
        query = query.where(Application.status == status)
    if keyword:
        pattern = f"%{keyword.strip()}%"
        query = query.where(or_(
            Application.application_no.ilike(pattern), Company.company_name.ilike(pattern),
            Application.country.ilike(pattern), Application.service_type.ilike(pattern), CustomerProfile.name.ilike(pattern),
        ))
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = db.scalars(query.order_by(Application.created_time.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return ApplicationList(items=[to_out(item) for item in items], total=total, page=page, page_size=page_size)


def customer_account_out(profile: CustomerProfile, order_count: int, company_count: int = 0) -> CustomerAccountOut:
    return CustomerAccountOut(
        id=profile.id, user_id=profile.user_id, customer_type=profile.customer_type, name=profile.name,
        username=profile.user.username, email=profile.user.email, contact_name=profile.contact_name,
        contact_phone=profile.contact_phone, active=profile.active, order_count=order_count, company_count=company_count,
        created_time=profile.created_time,
    )


def list_customer_accounts(db: Session, customer_type: CustomerType) -> list[CustomerAccountOut]:
    profiles = db.scalars(select(CustomerProfile).where(CustomerProfile.customer_type == customer_type).order_by(CustomerProfile.created_time.desc())).all()
    return [customer_account_out(
        profile,
        db.scalar(select(func.count(Application.id)).where(Application.user_id == profile.user_id)) or 0,
        db.scalar(select(func.count(Company.id)).where(Company.user_id == profile.user_id)) or 0,
    ) for profile in profiles]


def customer_account_detail(db: Session, profile_id: int, customer_type: CustomerType) -> CustomerAccountDetailOut:
    profile = db.scalar(select(CustomerProfile).where(CustomerProfile.id == profile_id, CustomerProfile.customer_type == customer_type))
    if not profile:
        raise HTTPException(status_code=404, detail="客户账号不存在")
    applications = db.scalars(select(Application).where(Application.user_id == profile.user_id).order_by(Application.created_time.desc())).all()
    companies = db.scalars(select(Company).where(Company.user_id == profile.user_id).order_by(Company.created_time.desc())).all()
    company_items = []
    for company in companies:
        count = db.scalar(select(func.count(Application.id)).where(Application.company_id == company.id)) or 0
        last_time = db.scalar(select(func.max(Application.created_time)).where(Application.company_id == company.id))
        required = [company.registration_region, company.company_type, company.company_name, company.register_number,
                    company.established_date, company.register_address, company.license_file, company.legal_person]
        company_items.append(CompanyProfileOut(
            **company_out(company).model_dump(), application_count=count,
            completeness=round(sum(bool(value) for value in required) / len(required) * 100),
            last_application_time=last_time,
        ))
    return CustomerAccountDetailOut(
        account=customer_account_out(profile, len(applications), len(companies)),
        applications=[to_out(item) for item in applications], companies=company_items,
    )


def create_customer_account(db: Session, payload: CustomerAccountCreate, customer_type: CustomerType) -> CustomerAccountOut:
    if db.scalar(select(User.id).where(or_(User.username == payload.username, User.email == payload.email))):
        raise HTTPException(status_code=409, detail="用户名或邮箱已存在")
    user = User(username=payload.username, email=str(payload.email), password_hash=hash_password(payload.password), role=UserRole.CUSTOMER)
    db.add(user); db.flush()
    profile = CustomerProfile(
        user_id=user.id, customer_type=customer_type, name=payload.name,
        contact_name=payload.contact_name, contact_phone=payload.contact_phone,
    )
    db.add(profile); db.commit(); db.refresh(profile)
    return customer_account_out(profile, 0)


def update_customer_account(db: Session, profile_id: int, customer_type: CustomerType, payload: CustomerAccountUpdate) -> CustomerAccountOut:
    profile = db.scalar(select(CustomerProfile).where(CustomerProfile.id == profile_id, CustomerProfile.customer_type == customer_type))
    if not profile:
        raise HTTPException(status_code=404, detail="客户账号不存在")
    email = str(payload.email)
    email_owner = db.scalar(select(User.id).where(User.email == email, User.id != profile.user_id))
    if email_owner:
        raise HTTPException(status_code=409, detail="邮箱已被其他账号使用")
    profile.user.email = email
    profile.name, profile.contact_name, profile.contact_phone, profile.active = payload.name, payload.contact_name, payload.contact_phone, payload.active
    db.commit(); db.refresh(profile)
    count = db.scalar(select(func.count(Application.id)).where(Application.user_id == profile.user_id)) or 0
    return customer_account_out(profile, count)


@router.get("/agents", response_model=list[CustomerAccountOut])
def agents(db: Session = Depends(get_db), user: User = Depends(get_current_admin)):
    require_any_permission(get_employee(db, user), "customer.manage", "application.review")
    return list_customer_accounts(db, CustomerType.AGENT)


@router.get("/agents/{profile_id}/detail", response_model=CustomerAccountDetailOut)
def agent_detail(profile_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_admin)):
    require_any_permission(get_employee(db, user), "customer.manage", "application.review")
    return customer_account_detail(db, profile_id, CustomerType.AGENT)


@router.post("/agents", response_model=CustomerAccountOut, status_code=201)
def create_agent(payload: CustomerAccountCreate, db: Session = Depends(get_db), user: User = Depends(get_current_admin)):
    require_permission(get_employee(db, user), "customer.manage")
    return create_customer_account(db, payload, CustomerType.AGENT)


@router.put("/agents/{profile_id}", response_model=CustomerAccountOut)
def update_agent(profile_id: int, payload: CustomerAccountUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_admin)):
    require_permission(get_employee(db, user), "customer.manage")
    return update_customer_account(db, profile_id, CustomerType.AGENT, payload)


@router.get("/direct-customers", response_model=list[CustomerAccountOut])
def direct_customers(db: Session = Depends(get_db), user: User = Depends(get_current_admin)):
    require_any_permission(get_employee(db, user), "customer.manage", "application.review")
    return list_customer_accounts(db, CustomerType.DIRECT)


@router.get("/direct-customers/{profile_id}/detail", response_model=CustomerAccountDetailOut)
def direct_customer_detail(profile_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_admin)):
    require_any_permission(get_employee(db, user), "customer.manage", "application.review")
    return customer_account_detail(db, profile_id, CustomerType.DIRECT)


@router.post("/direct-customers", response_model=CustomerAccountOut, status_code=201)
def create_direct_customer(payload: CustomerAccountCreate, db: Session = Depends(get_db), user: User = Depends(get_current_admin)):
    require_permission(get_employee(db, user), "customer.manage")
    return create_customer_account(db, payload, CustomerType.DIRECT)


@router.put("/direct-customers/{profile_id}", response_model=CustomerAccountOut)
def update_direct_customer(profile_id: int, payload: CustomerAccountUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_admin)):
    require_permission(get_employee(db, user), "customer.manage")
    return update_customer_account(db, profile_id, CustomerType.DIRECT, payload)


@router.get("/applications/{application_id}", response_model=ApplicationFormOut)
def review_detail(
    application_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_admin),
):
    require_any_permission(get_employee(db, user), "application.review", "application.deliver", "application.assign")
    application = get_application_or_404(db, application_id)
    template = application.template or db.scalar(select(ServiceTemplate).where(
        ServiceTemplate.country == application.country,
        ServiceTemplate.service_type == application.service_type,
        ServiceTemplate.status == "ACTIVE",
    ).order_by(ServiceTemplate.version.desc()))
    if not template:
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


@router.patch("/applications/{application_id}/status", response_model=ApplicationOut)
def update_review_status(
    application_id: int,
    payload: AdminStatusUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    application = get_application_or_404(db, application_id)
    employee = get_employee(db, admin)
    transitions = {
        ApplicationStatus.SUBMITTED: {ApplicationStatus.REVIEWING},
        ApplicationStatus.REVIEWING: {ApplicationStatus.NEED_FIX, ApplicationStatus.REGISTERING},
        ApplicationStatus.REGISTERING: {ApplicationStatus.COMPLETED},
        ApplicationStatus.COMPLETED: {ApplicationStatus.COMPLETED},
    }
    if payload.status not in transitions.get(application.status, set()):
        raise HTTPException(status_code=409, detail=f"不允许从 {application.status.value} 转为 {payload.status.value}")
    if payload.status in (ApplicationStatus.REVIEWING, ApplicationStatus.NEED_FIX, ApplicationStatus.REGISTERING):
        require_permission(employee, "application.review")
    elif payload.status == ApplicationStatus.COMPLETED:
        require_permission(employee, "application.deliver")
    if payload.status == ApplicationStatus.NEED_FIX and not payload.note:
        raise HTTPException(status_code=422, detail="要求补资料时必须填写审核意见")
    result_files_updated = payload.status == ApplicationStatus.COMPLETED
    if result_files_updated:
        if not payload.registration_number and not application.registration_number:
            raise HTTPException(status_code=422, detail="审核通过时必须填写下证注册号")
        application.registration_number = payload.registration_number or application.registration_number
        application.certificate_file = payload.certificate_file if payload.certificate_file is not None else application.certificate_file
        application.invoice_file = payload.invoice_file if payload.invoice_file is not None else application.invoice_file
        application.result_file = payload.result_file if payload.result_file is not None else application.result_file
        application.service_expiry_date = payload.service_expiry_date or application.service_expiry_date
    transition_application(db, application, payload.status, admin, payload.note)
    db.add(AuditRecord(application_id=application.id, employee_id=employee.id, action="STATUS_CHANGE", detail={"to_status": payload.status.value, "note": payload.note}))
    db.commit()
    db.refresh(application)
    background_tasks.add_task(
        notify_customer_update, application.user.email, application.application_no,
        application.status, payload.note, result_files_updated,
    )
    return to_out(application)


@router.get("/applications/{application_id}/status-history", response_model=list[StatusHistoryOut])
def review_status_history(
    application_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_admin),
):
    require_any_permission(get_employee(db, user), "application.review", "application.deliver", "application.assign")
    application = get_application_or_404(db, application_id)
    items = db.scalars(select(ApplicationStatusHistory).where(
        ApplicationStatusHistory.application_id == application.id
    ).order_by(ApplicationStatusHistory.created_time.desc())).all()
    return [StatusHistoryOut(
        id=item.id, from_status=item.from_status, to_status=item.to_status, note=item.note,
        operator_name=item.operator.username, created_time=item.created_time,
    ) for item in items]


@router.get("/dashboard", response_model=DashboardOut)
def dashboard(db: Session = Depends(get_db), user: User = Depends(get_current_admin)):
    employee = get_employee(db, user)
    counts = dict(db.execute(
        select(Application.status, func.count())
        .where(Application.status != ApplicationStatus.DRAFT)
        .group_by(Application.status)
    ).all())
    my_tasks = db.scalar(
        select(func.count()).select_from(ApplicationAssignment)
        .join(Application)
        .where(
            ApplicationAssignment.employee_id == employee.id,
            Application.status != ApplicationStatus.DRAFT,
        )
    ) or 0
    return DashboardOut(
        total=sum(counts.values()), submitted=counts.get(ApplicationStatus.SUBMITTED, 0),
        reviewing=counts.get(ApplicationStatus.REVIEWING, 0), need_fix=counts.get(ApplicationStatus.NEED_FIX, 0),
        completed=counts.get(ApplicationStatus.COMPLETED, 0), my_tasks=my_tasks,
    )


@router.get("/employees", response_model=list[EmployeeOut])
def employees(db: Session = Depends(get_db), user: User = Depends(get_current_admin)):
    current = get_employee(db, user)
    require_permission(current, "application.assign")
    items = db.scalars(select(Employee).where(Employee.active.is_(True)).order_by(Employee.display_name)).all()
    return [EmployeeOut(id=item.id, username=item.user.username, email=item.user.email, display_name=item.display_name, active=item.active, role=item.role) for item in items]


@router.get("/profile", response_model=EmployeeOut)
def employee_profile(db: Session = Depends(get_db), user: User = Depends(get_current_admin)):
    item = get_employee(db, user)
    return EmployeeOut(id=item.id, username=item.user.username, email=item.user.email, display_name=item.display_name, active=item.active, role=item.role)


@router.put("/applications/{application_id}/assignment", response_model=AssignmentOut)
def assign_application(application_id: int, payload: AssignmentUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_admin)):
    actor = get_employee(db, user)
    require_permission(actor, "application.assign")
    application = get_application_or_404(db, application_id)
    assignee = db.get(Employee, payload.employee_id)
    if not assignee or not assignee.active:
        raise HTTPException(status_code=422, detail="所选员工不存在或已停用")
    assignment = db.scalar(select(ApplicationAssignment).where(ApplicationAssignment.application_id == application.id))
    if assignment:
        assignment.employee_id, assignment.assigned_by_id = assignee.id, actor.id
    else:
        assignment = ApplicationAssignment(application_id=application.id, employee_id=assignee.id, assigned_by_id=actor.id)
        db.add(assignment)
    db.add(AuditRecord(application_id=application.id, employee_id=actor.id, action="ASSIGN", detail={"employee_id": assignee.id, "employee_name": assignee.display_name}))
    db.commit(); db.refresh(assignment)
    return AssignmentOut(id=assignment.id, application_id=application.id, employee_id=assignee.id, employee_name=assignee.display_name, assigned_by_name=actor.display_name, assigned_time=assignment.assigned_time)


@router.get("/applications/{application_id}/assignment", response_model=AssignmentOut | None)
def get_assignment(application_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_admin)):
    employee = get_employee(db, user)
    require_any_permission(employee, "application.review", "application.deliver", "application.assign")
    get_application_or_404(db, application_id)
    item = db.scalar(select(ApplicationAssignment).where(ApplicationAssignment.application_id == application_id))
    if not item: return None
    return AssignmentOut(id=item.id, application_id=item.application_id, employee_id=item.employee_id, employee_name=item.employee.display_name, assigned_by_name=item.assigned_by.display_name, assigned_time=item.assigned_time)


@router.get("/applications/{application_id}/audit-records", response_model=list[AuditRecordOut])
def audit_records(application_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_admin)):
    employee = get_employee(db, user)
    require_any_permission(employee, "application.review", "application.deliver", "application.assign")
    get_application_or_404(db, application_id)
    items = db.scalars(select(AuditRecord).where(AuditRecord.application_id == application_id).order_by(AuditRecord.created_time.desc())).all()
    return [AuditRecordOut(id=item.id, action=item.action, detail=item.detail, employee_name=item.employee.display_name, created_time=item.created_time) for item in items]


@router.get("/templates", response_model=list[TemplateOut])
def templates(db: Session = Depends(get_db), user: User = Depends(get_current_admin)):
    employee = get_employee(db, user); require_permission(employee, "template.manage")
    items = db.scalars(select(ServiceTemplate).order_by(ServiceTemplate.country, ServiceTemplate.service_type)).all()
    return [TemplateOut(id=item.id, country=item.country, service_type=item.service_type, version=item.version, fields=[FormFieldOut.model_validate(field) for field in sorted(item.form_fields, key=lambda value: value.sort)], materials=[MaterialRequirementOut.model_validate(rule) for rule in sorted(item.material_requirements, key=lambda value: value.sort)]) for item in items]


@router.put("/templates/{template_id}", response_model=TemplateOut)
def update_template(template_id: int, payload: TemplateConfigUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_admin)):
    employee = get_employee(db, user); require_permission(employee, "template.manage")
    template = db.get(ServiceTemplate, template_id)
    if not template: raise HTTPException(status_code=404, detail="模板不存在")
    db.execute(delete(FormField).where(FormField.template_id == template.id))
    db.execute(delete(MaterialRequirement).where(MaterialRequirement.template_id == template.id))
    db.flush()
    for item in payload.fields: db.add(FormField(template_id=template.id, **item.model_dump(exclude={"id"})))
    for item in payload.materials: db.add(MaterialRequirement(template_id=template.id, **item.model_dump(exclude={"id"})))
    db.add(AuditRecord(employee_id=employee.id, action="TEMPLATE_UPDATE", detail={"template_id": template.id, "country": template.country, "service_type": template.service_type}))
    db.commit(); db.refresh(template)
    return TemplateOut(id=template.id, country=template.country, service_type=template.service_type, version=template.version, fields=[FormFieldOut.model_validate(field) for field in sorted(template.form_fields, key=lambda value: value.sort)], materials=[MaterialRequirementOut.model_validate(rule) for rule in sorted(template.material_requirements, key=lambda value: value.sort)])
