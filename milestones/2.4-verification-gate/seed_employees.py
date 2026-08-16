"""Skrip seed sekali-jalan: baca employees_deduped.csv (diberikan user,
sumber nirwana-web), insert ke tabel `employees` (Supabase) - Milestone
2.4 Checkpoint 4.

Skrip sekali-pakai (BUKAN bagian runtime permanen src/), mirror pola
seed_role_permissions.py Milestone 2.2. Tabel ini HANYA untuk fixture
test M2.4 - lihat decisions.md Keputusan 2.

Tiap field di-strip() whitespace (CSV sumber py inkonsistensi whitespace,
mis. " Ade Wasita", "Housekeeping "). hire_date TIDAK di-parse/normalisasi
- disimpan str persis dari CSV (satu baris formatnya DD/MM/YYYY, lihat
decisions.md Keputusan 8).

Jalankan dari root repo: uv run python milestones/2.4-verification-gate/seed_employees.py
"""

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlmodel import Session, SQLModel

from src.config.database import get_engine
from src.db.models import EmployeeRow

CSV_PATH = Path(__file__).resolve().parent / "employees_deduped.csv"


def main() -> None:
    engine = get_engine()
    SQLModel.metadata.create_all(engine)

    with CSV_PATH.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    total_rows = 0
    with Session(engine) as session:
        for row in rows:
            session.add(
                EmployeeRow(
                    employee_id=row["employee_id"].strip(),
                    property_id=row["property_id"].strip(),
                    property_name=row["property_name"].strip(),
                    full_name=row["full_name"].strip(),
                    role_title=row["role_title"].strip(),
                    department=row["department"].strip(),
                    access_level=row["access_level"].strip(),
                    hire_date=row["hire_date"].strip(),
                    status=row["status"].strip(),
                )
            )
            total_rows += 1
        session.commit()

    print(f"{total_rows} baris karyawan di-seed ke tabel employees.")


if __name__ == "__main__":
    main()
