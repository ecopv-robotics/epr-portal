"""Create idempotent showcase customers, companies and applications for local demos."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import delete, select

from app.core.database import SessionLocal, apply_compatible_schema_updates
from app.core.security import hash_password
from app.models import (
    Application, ApplicationAssignment, ApplicationStatus, ApplicationStatusHistory, AuditRecord,
    Company, CustomerProfile, CustomerType, Employee, LegalPerson, MaterialFile, Product,
    PurchaseOrder, PurchaseOrderStatus, Role, ServiceTemplate, Store, User, UserRole,
)
from app.modules.portal.router import activate_paid_order
from app.portal_catalog import PORTAL_SERVICE_BY_ID
from app.seed import seed_demo_user, seed_service_catalog


ACCOUNTS = [
    ("showcase.agent.eu", "showcase.agent.eu@eprflow.com", CustomerType.AGENT, "欧桥合规代理", "陈经理", "13810001001"),
    ("showcase.agent.global", "showcase.agent.global@eprflow.com", CustomerType.AGENT, "环球合规服务", "林顾问", "13810001002"),
    ("showcase.direct.star", "showcase.direct.star@eprflow.com", CustomerType.DIRECT, "星河智能科技", "张女士", "13810002001"),
    ("showcase.direct.ocean", "showcase.direct.ocean@eprflow.com", CustomerType.DIRECT, "海拓跨境贸易", "王先生", "13810002002"),
]

APPLICATIONS = [
    ("SHOW2026000001", "欧桥电子科技有限公司", "Germany", "WEEE", ApplicationStatus.SUBMITTED),
    ("SHOW2026000002", "欧桥家居用品有限公司", "France", "Packaging", ApplicationStatus.REVIEWING),
    ("SHOW2026000003", "环球新能源有限公司", "Germany", "Battery", ApplicationStatus.NEED_FIX),
    ("SHOW2026000004", "环球餐饮用品有限公司", "Italy", "SUP", ApplicationStatus.REGISTERING),
    ("SHOW2026000005", "星河智能科技有限公司", "Germany", "WEEE", ApplicationStatus.COMPLETED),
    ("SHOW2026000006", "星河包装制品有限公司", "Spain", "Packaging", ApplicationStatus.DRAFT),
    ("SHOW2026000007", "海拓数码有限公司", "Netherlands", "WEEE", ApplicationStatus.REVIEWING),
    ("SHOW2026000008", "海拓电池科技有限公司", "France", "Battery", ApplicationStatus.COMPLETED),
]

# Orders waiting for a specific role action. User index points to ACCOUNTS.
ORDER_SCENARIOS = [
    ("SHOW-SALES-001", 2, "de-weee", PurchaseOrderStatus.PENDING, 0, None, "销售待联系：标准价订单，合同未上传"),
    ("SHOW-ADMIN-001", 2, "fr-pack", PurchaseOrderStatus.PENDING, 0, None, "管理员待处理：可与同客户订单设置打包优惠"),
    ("SHOW-ADMIN-002", 2, "de-battery-brand", PurchaseOrderStatus.PENDING, 120, "SHOW-BATCH-001", "管理员示例：已批准打包优惠并完成分摊"),
    ("SHOW-FIN-001", 3, "de-weee", PurchaseOrderStatus.PAYMENT_CONFIRMING, 0, None, "财务待处理：客户已上传付款凭证"),
    ("SHOW-FIN-002", 3, "fr-pack", PurchaseOrderStatus.PAYMENT_FAILED, 0, None, "财务示例：付款信息不符，已驳回"),
]

# Paid orders with service instances waiting for business or delivery actions.
WORKFLOW_SCENARIOS = [
    ("SHOW-BIZ-SUB", "SHOWROLE20260001", 2, "de-weee", ApplicationStatus.SUBMITTED),
    ("SHOW-BIZ-REV", "SHOWROLE20260002", 2, "fr-pack", ApplicationStatus.REVIEWING),
    ("SHOW-BIZ-FIX", "SHOWROLE20260003", 3, "de-battery-brand", ApplicationStatus.NEED_FIX),
    ("SHOW-DEL-REG", "SHOWROLE20260004", 3, "fr-plastic", ApplicationStatus.REGISTERING),
    ("SHOW-DEL-DONE", "SHOWROLE20260005", 2, "de-weee", ApplicationStatus.COMPLETED),
]


def seed() -> None:
    apply_compatible_schema_updates()
    now = datetime.now(timezone.utc)
    stored_files = list(Path("storage").glob("*"))
    pdf_name = next((item.name for item in stored_files if item.suffix.lower() == ".pdf"), None)
    image_name = next((item.name for item in stored_files if item.suffix.lower() in (".png", ".jpg", ".jpeg")), None)
    demo_pdf = f"/files/{pdf_name}" if pdf_name else None
    demo_image = f"/files/{image_name}" if image_name else demo_pdf
    with SessionLocal() as db:
        seed_demo_user(db)
        seed_service_catalog(db)
        users: list[User] = []
        for username, email, customer_type, name, contact_name, contact_phone in ACCOUNTS:
            user = db.scalar(select(User).where(User.email == email))
            if not user:
                user = User(username=username, email=email, password_hash=hash_password("Demo123!"), role=UserRole.CUSTOMER)
                db.add(user)
                db.flush()
            profile = db.scalar(select(CustomerProfile).where(CustomerProfile.user_id == user.id))
            if not profile:
                profile = CustomerProfile(user_id=user.id, customer_type=customer_type, name=name)
                db.add(profile)
            profile.customer_type = customer_type
            profile.name = name
            profile.contact_name = contact_name
            profile.contact_phone = contact_phone
            profile.active = True
            users.append(user)
        db.flush()

        for index, (application_no, company_name, country, service_type, status) in enumerate(APPLICATIONS):
            user = users[index // 2]
            company = db.scalar(select(Company).where(Company.user_id == user.id, Company.company_name == company_name))
            if not company:
                company = Company(user_id=user.id, company_name=company_name)
                db.add(company)
                db.flush()
            company.registration_region = "MAINLAND_CHINA"
            company.company_type = "有限责任公司"
            company.register_number = f"91310000SHOW{index + 1:04d}"
            company.established_date = f"202{index % 5 + 1}-0{index % 8 + 1}-15"
            company.register_address = f"上海市浦东新区示范路 {100 + index} 号"
            company.license_file = demo_image
            company.credit_report_file = demo_pdf
            legal = company.legal_person or LegalPerson(company_id=company.id)
            db.add(legal)
            legal.name_cn = ["陈晓", "李敏", "王磊", "赵婷"][index // 2]
            legal.name_en = ["Xiao Chen", "Min Li", "Lei Wang", "Ting Zhao"][index // 2]
            legal.certificate_type = "ID_CARD"
            legal.gender = "FEMALE" if index // 2 in (0, 3) else "MALE"
            legal.contact_email = user.email
            legal.contact_phone = ACCOUNTS[index // 2][5]
            legal.front_file = demo_image
            legal.back_file = demo_image
            legal.signature_file = demo_image

            template = db.scalar(select(ServiceTemplate).where(
                ServiceTemplate.country == country, ServiceTemplate.service_type == service_type,
                ServiceTemplate.status == "ACTIVE",
            ).order_by(ServiceTemplate.version.desc()))
            application = db.scalar(select(Application).where(Application.application_no == application_no))
            if not application:
                application = Application(application_no=application_no, user_id=user.id, country=country, service_type=service_type)
                db.add(application)
                db.flush()
            application.user_id = user.id
            application.company_id = company.id
            application.template_id = template.id if template else None
            application.status = status
            application.submitted_time = None if status == ApplicationStatus.DRAFT else now - timedelta(days=10 - index)
            application.reviewed_time = now - timedelta(days=1) if status == ApplicationStatus.COMPLETED else None
            application.review_note = "请补充最新店铺后台截图" if status == ApplicationStatus.NEED_FIX else None
            if status == ApplicationStatus.COMPLETED:
                application.registration_number = f"EPR-{country[:2].upper()}-{20260000 + index}"
                application.certificate_file = demo_pdf
                application.service_expiry_date = "2027-12-31"
            else:
                application.registration_number = None
                application.certificate_file = None
                application.service_expiry_date = None
            store = application.store or Store(application_id=application.id)
            db.add(store)
            store.platform = "Amazon"
            store.store_name = f"{company_name[:4]}旗舰店"
            store.store_url = f"https://example.com/store/{application_no.lower()}"
            store.company_name_en = company_name
            store.register_city_en = "Shanghai"
            store.postal_code = "200120"
            store.register_address_en = f"No. {100 + index}, Demo Road, Shanghai"
            if not application.products:
                db.add(Product(application_id=application.id, product_data={"name": f"演示产品 {index + 1}", "brand": "DemoBrand", "model": f"M-{index + 1:03d}", "weight": 1.2}))

        # Role-specific order scenarios for sales, administrator and finance.
        for order_no, user_index, service_id, status, discount, batch_no, note in ORDER_SCENARIOS:
            user = users[user_index]
            service = PORTAL_SERVICE_BY_ID[service_id]
            order = db.scalar(select(PurchaseOrder).where(PurchaseOrder.order_no == order_no))
            if not order:
                order = PurchaseOrder(
                    order_no=order_no, user_id=user.id, service_id=service_id,
                    service_year=service["service_years"][0], quantity=1,
                    unit_price=service["price"], standard_amount=service["price"],
                    total_amount=service["price"],
                )
                db.add(order)
            order.user_id = user.id
            order.service_id = service_id
            order.service_year = service["service_years"][0]
            order.quantity = 1
            order.unit_price = service["price"]
            order.standard_amount = service["price"]
            order.discount_amount = discount
            order.total_amount = service["price"] - discount
            order.discount_reason = "多项服务合作优惠" if discount else None
            order.batch_no = batch_no
            order.status = status
            order.payment_method = "OFFLINE" if status in (PurchaseOrderStatus.PAYMENT_CONFIRMING, PurchaseOrderStatus.PAYMENT_FAILED) else None
            order.payer_name = user.customer_profile.name if order.payment_method else None
            order.payment_proof = demo_pdf if order.payment_method else None
            order.finance_note = "付款账户与合同主体不一致，请客户重新提交" if status == PurchaseOrderStatus.PAYMENT_FAILED else note
            order.contract_no = "HT-SHOW-2026-001" if order_no == "SHOW-SALES-001" else None
            order.contract_file = demo_pdf if order_no == "SHOW-SALES-001" else None
            order.contract_version = "V1" if order.contract_file else None

        db.flush()
        admin_employee = db.scalar(select(Employee).join(Role).where(Role.code == "ADMIN"))
        business_employee = db.scalar(select(Employee).join(Role).where(Role.code == "BUSINESS"))
        delivery_employee = db.scalar(select(Employee).join(Role).where(Role.code == "DELIVERY"))

        # Paid service orders create real instances, then place each instance at a
        # workflow stage so business and delivery accounts have actionable queues.
        for scenario_index, (order_no, application_no, user_index, service_id, app_status) in enumerate(WORKFLOW_SCENARIOS):
            user = users[user_index]
            service = PORTAL_SERVICE_BY_ID[service_id]
            order = db.scalar(select(PurchaseOrder).where(PurchaseOrder.order_no == order_no))
            if not order:
                order = PurchaseOrder(
                    order_no=order_no, user_id=user.id, service_id=service_id,
                    service_year=service["service_years"][0], quantity=1,
                    unit_price=service["price"], standard_amount=service["price"],
                    discount_amount=0, total_amount=service["price"],
                )
                db.add(order)
                db.flush()
            order.user_id = user.id
            order.service_id = service_id
            order.service_year = service["service_years"][0]
            order.quantity = 1
            order.unit_price = service["price"]
            order.standard_amount = service["price"]
            order.discount_amount = 0
            order.total_amount = service["price"]
            order.payment_method = "OFFLINE"
            order.payer_name = user.customer_profile.name
            order.payment_proof = demo_pdf
            order.actual_paid_amount = service["price"]
            order.finance_receipt = demo_pdf
            order.finance_note = "演示数据：财务已确认到账"
            activate_paid_order(db, order, user)
            db.flush()
            application = db.scalar(select(Application).where(
                Application.purchase_order_id == order.id,
                Application.instance_index == 1,
            ))
            if not application:
                raise RuntimeError(f"Failed to create service instance for {order_no}")
            application.application_no = application_no
            application.status = app_status
            application.company_id = db.scalar(select(Company.id).where(Company.user_id == user.id).order_by(Company.id))
            application.submitted_time = now - timedelta(days=6 - scenario_index)
            application.reviewed_time = now - timedelta(days=1) if app_status in (ApplicationStatus.REGISTERING, ApplicationStatus.COMPLETED) else None
            application.review_note = "请补充最新店铺后台截图，并确认品牌信息" if app_status == ApplicationStatus.NEED_FIX else None
            if app_status == ApplicationStatus.COMPLETED:
                application.registration_number = "DE-WEEE-SHOW-2026-001"
                application.certificate_file = demo_pdf
                application.invoice_file = demo_pdf
                application.result_file = demo_pdf
                application.service_expiry_date = "2027-12-31"
            else:
                application.registration_number = None
                application.certificate_file = None
                application.invoice_file = None
                application.result_file = None
                application.service_expiry_date = None

            store = application.store or Store(application_id=application.id)
            db.add(store)
            store.platform = "Amazon"
            store.store_name = f"角色流程测试店铺 {scenario_index + 1}"
            store.store_url = f"https://example.com/role-scenario/{scenario_index + 1}"
            store.screenshot_file = demo_image
            if not application.products:
                db.add(Product(application_id=application.id, product_data={"name": f"角色测试产品 {scenario_index + 1}", "brand": "RoleDemo", "model": f"R-{scenario_index + 1:03d}"}))

            if demo_pdf and application.template:
                db.execute(delete(MaterialFile).where(MaterialFile.application_id == application.id))
                requirements = sorted(application.template.material_requirements, key=lambda item: item.sort)
                selected_requirements = requirements[:-1] if app_status == ApplicationStatus.NEED_FIX else requirements
                for requirement in selected_requirements:
                    db.add(MaterialFile(
                        application_id=application.id, requirement_id=requirement.id,
                        file_url=demo_pdf, original_name=f"演示-{requirement.material_name}.pdf", file_size=8,
                    ))

            db.execute(delete(ApplicationStatusHistory).where(ApplicationStatusHistory.application_id == application.id))
            history_steps = [(ApplicationStatus.DRAFT, ApplicationStatus.SUBMITTED, user.id, "客户提交申请")]
            if app_status in (ApplicationStatus.REVIEWING, ApplicationStatus.NEED_FIX, ApplicationStatus.REGISTERING, ApplicationStatus.COMPLETED):
                history_steps.append((ApplicationStatus.SUBMITTED, ApplicationStatus.REVIEWING, business_employee.user_id, "商务开始整体审核"))
            if app_status == ApplicationStatus.NEED_FIX:
                history_steps.append((ApplicationStatus.REVIEWING, ApplicationStatus.NEED_FIX, business_employee.user_id, application.review_note))
            if app_status in (ApplicationStatus.REGISTERING, ApplicationStatus.COMPLETED):
                history_steps.append((ApplicationStatus.REVIEWING, ApplicationStatus.REGISTERING, business_employee.user_id, "材料整体审核通过，转交交付"))
            if app_status == ApplicationStatus.COMPLETED:
                history_steps.append((ApplicationStatus.REGISTERING, ApplicationStatus.COMPLETED, delivery_employee.user_id, "官方下证，服务完成"))
            for from_status, to_status, operator_id, history_note in history_steps:
                db.add(ApplicationStatusHistory(
                    application_id=application.id, from_status=from_status.value, to_status=to_status.value,
                    note=history_note, operator_id=operator_id,
                ))

            assignee = delivery_employee if app_status in (ApplicationStatus.REGISTERING, ApplicationStatus.COMPLETED) else business_employee
            assignment = db.scalar(select(ApplicationAssignment).where(ApplicationAssignment.application_id == application.id))
            if not assignment:
                assignment = ApplicationAssignment(
                    application_id=application.id, employee_id=assignee.id, assigned_by_id=admin_employee.id,
                )
                db.add(assignment)
            else:
                assignment.employee_id = assignee.id
                assignment.assigned_by_id = admin_employee.id
            if not db.scalar(select(AuditRecord.id).where(
                AuditRecord.application_id == application.id, AuditRecord.action == "SHOWCASE_SCENARIO_ASSIGNED"
            )):
                db.add(AuditRecord(
                    application_id=application.id, employee_id=admin_employee.id,
                    action="SHOWCASE_SCENARIO_ASSIGNED",
                    detail={"role": assignee.role.code, "scenario": app_status.value},
                ))
        db.commit()
        print(
            f"Seeded {len(ACCOUNTS)} customer accounts, {len(APPLICATIONS)} showcase applications, "
            f"{len(ORDER_SCENARIOS)} role orders and {len(WORKFLOW_SCENARIOS)} workflow instances."
        )


if __name__ == "__main__":
    seed()
