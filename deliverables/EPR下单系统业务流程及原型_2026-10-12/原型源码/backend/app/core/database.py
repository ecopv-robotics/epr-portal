from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import get_settings

settings = get_settings()
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def apply_compatible_schema_updates() -> None:
    """Small additive bridge until Alembic is introduced before production rollout."""
    if engine.dialect.name == "postgresql":
        with engine.begin() as connection:
            enum_exists = connection.scalar(text("SELECT 1 FROM pg_type WHERE typname = 'userrole'"))
            if enum_exists:
                connection.execute(text("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'STAFF'"))
            application_status_exists = connection.scalar(text("SELECT 1 FROM pg_type WHERE typname = 'applicationstatus'"))
            if application_status_exists:
                connection.execute(text("ALTER TYPE applicationstatus ADD VALUE IF NOT EXISTS 'REGISTERING'"))
            purchase_status_exists = connection.scalar(text("SELECT 1 FROM pg_type WHERE typname = 'purchaseorderstatus'"))
            if purchase_status_exists:
                for value in ("PAYMENT_CONFIRMING", "CANCELLED", "PAYMENT_FAILED", "PARTIALLY_REFUNDED", "REFUNDED"):
                    connection.execute(text(f"ALTER TYPE purchaseorderstatus ADD VALUE IF NOT EXISTS '{value}'"))
    inspector = inspect(engine)
    if "application" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("application")}
        if "template_id" not in columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE application ADD COLUMN template_id INTEGER"))
    additions = {
        "user": {
            "role": "VARCHAR(20) DEFAULT 'CUSTOMER' NOT NULL",
        },
        "application": {
            "purchase_order_id": "INTEGER", "instance_index": "INTEGER",
            "reviewed_time": "TIMESTAMP", "review_note": "TEXT",
            "registration_number": "VARCHAR(150)", "certificate_file": "VARCHAR(500)",
            "invoice_file": "VARCHAR(500)", "result_file": "VARCHAR(500)",
            "service_expiry_date": "VARCHAR(20)",
        },
        "company": {
            "user_id": "INTEGER",
            "registration_region": "VARCHAR(30)", "established_date": "VARCHAR(20)",
            "vat_number": "VARCHAR(100)", "credit_report_file": "VARCHAR(500)",
            "license_translation_file": "VARCHAR(500)",
            "nnc1_file": "VARCHAR(500)", "director_index_file": "VARCHAR(500)",
        },
        "legal_person": {
            "gender": "VARCHAR(20)", "contact_email": "VARCHAR(255)", "contact_phone": "VARCHAR(50)",
        },
        "store": {
            "company_name_en": "VARCHAR(255)", "register_city_en": "VARCHAR(150)",
            "postal_code": "VARCHAR(30)", "register_address_en": "VARCHAR(500)",
        },
        "purchase_order": {
            "payment_method": "VARCHAR(30)", "payer_name": "VARCHAR(150)",
            "payment_proof": "VARCHAR(500)",
            "batch_no": "VARCHAR(30)", "standard_amount": "INTEGER DEFAULT 0 NOT NULL",
            "discount_amount": "INTEGER DEFAULT 0 NOT NULL", "discount_reason": "TEXT",
            "actual_paid_amount": "INTEGER", "finance_receipt": "VARCHAR(500)",
            "finance_note": "TEXT", "contract_no": "VARCHAR(80)",
            "contract_file": "VARCHAR(500)", "contract_version": "VARCHAR(30)",
        },
    }
    table_names = set(inspector.get_table_names())
    with engine.begin() as connection:
        for table_name, fields in additions.items():
            if table_name not in table_names:
                continue
            columns = {column["name"] for column in inspector.get_columns(table_name)}
            for field_name, field_type in fields.items():
                if field_name not in columns:
                    connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {field_name} {field_type}"))
        # Records completed by the old workflow have no official registration result yet.
        # Move them back to the new post-review stage so staff can enter certificate data.
        if "application" in table_names:
            connection.execute(text(
                "UPDATE application SET status = 'REGISTERING' "
                "WHERE status = 'COMPLETED' AND registration_number IS NULL"
            ))
        if "company" in table_names and "application" in table_names:
            connection.execute(text(
                "UPDATE company SET user_id = (SELECT application.user_id FROM application "
                "WHERE application.company_id = company.id ORDER BY application.id LIMIT 1) "
                "WHERE user_id IS NULL"
            ))
        if "purchase_order" in table_names and "application" in table_names:
            connection.execute(text(
                "UPDATE purchase_order SET standard_amount = total_amount "
                "WHERE standard_amount IS NULL OR standard_amount = 0"
            ))
            connection.execute(text(
                "UPDATE application SET purchase_order_id = ("
                "SELECT purchase_order.id FROM purchase_order "
                "WHERE purchase_order.application_id = application.id LIMIT 1"
                "), instance_index = COALESCE(instance_index, 1) "
                "WHERE purchase_order_id IS NULL AND EXISTS ("
                "SELECT 1 FROM purchase_order WHERE purchase_order.application_id = application.id)"
            ))
