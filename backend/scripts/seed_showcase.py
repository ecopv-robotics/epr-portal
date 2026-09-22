"""Create idempotent showcase customers, companies and applications for local demos."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import select

from app.core.database import SessionLocal, apply_compatible_schema_updates
from app.core.security import hash_password
from app.models import (
    Application, ApplicationStatus, Company, CustomerProfile, CustomerType,
    LegalPerson, Product, ServiceTemplate, Store, User, UserRole,
)


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


def seed() -> None:
    apply_compatible_schema_updates()
    now = datetime.now(timezone.utc)
    stored_files = list(Path("storage").glob("*"))
    pdf_name = next((item.name for item in stored_files if item.suffix.lower() == ".pdf"), None)
    image_name = next((item.name for item in stored_files if item.suffix.lower() in (".png", ".jpg", ".jpeg")), None)
    demo_pdf = f"/files/{pdf_name}" if pdf_name else None
    demo_image = f"/files/{image_name}" if image_name else demo_pdf
    with SessionLocal() as db:
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
        db.commit()
        print(f"Seeded {len(ACCOUNTS)} accounts and {len(APPLICATIONS)} applications. Password: Demo123!")


if __name__ == "__main__":
    seed()
