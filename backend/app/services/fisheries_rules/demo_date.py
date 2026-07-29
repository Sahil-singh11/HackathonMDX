"""Demo date service. The real date is used unless a simulated date is set,
and any simulated date is exposed so the UI can show its badge."""
from __future__ import annotations

from datetime import date

from sqlmodel import Session

from app.models.entities import DemoSetting

SIMULATED_DATE_KEY = "simulated_date"


def get_current_date(session: Session) -> tuple[date, bool]:
    """Returns (date, is_simulated)."""
    row = session.get(DemoSetting, SIMULATED_DATE_KEY)
    if row and row.value:
        return date.fromisoformat(row.value), True
    return date.today(), False


def set_simulated_date(session: Session, value: str | None) -> None:
    row = session.get(DemoSetting, SIMULATED_DATE_KEY)
    if value:
        date.fromisoformat(value)  # validate
        if row:
            row.value = value
        else:
            row = DemoSetting(key=SIMULATED_DATE_KEY, value=value)
        session.add(row)
    elif row:
        session.delete(row)
    session.commit()
