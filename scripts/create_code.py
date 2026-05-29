#!/usr/bin/env python3
"""
Create an access code and add it to the database.

Usage:
  python scripts/create_code.py <label> [--admin]
  python scripts/create_code.py --list              # list all codes
"""
import argparse
import secrets
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.database import SessionLocal, AccessCode

def make_code() -> str:
    return secrets.token_urlsafe(6)


def create_code(db, label: str, is_admin: bool = False) -> AccessCode:
    code = make_code()
    row = AccessCode(code=code, label=label, is_admin=is_admin)
    db.add(row)
    db.commit()
    print(f"Created:  code={code}  label={label}  admin={is_admin}")
    return row


def list_codes(db):
    rows = db.query(AccessCode).order_by(AccessCode.label).all()
    if not rows:
        print("No access codes in database.")
        return
    print(f"{'CODE':<12}  {'LABEL':<20}  {'ADMIN':<6}  {'GEN TODAY':<10}  LAST DATE")
    print("-" * 65)
    for r in rows:
        print(f"{r.code:<12}  {r.label:<20}  {str(r.is_admin):<6}  {r.generations_today:<10}  {r.last_generation_date or '-'}")


def main():
    parser = argparse.ArgumentParser(description="Manage TaleSnap access codes")
    parser.add_argument("label", nargs="?", help="Name/label for the new code")
    parser.add_argument("--admin", action="store_true", help="Mark the new code as admin")
    parser.add_argument("--list", action="store_true", help="List all access codes")
    args = parser.parse_args()

    os.makedirs("data", exist_ok=True)
    db = SessionLocal()

    try:
        if args.list:
            list_codes(db)
        elif args.label:
            create_code(db, args.label, is_admin=args.admin)
        else:
            parser.print_help()
    finally:
        db.close()


if __name__ == "__main__":
    main()
