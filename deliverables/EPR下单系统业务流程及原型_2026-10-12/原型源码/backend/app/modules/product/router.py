from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models import Product, User
from app.modules.application.service import ensure_editable, get_owned_application
from app.schemas import ProductData

router = APIRouter(tags=["产品资料"])


@router.put("/applications/{application_id}/products", response_model=list[ProductData])
def replace_products(
    application_id: int,
    payload: list[ProductData],
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    application = get_owned_application(db, user, application_id)
    ensure_editable(application)
    fields = {field.field_name: field for field in application.template.form_fields} if application.template else {}
    normalized_payload: list[dict] = []
    for index, item in enumerate(payload, 1):
        product_data = {name: value for name, value in item.product_data.items() if name in fields}
        for name, field in fields.items():
            value = product_data.get(name)
            if field.field_type == "select" and value not in (None, "") and value not in (field.options or []):
                raise HTTPException(status_code=422, detail=f"产品 {index}：{field.label}选项无效")
        normalized_payload.append(product_data)
    db.execute(delete(Product).where(Product.application_id == application.id))
    products = [Product(application_id=application.id, product_data=item) for item in normalized_payload]
    db.add_all(products)
    db.commit()
    return [ProductData(id=item.id, product_data=item.product_data) for item in products]
