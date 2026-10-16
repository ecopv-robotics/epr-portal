from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.email import send_email
from app.models import Application, ApplicationStatus, Employee

STATUS_LABELS = {
    ApplicationStatus.SUBMITTED: "待审核",
    ApplicationStatus.REVIEWING: "审核中",
    ApplicationStatus.NEED_FIX: "待补件",
    ApplicationStatus.REGISTERING: "注册中",
    ApplicationStatus.COMPLETED: "已完成",
}


def staff_review_recipients(db: Session, application: Application) -> list[str]:
    assigned = getattr(application, "assignment", None)
    if assigned and assigned.employee.active and assigned.employee.user.email:
        return [assigned.employee.user.email]
    employees = db.scalars(select(Employee).where(Employee.active.is_(True))).all()
    return [employee.user.email for employee in employees
            if employee.user.email and "application.review" in (employee.role.permissions or [])]


def notify_staff_new_order(recipients: list[str], application_no: str, is_resubmission: bool) -> None:
    settings = get_settings()
    action = "补件后重新提交" if is_resubmission else "提交了新订单"
    send_email(
        recipients,
        f"[EPR Portal] 待审核订单：{application_no}",
        f"客户已{action}。\n\n订单号：{application_no}\n请登录员工端及时审核：{settings.admin_portal_url}",
    )


def notify_customer_update(
    recipient: str | None,
    application_no: str,
    status: ApplicationStatus,
    note: str | None,
    result_files_updated: bool = False,
) -> None:
    if not recipient:
        return
    settings = get_settings()
    status_label = STATUS_LABELS.get(status, status.value)
    details = [f"订单号：{application_no}", f"当前状态：{status_label}"]
    if note:
        details.append(f"处理说明：{note}")
    if result_files_updated:
        details.append("下证信息或证书/账单/结果附件已更新，请登录客户门户查看。")
    details.append(f"查看订单：{settings.portal_url}")
    send_email([recipient], f"[EPR Portal] 订单更新：{application_no}（{status_label}）", "\n".join(details))
