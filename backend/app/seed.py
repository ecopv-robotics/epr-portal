from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.catalog import EUROPEAN_COUNTRIES, MATERIALS, SERVICES, get_product_fields
from app.models import Application, ApplicationAssignment, ApplicationStatus, CountryResponsibility, CustomerProfile, CustomerType, DeliveryTask, Employee, FormField, MaterialRequirement, Role, ServiceTemplate, User, UserRole


def seed_demo_user(db: Session) -> None:
    demo = db.scalar(select(User).where(User.email == "demo@eprflow.com"))
    if not demo:
        demo = User(username="demo", email="demo@eprflow.com", phone="13800000000", password_hash=hash_password("Demo123!"))
        db.add(demo)
    demo.password_hash = hash_password("Demo123!")
    demo.role = UserRole.CUSTOMER
    admin = db.scalar(select(User).where(User.email == "admin@eprflow.com"))
    if not admin:
        admin = User(username="admin", email="admin@eprflow.com", password_hash=hash_password("Demo123!"))
        db.add(admin)
    admin.password_hash = hash_password("Demo123!")
    admin.role = UserRole.ADMIN
    internal_accounts = [
        ("sales", "sales@eprflow.com", "Demo123!", "SALES", "销售1"),
        ("finance", "finance@eprflow.com", "Demo123!", "FINANCE", "财务专员"),
        ("business", "business@eprflow.com", "Demo123!", "BUSINESS", "商务1"),
        ("delivery", "delivery@eprflow.com", "Demo123!", "DELIVERY", "交付1"),
        # Keep the original staff account as a compatibility alias for business review.
        ("staff", "staff@eprflow.com", "Demo123!", "BUSINESS", "商务审核（兼容账号）"),
    ]
    for index in range(2, 6):
        internal_accounts.extend((
            (f"sales{index}", f"sales{index}@eprflow.com", "Demo123!", "SALES", f"销售{index}"),
            (f"business{index}", f"business{index}@eprflow.com", "Demo123!", "BUSINESS", f"商务{index}"),
            (f"delivery{index}", f"delivery{index}@eprflow.com", "Demo123!", "DELIVERY", f"交付{index}"),
        ))
    internal_users: list[tuple[User, str, str]] = []
    for username, email, password, role_code, display_name in internal_accounts:
        employee_user = db.scalar(select(User).where(User.email == email))
        if not employee_user:
            employee_user = User(username=username, email=email, password_hash=hash_password(password))
            db.add(employee_user)
        employee_user.password_hash = hash_password(password)
        employee_user.role = UserRole.STAFF
        internal_users.append((employee_user, role_code, display_name))
    db.commit()
    role_configs = {
        "ADMIN": ("系统管理员", ["dashboard", "application.review", "application.deliver", "application.assign", "employee.manage", "template.manage", "customer.manage", "order.create", "discount.approve", "contract.manage", "payment.review"]),
        "SALES": ("销售", ["dashboard", "customer.manage", "order.create", "discount.approve", "contract.manage"]),
        "FINANCE": ("财务", ["dashboard", "payment.review"]),
        "BUSINESS": ("商务", ["dashboard", "application.review"]),
        "DELIVERY": ("交付", ["dashboard", "application.deliver"]),
        "REVIEWER": ("商务", ["dashboard", "application.review"]),
    }
    roles: dict[str, Role] = {}
    for code, (name, permissions) in role_configs.items():
        role = db.scalar(select(Role).where(Role.code == code))
        if not role:
            role = Role(code=code, name=name, permissions=permissions)
            db.add(role)
            db.flush()
        role.name, role.permissions = name, permissions
        roles[code] = role
    for user, role_code, display_name in ((admin, "ADMIN", "系统管理员"), *internal_users):
        employee = db.scalar(select(Employee).where(Employee.user_id == user.id))
        if not employee:
            employee = Employee(user_id=user.id, role_id=roles[role_code].id, display_name=display_name)
            db.add(employee)
        employee.role_id, employee.display_name = roles[role_code].id, display_name
        employee.active = user.username != "staff"
    db.commit()
    delivery_employees = db.scalars(select(Employee).join(Role).where(
        Role.code == "DELIVERY", Employee.active.is_(True)
    ).order_by(Employee.display_name)).all()
    for index, (country, _) in enumerate(EUROPEAN_COUNTRIES):
        responsibility = db.scalar(select(CountryResponsibility).where(CountryResponsibility.country == country))
        defaults = {"delivery_employee_id": delivery_employees[index % 5].id}
        if not responsibility:
            db.add(CountryResponsibility(country=country, **defaults))
    # Older installations did not distinguish customer kinds. Keep those accounts
    # visible by classifying them as direct customers during the additive upgrade.
    customers = db.scalars(select(User).where(User.role == UserRole.CUSTOMER)).all()
    for customer in customers:
        if not customer.customer_profile:
            db.add(CustomerProfile(
                user_id=customer.id, customer_type=CustomerType.DIRECT,
                name="演示直客" if customer.id == demo.id else customer.username,
                contact_name="演示客户" if customer.id == demo.id else None,
                contact_phone=customer.phone,
            ))
    delivery_employee = db.scalar(select(Employee).join(Role).where(Role.code == "DELIVERY", Employee.active.is_(True)))
    admin_employee = db.scalar(select(Employee).join(Role).where(Role.code == "ADMIN", Employee.active.is_(True)))
    if delivery_employee and admin_employee:
        delivery_applications = db.scalars(select(Application).where(
            Application.status.in_((ApplicationStatus.REGISTERING, ApplicationStatus.COMPLETED))
        )).all()
        for application in delivery_applications:
            responsibility = db.scalar(select(CountryResponsibility).where(
                CountryResponsibility.country == application.country
            ))
            responsible_delivery = responsibility.delivery_employee if responsibility else delivery_employee
            if not application.delivery_task:
                application.delivery_task = DeliveryTask(
                    stage="COMPLETED" if application.status == ApplicationStatus.COMPLETED else "RECEIVED",
                    updated_by_id=admin_employee.id,
                )
            if not application.assignment:
                db.add(ApplicationAssignment(
                    application_id=application.id,
                    employee_id=responsible_delivery.id,
                    assigned_by_id=admin_employee.id,
                ))
            elif application.assignment.employee_id != responsible_delivery.id:
                application.assignment.employee_id = responsible_delivery.id
                application.assignment.assigned_by_id = admin_employee.id
    db.commit()


def seed_service_catalog(db: Session) -> None:
    existing = {
        (item.country, item.service_type): item
        for item in db.scalars(select(ServiceTemplate).where(ServiceTemplate.version == 1)).all()
    }
    for country, country_cn in EUROPEAN_COUNTRIES:
        for service, service_label, description in SERVICES:
            template = existing.get((country, service))
            if not template:
                template = ServiceTemplate(
                    country=country, country_label=f"{country_cn} ({country})",
                    service_type=service, service_label=service_label,
                    description=description, version=1, status="ACTIVE",
                )
                db.add(template)
                db.flush()
            template.country_label = f"{country_cn} ({country})"
            template.service_label = service_label
            template.description = description
            template.status = "ACTIVE"

            configured_fields = get_product_fields(country, service)
            configured_names = {field[0] for field in configured_fields}
            existing_fields = {field.field_name: field for field in template.form_fields}
            for sort, (name, label, field_type, required, options) in enumerate(configured_fields, 1):
                field = existing_fields.get(name)
                if not field:
                    field = FormField(template_id=template.id, field_name=name)
                    db.add(field)
                field.label, field.field_type, field.required, field.options, field.sort = label, field_type, required, options, sort
            for name, field in existing_fields.items():
                if name not in configured_names:
                    db.delete(field)

            existing_materials = {item.material_name: item for item in template.material_requirements}
            for sort, (name, required) in enumerate(MATERIALS[service], 1):
                requirement = existing_materials.get(name)
                if not requirement:
                    requirement = MaterialRequirement(template_id=template.id, material_name=name)
                    db.add(requirement)
                requirement.required = required
                requirement.file_type = "PDF,JPG,JPEG,PNG"
                requirement.description = "单个文件不超过 20MB"
                requirement.sort = sort
    db.commit()
    applications = db.scalars(select(Application).where(Application.template_id.is_(None))).all()
    for application in applications:
        application.template_id = db.scalar(select(ServiceTemplate.id).where(
            ServiceTemplate.country == application.country,
            ServiceTemplate.service_type == application.service_type,
            ServiceTemplate.status == "ACTIVE",
        ))
    db.commit()
