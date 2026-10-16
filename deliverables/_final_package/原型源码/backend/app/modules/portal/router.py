from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user
from app.catalog import EUROPEAN_COUNTRIES
from app.models import Application, ApplicationStatus, CartItem, PurchaseOrder, PurchaseOrderStatus, ServiceTemplate, User
from app.portal_catalog import PORTAL_COUNTRIES, PORTAL_SERVICE_BY_ID, PORTAL_SERVICES
from app.schemas import (
    CartCheckout, CartItemCreate, CartItemOut, CatalogServiceOut, DashboardTodoOut, ManagerOut,
    PortalDashboardOut, PortalMessageOut, PurchaseOrderCreate, PurchaseOrderOut, PurchaseOrderPay,
    ServiceInstanceOut,
)

router = APIRouter(prefix="/portal", tags=["客户门户"])


def catalog_service(service: dict) -> CatalogServiceOut:
    return CatalogServiceOut(**service)


def cart_item_out(item: CartItem) -> CartItemOut:
    service = PORTAL_SERVICE_BY_ID.get(item.service_id)
    if not service:
        raise HTTPException(status_code=409, detail="购物车中的服务已下架")
    return CartItemOut(id=item.id, service=catalog_service(service), quantity=item.quantity, created_time=item.created_time)


def purchase_order_out(item: PurchaseOrder) -> PurchaseOrderOut:
    service = PORTAL_SERVICE_BY_ID.get(item.service_id)
    if not service:
        raise HTTPException(status_code=409, detail="订单中的服务已下架")
    instances = list(item.applications)
    instance_items = [ServiceInstanceOut(
        id=instance.id,
        application_no=instance.application_no,
        instance_index=instance.instance_index or index,
        company_name=instance.company.company_name if instance.company else None,
        status=instance.status,
        registration_number=instance.registration_number,
        certificate_file=instance.certificate_file,
        invoice_file=instance.invoice_file,
        result_file=instance.result_file,
        service_expiry_date=instance.service_expiry_date,
    ) for index, instance in enumerate(instances, start=1)]
    if item.status != PurchaseOrderStatus.PAID:
        progress = None
    elif instance_items and all(instance.status == ApplicationStatus.COMPLETED for instance in instance_items):
        progress = "COMPLETED"
    elif any(instance.status == ApplicationStatus.REGISTERING for instance in instance_items):
        progress = "REGISTERING"
    elif any(instance.status in (ApplicationStatus.SUBMITTED, ApplicationStatus.REVIEWING) for instance in instance_items):
        progress = "REVIEWING"
    elif any(instance.status == ApplicationStatus.NEED_FIX for instance in instance_items):
        progress = "NEED_FIX"
    else:
        progress = "DRAFT"
    return PurchaseOrderOut(
        id=item.id, order_no=item.order_no, service=catalog_service(service), service_year=item.service_year,
        subject_type=item.subject_type, package_type=item.package_type, quantity=item.quantity,
        unit_price=item.unit_price, batch_no=item.batch_no, standard_amount=item.standard_amount or item.unit_price * item.quantity,
        discount_amount=item.discount_amount or 0, discount_reason=item.discount_reason,
        total_amount=item.total_amount, status=item.status,
        payment_method=item.payment_method, payer_name=item.payer_name, payment_proof=item.payment_proof,
        actual_paid_amount=item.actual_paid_amount, finance_receipt=item.finance_receipt, finance_note=item.finance_note,
        contract_no=item.contract_no, contract_file=item.contract_file, contract_version=item.contract_version,
        application_id=item.application_id, service_instances=instance_items, service_progress=progress,
        created_time=item.created_time, paid_time=item.paid_time,
    )


def activate_paid_order(db: Session, order: PurchaseOrder, user: User) -> None:
    """Create one independent service instance per purchased unit, exactly once."""
    service = PORTAL_SERVICE_BY_ID.get(order.service_id)
    if not service:
        raise HTTPException(status_code=409, detail="订单中的服务已下架")
    country_by_label = {label: value for value, label in EUROPEAN_COUNTRIES}
    service_type_by_product = {"WEEE": "WEEE", "电池法": "Battery", "包装法": "Packaging", "一次性塑料": "SUP"}
    country = country_by_label.get(service["country"])
    service_type = service_type_by_product.get(service["product_type"])
    template_id = db.scalar(select(ServiceTemplate.id).where(
        ServiceTemplate.country == country,
        ServiceTemplate.service_type == service_type,
        ServiceTemplate.status == "ACTIVE",
    ).order_by(ServiceTemplate.version.desc()))
    if not country or not service_type or not template_id:
        raise HTTPException(status_code=422, detail="该商品暂未配置递单模板")
    existing = {item.instance_index: item for item in order.applications if item.instance_index}
    for instance_index in range(1, order.quantity + 1):
        if instance_index in existing:
            continue
        application = Application(
            application_no="PENDING", user_id=user.id, template_id=template_id,
            purchase_order_id=order.id, instance_index=instance_index,
            country=country, service_type=service_type, status=ApplicationStatus.DRAFT,
        )
        db.add(application)
        db.flush()
        application.application_no = f"EPR{datetime.now(timezone.utc).year}{application.id:06d}"
        if order.application_id is None:
            order.application_id = application.id
    order.status = PurchaseOrderStatus.PAID
    order.paid_time = order.paid_time or datetime.now(timezone.utc)


@router.get("/catalog", response_model=list[CatalogServiceOut])
def catalog():
    return [catalog_service(item) for item in PORTAL_SERVICES]


@router.get("/catalog/countries", response_model=list[str])
def countries():
    return PORTAL_COUNTRIES


@router.get("/dashboard", response_model=PortalDashboardOut)
def dashboard(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    applications = db.scalars(select(Application).where(Application.user_id == user.id).order_by(Application.created_time.desc())).all()
    todos = [DashboardTodoOut(
        id=f"application-{item.id}", type="MATERIAL", company=item.company.company_name if item.company else "待填写",
        country=item.country, service=item.service_type, service_no=item.application_no,
        created_time=item.created_time, application_id=item.id,
    ) for item in applications if item.status in (ApplicationStatus.DRAFT, ApplicationStatus.NEED_FIX)]
    now = datetime.now(timezone.utc).date()
    renewals = [item for item in applications if item.service_expiry_date and 0 <= (datetime.fromisoformat(item.service_expiry_date).date() - now).days <= 30]
    todos.extend(DashboardTodoOut(
        id=f"renewal-{item.id}", type="RENEWAL", company=item.company.company_name if item.company else "待填写",
        country=item.country, service=item.service_type, service_no=item.application_no,
        created_time=item.created_time, application_id=item.id,
    ) for item in renewals)
    unread = len([item for item in applications if item.status in (ApplicationStatus.NEED_FIX, ApplicationStatus.REGISTERING)])
    return PortalDashboardOut(pending_materials=len(todos) - len(renewals), pending_renewals=len(renewals), unread_messages=unread, todos=todos)


@router.get("/messages", response_model=list[PortalMessageOut])
def messages(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    applications = db.scalars(select(Application).where(Application.user_id == user.id).order_by(Application.created_time.desc()).limit(20)).all()
    results: list[PortalMessageOut] = []
    for item in applications:
        if item.status == ApplicationStatus.NEED_FIX:
            results.append(PortalMessageOut(id=f"fix-{item.id}", title=f"{item.service_type}需要补充资料", description=item.review_note or "请补充缺失资料后重新提交。", message_type="资料提醒", created_time=item.reviewed_time or item.created_time, application_id=item.id))
        elif item.status == ApplicationStatus.REGISTERING:
            results.append(PortalMessageOut(id=f"progress-{item.id}", title=f"{item.service_type}已进入业务办理阶段", description="资料审核已经完成，服务正在办理中。", message_type="进度通知", created_time=item.reviewed_time or item.created_time, application_id=item.id))
        elif item.status == ApplicationStatus.COMPLETED:
            results.append(PortalMessageOut(id=f"complete-{item.id}", title=f"{item.service_type}已完成", description="注册结果已更新，可进入 EPR 注册号页面查看。", message_type="完成通知", created_time=item.reviewed_time or item.created_time, application_id=item.id))
    if not results:
        results.append(PortalMessageOut(id="welcome", title="欢迎使用 EPR FLOW", description="你可以从购买服务开始办理首个 EPR 合规项目。", message_type="平台消息", created_time=datetime.now(timezone.utc) - timedelta(minutes=5)))
    return results


@router.get("/manager", response_model=ManagerOut)
def manager(_: User = Depends(get_current_user)):
    return ManagerOut(name="Norah", role="专属客户经理", phone="18120741686", wechat="18120741686", work_hours="工作日 09:00–18:00", online=True)


@router.get("/cart", response_model=list[CartItemOut])
def list_cart(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return [cart_item_out(item) for item in db.scalars(select(CartItem).where(CartItem.user_id == user.id).order_by(CartItem.created_time.desc())).all()]


@router.post("/cart", response_model=CartItemOut, status_code=status.HTTP_201_CREATED)
def add_cart(payload: CartItemCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if payload.service_id not in PORTAL_SERVICE_BY_ID:
        raise HTTPException(status_code=404, detail="服务不存在或已下架")
    item = db.scalar(select(CartItem).where(CartItem.user_id == user.id, CartItem.service_id == payload.service_id))
    if item:
        return cart_item_out(item)
    item = CartItem(user_id=user.id, service_id=payload.service_id)
    db.add(item)
    db.commit()
    db.refresh(item)
    return cart_item_out(item)


@router.delete("/cart/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_cart(item_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    item = db.scalar(select(CartItem).where(CartItem.id == item_id, CartItem.user_id == user.id))
    if not item:
        raise HTTPException(status_code=404, detail="购物车项目不存在")
    db.delete(item)
    db.commit()


@router.post("/orders", response_model=PurchaseOrderOut, status_code=status.HTTP_201_CREATED)
def create_purchase_order(payload: PurchaseOrderCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    service = PORTAL_SERVICE_BY_ID.get(payload.service_id)
    if not service:
        raise HTTPException(status_code=404, detail="服务不存在或已下架")
    if payload.service_year not in service["service_years"]:
        raise HTTPException(status_code=422, detail="商品属性无效")
    standard_amount = service["price"] * payload.quantity
    order = PurchaseOrder(
        order_no="PENDING", user_id=user.id, service_id=payload.service_id,
        service_year=payload.service_year, subject_type="",
        package_type="", quantity=payload.quantity,
        unit_price=service["price"], standard_amount=standard_amount, discount_amount=0,
        total_amount=standard_amount,
    )
    db.add(order)
    db.flush()
    order.order_no = f"ORD{datetime.now(timezone.utc).year}{order.id:08d}"
    db.commit()
    db.refresh(order)
    return purchase_order_out(order)


@router.post("/cart/checkout", response_model=list[PurchaseOrderOut], status_code=status.HTTP_201_CREATED)
def checkout_cart(payload: CartCheckout, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    cart_ids = [item.cart_item_id for item in payload.items]
    cart_items = db.scalars(select(CartItem).where(CartItem.user_id == user.id, CartItem.id.in_(cart_ids))).all()
    cart_by_id = {item.id: item for item in cart_items}
    if len(cart_by_id) != len(set(cart_ids)):
        raise HTTPException(status_code=404, detail="购物车中存在无效项目")
    orders: list[PurchaseOrder] = []
    for checkout_item in payload.items:
        cart_item = cart_by_id[checkout_item.cart_item_id]
        service = PORTAL_SERVICE_BY_ID.get(cart_item.service_id)
        if not service:
            raise HTTPException(status_code=409, detail="购物车中的服务已下架")
        if checkout_item.service_year not in service["service_years"]:
            raise HTTPException(status_code=422, detail=f"{service['title']}的服务年度无效")
        standard_amount = service["price"] * checkout_item.quantity
        order = PurchaseOrder(
            order_no="PENDING", user_id=user.id, service_id=cart_item.service_id,
            service_year=checkout_item.service_year, subject_type="", package_type="",
            quantity=checkout_item.quantity, unit_price=service["price"],
            standard_amount=standard_amount, discount_amount=0, total_amount=standard_amount,
        )
        db.add(order)
        db.flush()
        order.order_no = f"ORD{datetime.now(timezone.utc).year}{order.id:08d}"
        orders.append(order)
    batch_no = f"BAT{datetime.now(timezone.utc).year}{orders[0].id:08d}"
    for order in orders:
        order.batch_no = batch_no
    for item in cart_items:
        db.delete(item)
    db.commit()
    for order in orders:
        db.refresh(order)
    return [purchase_order_out(order) for order in orders]


@router.get("/orders", response_model=list[PurchaseOrderOut])
def list_purchase_orders(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    items = db.scalars(select(PurchaseOrder).where(PurchaseOrder.user_id == user.id).order_by(PurchaseOrder.created_time.desc())).all()
    return [purchase_order_out(item) for item in items]


@router.get("/orders/{order_id}", response_model=PurchaseOrderOut)
def get_purchase_order(order_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    order = db.scalar(select(PurchaseOrder).where(PurchaseOrder.id == order_id, PurchaseOrder.user_id == user.id))
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    return purchase_order_out(order)


@router.post("/orders/{order_id}/pay", response_model=PurchaseOrderOut)
def pay_purchase_order(order_id: int, payload: PurchaseOrderPay | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    order = db.scalar(select(PurchaseOrder).where(
        PurchaseOrder.id == order_id, PurchaseOrder.user_id == user.id
    ).with_for_update())
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    if order.status == PurchaseOrderStatus.PAID:
        return purchase_order_out(order)
    if order.status in (PurchaseOrderStatus.CANCELLED, PurchaseOrderStatus.PARTIALLY_REFUNDED, PurchaseOrderStatus.REFUNDED):
        raise HTTPException(status_code=409, detail="当前订单状态不能付款")
    payment = payload or PurchaseOrderPay()
    if payment.payment_method != "OFFLINE":
        raise HTTPException(status_code=422, detail="当前仅支持线下对公转账")
    if not payment.payer_name or not payment.payment_proof:
        raise HTTPException(status_code=422, detail="线下对公转账需填写付款账户名称并上传转账凭证")
    order.payment_method = payment.payment_method
    order.payer_name = payment.payer_name
    order.payment_proof = payment.payment_proof
    order.status = PurchaseOrderStatus.PAYMENT_CONFIRMING
    db.commit()
    db.refresh(order)
    return purchase_order_out(order)


@router.post("/orders/{order_id}/cancel", response_model=PurchaseOrderOut)
def cancel_purchase_order(order_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    order = db.scalar(select(PurchaseOrder).where(
        PurchaseOrder.id == order_id, PurchaseOrder.user_id == user.id
    ).with_for_update())
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    if order.status not in (PurchaseOrderStatus.PENDING, PurchaseOrderStatus.PAYMENT_FAILED, PurchaseOrderStatus.PAYMENT_CONFIRMING):
        raise HTTPException(status_code=409, detail="已付款订单不能取消")
    order.status = PurchaseOrderStatus.CANCELLED
    db.commit()
    db.refresh(order)
    return purchase_order_out(order)
