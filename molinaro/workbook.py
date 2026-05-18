from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

import duckdb
import pandas as pd


EXCEL_EXTENSIONS = (".xlsx", ".xls", ".xlsm")


@dataclass(slots=True)
class TableMeta:
    table_name: str
    sheet_name: str
    columns: list[str]
    dtypes: dict[str, str]
    rows: int


def clean_name(name: str) -> str:
    normalized = re.sub(r"\W+", "_", name).strip("_").lower()
    return normalized or "sheet"


def quote_identifier(identifier: str) -> str:
    if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", identifier):
        return identifier
    return '"' + identifier.replace('"', '""') + '"'


def normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy()
    for column in normalized.columns:
        if normalized[column].dtype == "object":
            normalized[column] = normalized[column].map(lambda value: None if pd.isna(value) else str(value))
    return normalized


class WorkbookSession:
    def __init__(self, xlsx_path: Path, connection: duckdb.DuckDBPyConnection, tables: list[TableMeta]):
        self.xlsx_path = xlsx_path
        self.connection = connection
        self.tables = tables

    @classmethod
    def load(cls, xlsx_path: Path) -> "WorkbookSession":
        sheets = pd.read_excel(xlsx_path, sheet_name=None)
        connection = duckdb.connect()
        tables: list[TableMeta] = []

        for sheet_name, df in sheets.items():
            table_name = clean_name(sheet_name)
            normalized = normalize_dataframe(df)
            connection.register(table_name, normalized)
            tables.append(
                TableMeta(
                    table_name=table_name,
                    sheet_name=sheet_name,
                    columns=[str(column) for column in normalized.columns],
                    dtypes={str(column): str(normalized.dtypes[column]) for column in normalized.columns},
                    rows=len(normalized),
                )
            )

        return cls(xlsx_path=xlsx_path, connection=connection, tables=tables)

    def close(self) -> None:
        self.connection.close()

    def table_names(self) -> list[str]:
        return [table.table_name for table in self.tables]

    def find_table(self, table_name: str) -> TableMeta | None:
        for table in self.tables:
            if table.table_name == table_name:
                return table
        return None
