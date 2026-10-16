from pathlib import Path
from typing import BinaryIO, Protocol
from uuid import uuid4

from app.core.config import get_settings


class FileStorage(Protocol):
    def save(self, source: BinaryIO, original_name: str) -> tuple[str, int]: ...


class LocalFileStorage:
    def __init__(self) -> None:
        self.root = Path(get_settings().storage_path).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, source: BinaryIO, original_name: str) -> tuple[str, int]:
        suffix = Path(original_name).suffix.lower()
        filename = f"{uuid4().hex}{suffix}"
        target = self.root / filename
        size = 0
        with target.open("wb") as output:
            while chunk := source.read(1024 * 1024):
                size += len(chunk)
                output.write(chunk)
        return f"/files/{filename}", size

    def delete_url(self, file_url: str) -> None:
        target = (self.root / Path(file_url).name).resolve()
        if target.parent == self.root and target.exists():
            target.unlink()


storage: FileStorage = LocalFileStorage()
