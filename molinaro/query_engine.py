from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from molinaro.workbook import WorkbookSession


@dataclass(slots=True)
class QueryResult:
    dataframe: pd.DataFrame
    elapsed_seconds: float
    truncated: bool
    source_sql: str


class QueryEngine:
    def __init__(self, workbook: WorkbookSession):
        self.workbook = workbook

    def run(self, sql: str, row_limit: int = 1000) -> QueryResult:
        start = pd.Timestamp.utcnow()
        dataframe = self.workbook.connection.sql(sql).limit(row_limit + 1).df()
        elapsed = (pd.Timestamp.utcnow() - start).total_seconds()
        truncated = len(dataframe) > row_limit
        if truncated:
            dataframe = dataframe.iloc[:row_limit].copy()
        return QueryResult(
            dataframe=dataframe,
            elapsed_seconds=elapsed,
            truncated=truncated,
            source_sql=sql,
        )

    def export(self, sql: str, output_path: Path) -> Path:
        path = Path(output_path)
        if not path.suffix:
            path = path.with_suffix(".xlsx")

        path.parent.mkdir(parents=True, exist_ok=True)
        dataframe = self.workbook.connection.sql(sql).df()

        if path.suffix.lower() == ".csv":
            dataframe.to_csv(path, index=False)
        elif path.suffix.lower() in {".xlsx", ".xls"}:
            with pd.ExcelWriter(path, engine="openpyxl") as writer:
                dataframe.to_excel(writer, sheet_name="consulta", index=False)
        else:
            raise ValueError("Extension no soportada. Usa .csv, .xlsx o .xls.")

        return path
