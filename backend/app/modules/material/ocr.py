import base64
import hashlib
import hmac
import json
import mimetypes
from pathlib import Path

from fastapi import HTTPException

from app.core.config import get_settings


DOCUMENT_FIELDS: dict[str, dict[str, str]] = {
    "business_license": {
        "company_name": "公司中文名称",
        "company_type": "公司类型",
        "register_number": "统一社会信用代码 / 注册号",
        "established_date": "公司成立日期",
        "register_address": "注册地址",
    },
    "id_card_front": {
        "name_cn": "姓名",
        "certificate_number": "身份证号码",
        "gender": "性别",
    },
    "passport": {
        "name_cn": "中文姓名",
        "name_en": "英文 / 拼音姓名",
        "certificate_number": "护照号码",
        "gender": "性别",
    },
}


def recognition_token(file_url: str) -> str:
    secret = get_settings().jwt_secret.encode("utf-8")
    return hmac.new(secret, f"ocr:{file_url}".encode("utf-8"), hashlib.sha256).hexdigest()


def stored_file(file_url: str, token: str) -> Path:
    if not hmac.compare_digest(recognition_token(file_url), token):
        raise HTTPException(status_code=403, detail="文件识别凭证无效，请重新上传")
    if not file_url.startswith("/files/") or Path(file_url).name != file_url.removeprefix("/files/"):
        raise HTTPException(status_code=422, detail="只能识别本系统刚上传的文件")
    root = Path(get_settings().storage_path).resolve()
    source = (root / Path(file_url).name).resolve()
    if source.parent != root or not source.is_file():
        raise HTTPException(status_code=404, detail="找不到待识别文件，请重新上传")
    if source.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp", ".pdf"}:
        raise HTTPException(status_code=422, detail="文字识别仅支持 JPG、JPEG、PNG、WEBP 或 PDF")
    return source


def _json_payload(content: str) -> dict:
    content = content.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[1].rsplit("```", 1)[0]
    try:
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail="识别服务返回了无法解析的结果，请重试") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=502, detail="识别服务返回格式不正确，请重试")
    return payload


def recognize_document(source: Path, document_type: str) -> tuple[list[dict], list[str]]:
    fields = DOCUMENT_FIELDS.get(document_type)
    if not fields:
        raise HTTPException(status_code=422, detail="暂不支持该证件类型")
    settings = get_settings()
    if settings.ocr_provider == "local":
        from app.modules.material.local_ocr import recognize_local
        return recognize_local(source, document_type, fields)
    if settings.ocr_provider != "openai":
        raise HTTPException(status_code=503, detail="OCR 服务配置错误")
    if not settings.openai_api_key:
        raise HTTPException(status_code=503, detail="未配置 OPENAI_API_KEY，暂时无法使用智能识别")

    encoded = base64.b64encode(source.read_bytes()).decode("ascii")
    mime = mimetypes.guess_type(source.name)[0] or "application/octet-stream"
    file_part = ({
        "type": "input_file",
        "filename": source.name,
        "file_data": f"data:{mime};base64,{encoded}",
    } if source.suffix.lower() == ".pdf" else {
        "type": "input_image",
        "image_url": f"data:{mime};base64,{encoded}",
        "detail": "high",
    })
    requested = ", ".join(f'{key}（{label}）' for key, label in fields.items())
    try:
        from openai import OpenAI

        response = OpenAI(api_key=settings.openai_api_key).responses.create(
            model=settings.openai_ocr_model,
            store=False,
            input=[{
                "role": "user",
                "content": [file_part, {
                    "type": "input_text",
                    "text": (
                        "你是证照 OCR 数据提取器。只读取图片中清晰可见的文字，不推测、不补全。"
                        f"提取这些字段：{requested}。日期统一为 YYYY-MM-DD；"
                        "gender 只允许 MALE、FEMALE、OTHER 或空字符串。"
                        "只返回 JSON，格式为 {\"fields\": {\"字段名\": "
                        "{\"value\": \"字符串\", \"confidence\": 0到1}}, "
                        "\"warnings\": [\"需要人工注意的问题\"]}。缺失或模糊字段 value 为空，且不要返回其他字段。"
                    ),
                }],
            }],
        )
        payload = _json_payload(response.output_text)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"证件文字识别失败：{exc}") from exc

    raw_fields = payload.get("fields") if isinstance(payload.get("fields"), dict) else {}
    matches: list[dict] = []
    for name, label in fields.items():
        raw = raw_fields.get(name, {})
        if not isinstance(raw, dict):
            raw = {}
        value = str(raw.get("value") or "").strip()[:1000]
        try:
            confidence = min(1.0, max(0.0, float(raw.get("confidence", 0))))
        except (TypeError, ValueError):
            confidence = 0.0
        if value:
            matches.append({"target_field": name, "label": label, "value": value, "confidence": confidence})
    warnings = payload.get("warnings") if isinstance(payload.get("warnings"), list) else []
    return matches, [str(item).strip()[:300] for item in warnings if str(item).strip()][:10]
