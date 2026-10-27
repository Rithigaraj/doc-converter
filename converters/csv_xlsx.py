from pathlib import Path
from typing import Any

import pandas as pd

from .base import BaseConverter, ConvertResult


class CsvXlsxConverter(BaseConverter):
    name = "csv_xlsx"

    def convert(self, input_path: Path, output_path: Path, options: dict[str, Any] | None = None) -> ConvertResult:
        options = options or {}
        warnings = []
        try:
            src = input_path.suffix.lower()
            if src == ".csv":
                df = pd.read_csv(input_path)
                df.to_excel(output_path, index=False)
            else:  # xlsx/xls
                df = pd.read_excel(input_path)
                df.to_csv(output_path, index=False)
            return ConvertResult(ok=True, output_path=output_path, warnings=warnings, meta={"engine": "pandas"})
        except Exception as e:
            return ConvertResult(ok=False, error=str(e), warnings=warnings)
