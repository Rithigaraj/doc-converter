from pathlib import Path
from typing import Any
import pandas as pd
import openpyxl

from .base import BaseConverter, ConvertResult


class CsvXlsxConverter(BaseConverter):
    name = "csv_xlsx"

    def convert(self, input_path: Path, output_path: Path, options: dict[str, Any] | None = None) -> ConvertResult:
        options = options or {}
        warnings: list[str] = []
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            src = input_path.suffix.lower()
            dst = output_path.suffix.lower()

            if src == ".csv" and dst in {".xlsx", ".xls"}:
                df = pd.read_csv(input_path)
                df.to_excel(output_path, index=False)
            elif src in {".xlsx", ".xls"} and dst == ".csv":
                df = pd.read_excel(input_path)
                df.to_csv(output_path, index=False)
            elif src == ".txt" and dst in {".xlsx", ".xls"}:
                # Tab-delimited or line-based text to Excel
                lines = input_path.read_text(encoding="utf-8", errors="ignore").splitlines()
                wb = openpyxl.Workbook()
                ws = wb.active
                ws.title = "Text Data"
                for r_idx, line in enumerate(lines, 1):
                    cols = line.split("\t") if "\t" in line else (line.split(",") if "," in line else [line])
                    for c_idx, val in enumerate(cols, 1):
                        ws.cell(row=r_idx, column=c_idx, value=val.strip())
                wb.save(str(output_path))
                warnings.append("Text lines parsed and mapped into spreadsheet columns.")
            else:
                df = pd.read_csv(input_path, sep=None, engine='python')
                if dst in {".xlsx", ".xls"}:
                    df.to_excel(output_path, index=False)
                else:
                    df.to_csv(output_path, index=False)

            return ConvertResult(ok=True, output_path=output_path, warnings=warnings, meta={"engine": "pandas+openpyxl"})
        except Exception as e:
            return ConvertResult(ok=False, error=str(e), warnings=warnings)
