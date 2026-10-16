"""Local CPU OCR and conservative label-based matching; no cloud fallback."""
import re
import threading
import unicodedata
from datetime import date
from pathlib import Path

from fastapi import HTTPException

_lock = threading.Lock()
_engine = None
_fallback_engine = None

LABELS = {
    "company_name": ("企业名称", "公司名称", "名称"),
    "company_type": ("主体类型", "类型"),
    "register_number": ("统一社会信用代码", "注册号"),
    "established_date": ("成立日期", "注册日期"),
    "register_address": ("经营场所", "营业场所", "住所", "注册地址"),
    "name_cn": ("姓名",),
    "certificate_number": ("公民身份号码", "公民身份证号码", "身份证号码", "护照号码"),
    "gender": ("性别",),
}
STOPS = ("法定代表人", "注册资本", "经营范围", "营业期限", "登记机关", "签发机关", "民族", "出生", "有效期限", "重要提示", "商事主体", "__SECTION__")
_label_pattern = re.compile("|".join(sorted({x for labels in LABELS.values() for x in labels} | set(STOPS), key=len, reverse=True)))


def reading_lines(result) -> list[tuple[str, float]]:
    if result.txts is None:
        return []
    rows = []
    for box, text, score in zip(result.boxes, result.txts, result.scores):
        x = float(min(point[0] for point in box))
        y = float(sum(point[1] for point in box) / 4)
        height = float(max(point[1] for point in box) - min(point[1] for point in box))
        row = next((row for row in rows if abs(row[0] - y) < min(row[1], height) * 0.5), None)
        if row is None:
            row = [y, height, []]
            rows.append(row)
        right = float(max(point[0] for point in box))
        row[2].append((x, text, float(score), right))
    lines = []
    previous = None
    for row in sorted(rows, key=lambda row: row[0]):
        if previous is not None and row[0] - previous[0] > max(row[1], previous[1]) * 3:
            lines.append(("__SECTION__", 1.0))
        parts = []
        last_right = None
        for x, text, score, right in sorted(row[2]):
            # Separate distant columns, but retain spaced-out Chinese label characters.
            if last_right is not None and x - last_right > row[1] * 6:
                parts.append("__SECTION__")
            parts.append(text)
            last_right = right
        lines.append((" ".join(parts), min(item[2] for item in row[2])))
        previous = row
    return lines


def match_fields(lines: list[tuple[str, float]], fields: dict[str, str]) -> list[dict]:
    # Preserve OCR reading order while joining labels split by spaces or line breaks.
    normalized = [re.sub(r"[ \t\u3000]", "", unicodedata.normalize("NFKC", text)) for text, _ in lines]
    text = "\n".join(normalized)
    spans = []
    offset = 0
    for line, (_, score) in zip(normalized, lines):
        spans.append((offset, offset + len(line), float(score)))
        offset += len(line) + 1
    matches = list(_label_pattern.finditer(text))
    values = {}
    scores = {}
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        value = text[match.end():end].strip("\n:：· ")
        for field, labels in LABELS.items():
            if field in fields and match.group() in labels and field not in values:
                values[field] = value
                scores[field] = min((score for start, stop, score in spans
                                     if stop > match.start() and start < end
                                     and text[start:stop] != '__SECTION__'), default=0.0)
    output = []
    for field, label in fields.items():
        value = values.get(field, "")
        if field == "register_number":
            found = re.search(r"(?<![0-9A-Z])[0-9A-HJ-NPQRTUW-Y]{18}(?![0-9A-Z])", value.upper())
            value = found.group() if found else ""
        elif field == "certificate_number":
            found = re.search(r"(?<!\d)\d{17}[\dXx](?!\d)", value)
            value = found.group().upper() if found else ""
        elif field == "established_date":
            found = re.search(r"(\d{4})[年./-](\d{1,2})[月./-](\d{1,2})", value)
            try:
                value = date(*map(int, found.groups())).isoformat() if found else ""
            except ValueError:
                value = ""
        elif field == "gender":
            value = "MALE" if value.startswith("男") else "FEMALE" if value.startswith("女") else ""
        else:
            value = value.replace("\n", "")
            # Unbounded text usually means a label or document layout was not recognized.
            if len(value) > (200 if field == "register_address" else 80):
                value = ""
            if field == "company_name" and len(value) < 5:
                value = ""
            if field == "register_address" and (len(value) < 6 or not re.search("省|市|县|区|镇|路|街|村", value)):
                value = ""
        if value:
            # Character OCR confidence is not a guarantee of correct field assignment.
            score = scores.get(field, 0.0)
            output.append({"target_field": field, "label": label, "value": value,
                           "confidence": round(max(0, min(score, 1.0)), 3)})
    return output


def recognize_local(source: Path, document_type: str, fields: dict[str, str]) -> tuple[list[dict], list[str]]:
    if document_type == "passport":
        raise HTTPException(status_code=422, detail="本地识别暂支持大陆营业执照和身份证人像面，护照请手动填写")
    try:
        from PIL import Image, ImageOps, ImageFilter
        from rapidocr import RapidOCR, ModelType
    except ImportError as exc:
        raise HTTPException(status_code=503, detail="本地 OCR 依赖未安装，请管理员安装后端 requirements.txt") from exc
    global _engine, _fallback_engine
    try:
        with _lock:
            if _engine is None:
                _engine = RapidOCR(params={
                    "Det.model_type": ModelType.MEDIUM,
                    "Rec.model_type": ModelType.MEDIUM,
                    "Det.limit_side_len": 1280,
                    "Global.max_side_len": 3200,
                })
            if source.suffix.lower() == ".pdf":
                import pypdfium2 as pdfium
                with pdfium.PdfDocument(str(source)) as document:
                    if len(document) != 1:
                        raise HTTPException(status_code=422, detail="请上传单页证件 PDF 或证件图片")
                    with document[0] as page:
                        scale = min(3.0, 3200 / max(page.get_size()))
                        bitmap = page.render(scale=scale)
                        try:
                            image = bitmap.to_pil().convert("RGB")
                        finally:
                            bitmap.close()
            else:
                with Image.open(source) as original:
                    if original.width * original.height > 40_000_000:
                        raise HTTPException(status_code=422, detail="图片分辨率过大，请缩小后上传")
                    image = ImageOps.exif_transpose(original).convert("RGB")
            try:
                image.thumbnail((3200, 3200))
                result = _engine(image)
                matched = match_fields(reading_lines(result), fields)
                warnings = ["本地 OCR 识别结果，请对照原件核对后回填。分数表示文字识别置信度，不代表字段准确率。"]
                if len(matched) < len(fields) or any(item['confidence'] < 0.9 for item in matched):
                    enhanced = ImageOps.autocontrast(ImageOps.grayscale(image)).filter(ImageFilter.UnsharpMask(radius=1, percent=120, threshold=3))
                    try:
                        if _fallback_engine is None:
                            _fallback_engine = RapidOCR()
                        with enhanced.convert('RGB') as retry_image:
                            second = match_fields(reading_lines(_fallback_engine(retry_image)), fields)
                    finally:
                        enhanced.close()
                    by_field = {item['target_field']: item for item in matched}
                    for item in second:
                        previous = by_field.get(item['target_field'])
                        if previous is None:
                            if item['confidence'] >= 0.9:
                                by_field[item['target_field']] = item
                        elif previous['value'] != item['value']:
                            previous['confidence'] = min(previous['confidence'], 0.64)
                            warnings.append(f"{item['label']}两次识别结果不一致，请重点核对或手动填写。")
                    matched = list(by_field.values())
            finally:
                image.close()
        missing = [label for field, label in fields.items() if field not in {item['target_field'] for item in matched}]
        if missing:
            warnings.append('未识别到：' + '、'.join(missing) + '。请上传清晰原件或手动填写。')
        return matched, warnings
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail="本地 OCR 未能完成，请检查图片或本地模型是否已安装") from exc
