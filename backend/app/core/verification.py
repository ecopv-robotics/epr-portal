import json
import logging
from urllib.request import Request, urlopen

from app.core.config import get_settings
from app.core.email import send_email

logger = logging.getLogger(__name__)


def send_verification_code(channel: str, target: str, code: str) -> bool:
    """Deliver a registration code through the configured email or SMS channel."""
    settings = get_settings()
    if channel == "email":
        return send_email(
            [target],
            "[EPR Portal] 注册验证码",
            f"您的注册验证码是：{code}\n\n验证码 {settings.verification_code_expire_minutes} 分钟内有效，请勿转发给他人。",
        )

    if not settings.sms_webhook_url:
        logger.info("SMS webhook is not configured; skipped verification SMS to %s", target)
        return False

    body = json.dumps({
        "phone": target,
        "code": code,
        "purpose": "register",
        "expires_in_minutes": settings.verification_code_expire_minutes,
    }).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if settings.sms_webhook_token:
        headers["Authorization"] = f"Bearer {settings.sms_webhook_token}"
    try:
        request = Request(settings.sms_webhook_url, data=body, headers=headers, method="POST")
        with urlopen(request, timeout=15) as response:
            return 200 <= response.status < 300
    except Exception:
        logger.exception("Failed to send verification SMS to %s", target)
        return False
