from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "deliverables" / "EPR下单系统业务流程及原型_2026-10-12"
OUTPUT = ROOT / "deliverables" / "EPR下单系统业务流程及原型_2026-10-12_交付版.zip"

INCLUDED = (
    SOURCE / "EPR下单系统业务流程与原型确认稿.docx",
    SOURCE / "README.txt",
    SOURCE / "业务流程图",
    SOURCE / "原型截图",
    SOURCE / "原型源码",
    SOURCE / "可运行构建",
)


def should_skip(path: Path) -> bool:
    relative = path.relative_to(SOURCE)
    parts = set(relative.parts)
    return (
        "__pycache__" in parts
        or "node_modules" in parts
        or "storage" in parts
        or path.suffix in {".pyc", ".db"}
        or path.name == ".env"
    )


with ZipFile(OUTPUT, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
    for item in INCLUDED:
        if item.is_file():
            archive.write(item, item.relative_to(SOURCE))
            continue
        for path in sorted(item.rglob("*")):
            if path.is_file() and not should_skip(path):
                archive.write(path, path.relative_to(SOURCE))

print(OUTPUT)
