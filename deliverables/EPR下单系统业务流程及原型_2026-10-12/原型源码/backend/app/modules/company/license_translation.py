import base64
import json
import mimetypes
from io import BytesIO
from pathlib import Path
from textwrap import wrap

from fastapi import HTTPException

from app.core.config import get_settings
from app.core.storage import storage


FIELDS = [
    ("unified_social_credit_code", "Unified Social Credit Code"),
    ("company_name", "Company Name"),
    ("company_type", "Company Type"),
    ("legal_representative", "Legal Representative"),
    ("registered_capital", "Registered Capital"),
    ("establishment_date", "Date of Establishment"),
    ("business_term", "Business Term"),
    ("registered_address", "Registered Address"),
    ("business_scope", "Business Scope"),
    ("registration_authority", "Registration Authority"),
    ("issue_date", "Issue Date"),
]


def extract_translation(source: Path) -> dict[str, str]:
    settings = get_settings()
    if not settings.openai_api_key:
        raise HTTPException(status_code=503, detail="未配置 OPENAI_API_KEY，暂时无法生成翻译件")
    try:
        from openai import OpenAI

        encoded = base64.b64encode(source.read_bytes()).decode("ascii")
        mime = mimetypes.guess_type(source.name)[0] or "application/octet-stream"
        file_part = ({
            "type": "input_file", "filename": source.name,
            "file_data": f"data:{mime};base64,{encoded}",
        } if source.suffix.lower() == ".pdf" else {
            "type": "input_image", "image_url": f"data:{mime};base64,{encoded}", "detail": "high",
        })
        response = OpenAI(api_key=settings.openai_api_key).responses.create(
            model=settings.openai_translation_model,
            store=False,
            input=[{
                "role": "user",
                "content": [file_part, {
                    "type": "input_text",
                    "text": (
                        "Read this Chinese business license and translate it into professional English. "
                        "Return JSON only, with exactly these string keys: "
                        + ", ".join(key for key, _ in FIELDS)
                        + ". Use an empty string when a field is absent or illegible. Do not guess."
                    ),
                }],
            }],
        )
        content = response.output_text.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0]
        payload = json.loads(content)
        return {key: str(payload.get(key, "")).strip() for key, _ in FIELDS}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"营业执照识别或翻译失败：{exc}") from exc


def _pdf_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def build_translation_pdf(values: dict[str, str]) -> bytes:
    lines = ["BUSINESS LICENSE - ENGLISH TRANSLATION", ""]
    for key, label in FIELDS:
        value = values.get(key) or "Not stated / illegible"
        wrapped = wrap(f"{label}: {value}", width=88, break_long_words=False) or [f"{label}:"]
        lines.extend(wrapped)
        lines.append("")
    lines.extend([
        "NOTICE: This translation was generated with AI assistance from the uploaded original.",
        "Please verify all information against the original document before official use.",
    ])
    commands = ["BT", "/F1 14 Tf", "50 790 Td"]
    for index, line in enumerate(lines):
        if index == 2:
            commands.append("/F1 10 Tf")
        commands.extend([f"({_pdf_escape(line)}) Tj", "0 -15 Td"])
    commands.append("ET")
    stream = "\n".join(commands).encode("latin-1", errors="replace")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    output = BytesIO(); output.write(b"%PDF-1.4\n")
    offsets = [0]
    for number, obj in enumerate(objects, 1):
        offsets.append(output.tell()); output.write(f"{number} 0 obj\n".encode()); output.write(obj); output.write(b"\nendobj\n")
    xref = output.tell(); output.write(f"xref\n0 {len(objects) + 1}\n".encode()); output.write(b"0000000000 65535 f \n")
    for offset in offsets[1:]: output.write(f"{offset:010d} 00000 n \n".encode())
    output.write(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode())
    return output.getvalue()


def generate_translation(source_url: str) -> tuple[str, int]:
    root = Path(get_settings().storage_path).resolve()
    source = (root / Path(source_url).name).resolve()
    if source.parent != root or not source.is_file():
        raise HTTPException(status_code=422, detail="找不到已上传的营业执照文件")
    translated = extract_translation(source)
    return storage.save(BytesIO(build_translation_pdf(translated)), "business-license-translation.pdf")
