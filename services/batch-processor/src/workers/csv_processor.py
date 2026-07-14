"""CSV parsing/validation for batch expense imports."""
from __future__ import annotations

import csv
import io
from datetime import datetime

REQUIRED_COLUMNS = {"merchant", "amount", "date"}
OPTIONAL_COLUMNS = {"category", "currency", "description", "id"}


def parse_expense_csv(content: bytes) -> tuple[list[dict], list[str]]:
    """Parse a CSV of expenses into (valid_rows, row_errors).

    Required columns: merchant, amount (positive number), date (ISO or
    YYYY-MM-DD). Unknown columns are ignored; bad rows are reported with
    their line number, never silently dropped.
    """
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        return [], ["file is not valid UTF-8 text"]

    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        return [], ["file is empty"]

    missing = REQUIRED_COLUMNS - {c.strip().lower() for c in reader.fieldnames}
    if missing:
        return [], [f"missing required column(s): {', '.join(sorted(missing))}"]

    valid: list[dict] = []
    errors: list[str] = []
    for lineno, raw in enumerate(reader, start=2):  # header is line 1
        row = {(k or "").strip().lower(): (v or "").strip() for k, v in raw.items()}
        problems = []

        if not row.get("merchant"):
            problems.append("merchant is empty")

        amount = 0.0
        try:
            amount = float(row.get("amount", ""))
            if amount <= 0:
                problems.append("amount must be positive")
        except ValueError:
            problems.append(f"amount {row.get('amount')!r} is not a number")

        date_val = row.get("date", "")
        parsed_date = None
        for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%m/%d/%Y"):
            try:
                parsed_date = datetime.strptime(date_val[:19], fmt)
                break
            except ValueError:
                continue
        if parsed_date is None:
            problems.append(f"date {date_val!r} is not a recognized format")

        if problems:
            errors.append(f"line {lineno}: {'; '.join(problems)}")
            continue

        valid.append(
            {
                "external_id": row.get("id", ""),
                "merchant": row["merchant"],
                "amount": amount,
                "date": parsed_date.date().isoformat(),
                "category": row.get("category", ""),
                "currency": (row.get("currency") or "USD").upper(),
                "description": row.get("description", ""),
            }
        )
    return valid, errors
