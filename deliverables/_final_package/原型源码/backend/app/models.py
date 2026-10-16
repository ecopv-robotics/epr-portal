import enum
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ApplicationStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    REVIEWING = "REVIEWING"
    NEED_FIX = "NEED_FIX"
    REGISTERING = "REGISTERING"
    COMPLETED = "COMPLETED"


class UserRole(str, enum.Enum):
    CUSTOMER = "CUSTOMER"
    STAFF = "STAFF"
    ADMIN = "ADMIN"


class CustomerType(str, enum.Enum):
    AGENT = "AGENT"
    DIRECT = "DIRECT"


class PurchaseOrderStatus(str, enum.Enum):
    PENDING = "PENDING"
    PAYMENT_CONFIRMING = "PAYMENT_CONFIRMING"
    PAID = "PAID"
    CANCELLED = "CANCELLED"
    PAYMENT_FAILED = "PAYMENT_FAILED"
    PARTIALLY_REFUNDED = "PARTIALLY_REFUNDED"
    REFUNDED = "REFUNDED"


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(30), unique=True, nullable=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True, index=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.CUSTOMER, index=True)
    created_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    applications: Mapped[list["Application"]] = relationship(back_populates="user")
    customer_profile: Mapped["CustomerProfile | None"] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")


class VerificationCode(Base):
    __tablename__ = "verification_code"

    id: Mapped[int] = mapped_column(primary_key=True)
    target: Mapped[str] = mapped_column(String(255), index=True)
    channel: Mapped[str] = mapped_column(String(10), index=True)
    purpose: Mapped[str] = mapped_column(String(30), default="REGISTER", index=True)
    code_hash: Mapped[str] = mapped_column(String(64))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class CustomerProfile(Base):
    __tablename__ = "customer_profile"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), unique=True, index=True)
    customer_type: Mapped[CustomerType] = mapped_column(Enum(CustomerType), index=True)
    name: Mapped[str] = mapped_column(String(150), index=True)
    contact_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    user: Mapped[User] = relationship(back_populates="customer_profile")


class Role(Base):
    __tablename__ = "role"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    permissions: Mapped[list] = mapped_column(JSON, default=list)
    created_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    employees: Mapped[list["Employee"]] = relationship(back_populates="role")


class Employee(Base):
    __tablename__ = "employee"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), unique=True, index=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("role.id"), index=True)
    display_name: Mapped[str] = mapped_column(String(100))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    user: Mapped[User] = relationship()
    role: Mapped[Role] = relationship(back_populates="employees")


class Company(Base):
    __tablename__ = "company"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"), nullable=True, index=True)
    company_name: Mapped[str] = mapped_column(String(255), index=True)
    company_name_en: Mapped[str | None] = mapped_column(String(255), nullable=True)
    registration_region: Mapped[str | None] = mapped_column(String(30), nullable=True)
    company_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    register_number: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    established_date: Mapped[str | None] = mapped_column(String(20), nullable=True)
    vat_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    register_address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    license_file: Mapped[str | None] = mapped_column(String(500), nullable=True)
    license_translation_file: Mapped[str | None] = mapped_column(String(500), nullable=True)
    credit_report_file: Mapped[str | None] = mapped_column(String(500), nullable=True)
    br_file: Mapped[str | None] = mapped_column(String(500), nullable=True)
    cr_file: Mapped[str | None] = mapped_column(String(500), nullable=True)
    nnc1_file: Mapped[str | None] = mapped_column(String(500), nullable=True)
    director_index_file: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    legal_person: Mapped["LegalPerson | None"] = relationship(back_populates="company", uselist=False, cascade="all, delete-orphan")


class Application(Base):
    __tablename__ = "application"
    __table_args__ = (UniqueConstraint("purchase_order_id", "instance_index", name="uq_order_service_instance"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    application_no: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("company.id"), nullable=True, index=True)
    template_id: Mapped[int | None] = mapped_column(ForeignKey("service_template.id"), nullable=True, index=True)
    purchase_order_id: Mapped[int | None] = mapped_column(ForeignKey("purchase_order.id"), nullable=True, index=True)
    instance_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    country: Mapped[str] = mapped_column(String(100))
    service_type: Mapped[str] = mapped_column(String(100))
    status: Mapped[ApplicationStatus] = mapped_column(Enum(ApplicationStatus), default=ApplicationStatus.DRAFT)
    created_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    submitted_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    registration_number: Mapped[str | None] = mapped_column(String(150), nullable=True, index=True)
    certificate_file: Mapped[str | None] = mapped_column(String(500), nullable=True)
    invoice_file: Mapped[str | None] = mapped_column(String(500), nullable=True)
    result_file: Mapped[str | None] = mapped_column(String(500), nullable=True)
    service_expiry_date: Mapped[str | None] = mapped_column(String(20), nullable=True)
    user: Mapped[User] = relationship(back_populates="applications")
    company: Mapped[Company | None] = relationship()
    template: Mapped["ServiceTemplate | None"] = relationship()
    store: Mapped["Store | None"] = relationship(back_populates="application", uselist=False, cascade="all, delete-orphan")
    products: Mapped[list["Product"]] = relationship(back_populates="application", cascade="all, delete-orphan")
    material_files: Mapped[list["MaterialFile"]] = relationship(back_populates="application", cascade="all, delete-orphan")
    status_history: Mapped[list["ApplicationStatusHistory"]] = relationship(back_populates="application", cascade="all, delete-orphan")
    assignment: Mapped["ApplicationAssignment | None"] = relationship(back_populates="application", uselist=False)
    purchase_order: Mapped["PurchaseOrder | None"] = relationship(
        back_populates="applications", foreign_keys=[purchase_order_id]
    )


class ServiceTemplate(Base):
    __tablename__ = "service_template"
    __table_args__ = (UniqueConstraint("country", "service_type", "version", name="uq_template_version"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    country: Mapped[str] = mapped_column(String(100), index=True)
    country_label: Mapped[str] = mapped_column(String(150))
    service_type: Mapped[str] = mapped_column(String(100), index=True)
    service_label: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(String(255), default="")
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", index=True)
    form_fields: Mapped[list["FormField"]] = relationship(back_populates="template", cascade="all, delete-orphan")
    material_requirements: Mapped[list["MaterialRequirement"]] = relationship(back_populates="template", cascade="all, delete-orphan")


class LegalPerson(Base):
    __tablename__ = "legal_person"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("company.id"), unique=True, index=True)
    name_cn: Mapped[str | None] = mapped_column(String(100), nullable=True)
    name_en: Mapped[str | None] = mapped_column(String(100), nullable=True)
    certificate_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    certificate_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    gender: Mapped[str | None] = mapped_column(String(20), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    front_file: Mapped[str | None] = mapped_column(String(500), nullable=True)
    back_file: Mapped[str | None] = mapped_column(String(500), nullable=True)
    signature_file: Mapped[str | None] = mapped_column(String(500), nullable=True)
    company: Mapped[Company] = relationship(back_populates="legal_person")


class Store(Base):
    __tablename__ = "store"

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("application.id"), unique=True, index=True)
    platform: Mapped[str | None] = mapped_column(String(100), nullable=True)
    store_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    store_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    company_name_en: Mapped[str | None] = mapped_column(String(255), nullable=True)
    register_city_en: Mapped[str | None] = mapped_column(String(150), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(30), nullable=True)
    register_address_en: Mapped[str | None] = mapped_column(String(500), nullable=True)
    screenshot_file: Mapped[str | None] = mapped_column(String(500), nullable=True)
    application: Mapped[Application] = relationship(back_populates="store")


class Product(Base):
    __tablename__ = "product"

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("application.id"), index=True)
    product_data: Mapped[dict] = mapped_column(JSON, default=dict)
    application: Mapped[Application] = relationship(back_populates="products")


class FormField(Base):
    __tablename__ = "form_field"
    __table_args__ = (UniqueConstraint("template_id", "field_name", name="uq_template_field"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("service_template.id"), index=True)
    field_name: Mapped[str] = mapped_column(String(100))
    label: Mapped[str] = mapped_column(String(150))
    field_type: Mapped[str] = mapped_column(String(30))
    required: Mapped[bool] = mapped_column(Boolean, default=False)
    options: Mapped[list | None] = mapped_column(JSON, nullable=True)
    sort: Mapped[int] = mapped_column(Integer, default=0)
    template: Mapped[ServiceTemplate] = relationship(back_populates="form_fields")


class MaterialRequirement(Base):
    __tablename__ = "material_requirement"
    __table_args__ = (UniqueConstraint("template_id", "material_name", name="uq_template_material"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("service_template.id"), index=True)
    material_name: Mapped[str] = mapped_column(String(150))
    required: Mapped[bool] = mapped_column(Boolean, default=False)
    file_type: Mapped[str] = mapped_column(String(100), default="PDF,JPG,JPEG,PNG")
    description: Mapped[str] = mapped_column(Text, default="")
    sort: Mapped[int] = mapped_column(Integer, default=0)
    template: Mapped[ServiceTemplate] = relationship(back_populates="material_requirements")


class MaterialFile(Base):
    __tablename__ = "material_file"
    __table_args__ = (UniqueConstraint("application_id", "requirement_id", name="uq_application_material"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("application.id"), index=True)
    requirement_id: Mapped[int] = mapped_column(ForeignKey("material_requirement.id"), index=True)
    file_url: Mapped[str] = mapped_column(String(500))
    original_name: Mapped[str] = mapped_column(String(255))
    file_size: Mapped[float] = mapped_column(Float, default=0)
    upload_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    application: Mapped[Application] = relationship(back_populates="material_files")
    requirement: Mapped[MaterialRequirement] = relationship()


class ApplicationStatusHistory(Base):
    __tablename__ = "application_status_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("application.id"), index=True)
    from_status: Mapped[str] = mapped_column(String(30))
    to_status: Mapped[str] = mapped_column(String(30))
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    operator_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)
    created_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    application: Mapped[Application] = relationship(back_populates="status_history")
    operator: Mapped[User] = relationship()


class ApplicationAssignment(Base):
    __tablename__ = "application_assignment"
    __table_args__ = (UniqueConstraint("application_id", name="uq_application_assignment"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("application.id"), index=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employee.id"), index=True)
    assigned_by_id: Mapped[int] = mapped_column(ForeignKey("employee.id"), index=True)
    assigned_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    application: Mapped[Application] = relationship(back_populates="assignment")
    employee: Mapped[Employee] = relationship(foreign_keys=[employee_id])
    assigned_by: Mapped[Employee] = relationship(foreign_keys=[assigned_by_id])


class AuditRecord(Base):
    __tablename__ = "audit_record"

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int | None] = mapped_column(ForeignKey("application.id"), nullable=True, index=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employee.id"), index=True)
    action: Mapped[str] = mapped_column(String(80), index=True)
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    created_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    application: Mapped[Application | None] = relationship()
    employee: Mapped[Employee] = relationship()


class CartItem(Base):
    __tablename__ = "cart_item"
    __table_args__ = (UniqueConstraint("user_id", "service_id", name="uq_cart_user_service"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)
    service_id: Mapped[str] = mapped_column(String(80), index=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    created_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    user: Mapped[User] = relationship()


class PurchaseOrder(Base):
    __tablename__ = "purchase_order"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_no: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)
    service_id: Mapped[str] = mapped_column(String(80), index=True)
    batch_no: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)
    service_year: Mapped[str] = mapped_column(String(50))
    # Legacy columns retained for compatibility. Service information is completed
    # independently on each paid service instance, not during checkout.
    subject_type: Mapped[str] = mapped_column(String(100), default="")
    package_type: Mapped[str] = mapped_column(String(100), default="")
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    unit_price: Mapped[int] = mapped_column(Integer)
    standard_amount: Mapped[int] = mapped_column(Integer, default=0)
    discount_amount: Mapped[int] = mapped_column(Integer, default=0)
    discount_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_amount: Mapped[int] = mapped_column(Integer)
    status: Mapped[PurchaseOrderStatus] = mapped_column(Enum(PurchaseOrderStatus), default=PurchaseOrderStatus.PENDING, index=True)
    payment_method: Mapped[str | None] = mapped_column(String(30), nullable=True)
    payer_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    payment_proof: Mapped[str | None] = mapped_column(String(500), nullable=True)
    actual_paid_amount: Mapped[int | None] = mapped_column(Integer, nullable=True)
    finance_receipt: Mapped[str | None] = mapped_column(String(500), nullable=True)
    finance_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    contract_no: Mapped[str | None] = mapped_column(String(80), nullable=True)
    contract_file: Mapped[str | None] = mapped_column(String(500), nullable=True)
    contract_version: Mapped[str | None] = mapped_column(String(30), nullable=True)
    application_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    created_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    paid_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    user: Mapped[User] = relationship()
    applications: Mapped[list[Application]] = relationship(
        back_populates="purchase_order",
        foreign_keys=[Application.purchase_order_id],
        order_by=Application.instance_index,
    )
