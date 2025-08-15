from __future__ import annotations

from pathlib import Path


class InputFileError(ValueError):
    def __init__(self, message: str, file: Path):
        message = f"{file.relative_to(Path.cwd())}: Error: {message}"
        super().__init__(message)
