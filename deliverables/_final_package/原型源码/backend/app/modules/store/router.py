from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models import Store, User
from app.modules.application.service import ensure_editable, get_owned_application
from app.schemas import StoreData

router = APIRouter(tags=["店铺资料"])


@router.put("/applications/{application_id}/store", response_model=StoreData)
def save_store(
    application_id: int,
    payload: StoreData,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    application = get_owned_application(db, user, application_id)
    ensure_editable(application)
    store = application.store or Store(application_id=application.id)
    db.add(store)
    for field, value in payload.model_dump().items():
        setattr(store, field, value)
    db.commit()
    return StoreData.model_validate(store, from_attributes=True)
