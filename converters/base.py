from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ConvertResult:
    ok: bool
    output_path: Path | None = None
    warnings: list[str] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


class BaseConverter:
    name = "base"

    def convert(self, input_path: Path, output_path: Path, options: dict[str, Any] | None = None) -> ConvertResult:
        raise NotImplementedError
