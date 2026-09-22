from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import ApplicationStatus, CustomerType, UserRole


class LoginRequest(BaseModel):
    account: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=6, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    phone: str | None
    email: EmailStr | None
    role: UserRole


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class ApplicationCreate(BaseModel):
    country: str = Field(min_length=2, max_length=100)
    service_type: str = Field(min_length=2, max_length=100)
    company_id: int | None = None


class ApplicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    application_no: str
    company_name: str | None = None
    registration_number: str | None = None
    certificate_file: str | None = None
    invoice_file: str | None = None
    result_file: str | None = None
    service_expiry_date: str | None = None
    agent_name: str | None = None
    country: str
    service_type: str
    status: ApplicationStatus
    created_time: datetime
    submitted_time: datetime | None
    reviewed_time: datetime | None = None
    review_note: str | None = None


class ApplicationList(BaseModel):
    items: list[ApplicationOut]
    total: int
    page: int
    page_size: int


class ServiceOption(BaseModel):
    value: str
    label: str
    description: str


class CountryOption(BaseModel):
    value: str
    label: str
    services: list[ServiceOption]


class FormFieldOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    field_name: str
    label: str
    field_type: str
    required: bool
    options: list | None
    sort: int


class MaterialRequirementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    material_name: str
    required: bool
    file_type: str
    description: str
    sort: int


class TemplateOut(BaseModel):
    id: int
    country: str
    service_type: str
    version: int
    fields: list[FormFieldOut]
    materials: list[MaterialRequirementOut]


class LegalPersonData(BaseModel):
    name_cn: str | None = None
    name_en: str | None = None
    certificate_type: str | None = None
    certificate_number: str | None = None
    gender: str | None = None
    contact_email: EmailStr | None = None
    contact_phone: str | None = None
    front_file: str | None = None
    back_file: str | None = None
    signature_file: str | None = None


class CompanyData(BaseModel):
    id: int | None = None
    company_name: str = Field(min_length=1, max_length=255)
    company_name_en: str | None = None
    registration_region: str | None = None
    company_type: str | None = None
    register_number: str | None = None
    established_date: str | None = None
    vat_number: str | None = None
    register_address: str | None = None
    license_file: str | None = None
    license_translation_file: str | None = None
    credit_report_file: str | None = None
    br_file: str | None = None
    cr_file: str | None = None
    nnc1_file: str | None = None
    director_index_file: str | None = None
    legal_person: LegalPersonData | None = None


class CompanyOut(CompanyData):
    id: int
    created_time: datetime


class CompanyProfileOut(CompanyOut):
    application_count: int = 0
    completeness: int = 0
    last_application_time: datetime | None = None


class StoreData(BaseModel):
    platform: str | None = None
    store_url: str | None = None
    store_name: str | None = None
    company_name_en: str | None = None
    register_city_en: str | None = None
    postal_code: str | None = None
    register_address_en: str | None = None
    screenshot_file: str | None = None


class ProductData(BaseModel):
    id: int | None = None
    product_data: dict


class MaterialFileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    requirement_id: int
    file_url: str
    original_name: str
    file_size: float
    upload_time: datetime
    auto_synced: bool = False


class UploadOut(BaseModel):
    file_url: str
    original_name: str
    file_size: int


class ApplicationFormOut(BaseModel):
    application: ApplicationOut
    template: TemplateOut
    company: CompanyOut | None
    store: StoreData | None
    products: list[ProductData]
    material_files: list[MaterialFileOut]


class StatusHistoryOut(BaseModel):
    id: int
    from_status: str
    to_status: str
    note: str | None
    operator_name: str
    created_time: datetime


class AdminStatusUpdate(BaseModel):
    status: ApplicationStatus
    note: str | None = Field(default=None, max_length=2000)
    registration_number: str | None = Field(default=None, max_length=150)
    certificate_file: str | None = Field(default=None, max_length=500)
    invoice_file: str | None = Field(default=None, max_length=500)
    result_file: str | None = Field(default=None, max_length=500)
    service_expiry_date: str | None = Field(default=None, max_length=20)


class DashboardOut(BaseModel):
    total: int
    submitted: int
    reviewing: int
    need_fix: int
    completed: int
    my_tasks: int


class RoleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    name: str
    permissions: list


class EmployeeOut(BaseModel):
    id: int
    username: str
    email: str | None
    display_name: str
    active: bool
    role: RoleOut


class AssignmentUpdate(BaseModel):
    employee_id: int


class AssignmentOut(BaseModel):
    id: int
    application_id: int
    employee_id: int
    employee_name: str
    assigned_by_name: str
    assigned_time: datetime


class AuditRecordOut(BaseModel):
    id: int
    action: str
    detail: dict
    employee_name: str
    created_time: datetime


class FormFieldConfig(BaseModel):
    id: int | None = None
    field_name: str = Field(min_length=1, max_length=100)
    label: str = Field(min_length=1, max_length=150)
    field_type: str = Field(pattern="^(text|number|select|date|upload)$")
    required: bool = False
    options: list | None = None
    sort: int = 0


class MaterialRuleConfig(BaseModel):
    id: int | None = None
    material_name: str = Field(min_length=1, max_length=150)
    required: bool = False
    file_type: str = Field(min_length=1, max_length=100)
    description: str = ""
    sort: int = 0


class TemplateConfigUpdate(BaseModel):
    fields: list[FormFieldConfig]
    materials: list[MaterialRuleConfig]


class SubmissionValidationError(BaseModel):
    missing_fields: list[str]


class CustomerAccountCreate(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    name: str = Field(min_length=1, max_length=150)
    contact_name: str | None = Field(default=None, max_length=100)
    contact_phone: str | None = Field(default=None, max_length=30)


class CustomerAccountUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    contact_name: str | None = Field(default=None, max_length=100)
    contact_phone: str | None = Field(default=None, max_length=30)
    active: bool = True


class CustomerAccountOut(BaseModel):
    id: int
    user_id: int
    customer_type: CustomerType
    name: str
    username: str
    email: EmailStr | None
    contact_name: str | None
    contact_phone: str | None
    active: bool
    order_count: int
    company_count: int = 0
    created_time: datetime


class CustomerAccountDetailOut(BaseModel):
    account: CustomerAccountOut
    applications: list[ApplicationOut]
    companies: list[CompanyProfileOut]
