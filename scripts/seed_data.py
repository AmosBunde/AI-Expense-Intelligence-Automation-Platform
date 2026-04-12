"""
Seed data script - Populates the database with sample data for development and demos.
Usage: python scripts/seed_data.py
"""
import asyncio
import os
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
import random

# This script assumes the database client is importable
# In production: pip install -e packages/db-client packages/shared-types

SAMPLE_MERCHANTS = [
    ("Starbucks", "meals", 5.75),
    ("Uber", "travel", 24.50),
    ("Amazon Web Services", "software", 450.00),
    ("Office Depot", "office_supplies", 89.99),
    ("Delta Airlines", "travel", 387.00),
    ("Hilton Hotels", "travel", 189.00),
    ("Google Workspace", "software", 12.00),
    ("WeWork", "rent", 500.00),
    ("DoorDash", "meals", 32.50),
    ("Slack", "software", 8.75),
    ("FedEx", "shipping", 45.00),
    ("LinkedIn Premium", "software", 29.99),
    ("Zoom", "software", 14.99),
    ("The Capital Grille", "meals", 125.00),
    ("Marriott", "travel", 245.00),
    ("Staples", "office_supplies", 67.50),
    ("Adobe Creative Cloud", "software", 54.99),
    ("Comcast Business", "utilities", 199.99),
    ("Blue Apron", "meals", 59.94),
    ("Coursera", "training", 49.00),
]

STATUSES = ["pending", "processing", "extracted", "categorized", "approved", "flagged", "rejected"]

def generate_expenses(count: int = 50) -> list[dict]:
    """Generate sample expense records."""
    expenses = []
    org_id = str(uuid.uuid4())
    users = [
        {"id": str(uuid.uuid4()), "name": "Alice Johnson", "role": "employee", "dept": "Engineering"},
        {"id": str(uuid.uuid4()), "name": "Bob Smith", "role": "employee", "dept": "Marketing"},
        {"id": str(uuid.uuid4()), "name": "Carol Davis", "role": "manager", "dept": "Engineering"},
        {"id": str(uuid.uuid4()), "name": "Dave Wilson", "role": "finance", "dept": "Finance"},
        {"id": str(uuid.uuid4()), "name": "Eve Chen", "role": "employee", "dept": "Sales"},
    ]

    for i in range(count):
        merchant, category, base_amount = random.choice(SAMPLE_MERCHANTS)
        user = random.choice(users)
        amount = round(base_amount * random.uniform(0.5, 2.5), 2)
        days_ago = random.randint(0, 90)
        date = datetime.utcnow() - timedelta(days=days_ago)

        expenses.append({
            "id": str(uuid.uuid4()),
            "user_id": user["id"],
            "user_name": user["name"],
            "department": user["dept"],
            "organization_id": org_id,
            "status": random.choice(STATUSES),
            "document_type": random.choice(["receipt", "invoice", "credit_card"]),
            "merchant_name": merchant,
            "amount": amount,
            "currency": "USD",
            "category": category,
            "category_confidence": round(random.uniform(0.7, 0.99), 2),
            "transaction_date": date.isoformat(),
            "created_at": date.isoformat(),
        })

    return expenses


def main():
    print("=" * 60)
    print("AI Expense Intelligence Platform - Seed Data")
    print("=" * 60)

    expenses = generate_expenses(50)

    print(f"\nGenerated {len(expenses)} sample expenses")
    print(f"Organization ID: {expenses[0]['organization_id']}")

    # Summary
    categories = {}
    statuses = {}
    total = 0
    for exp in expenses:
        cat = exp["category"]
        st = exp["status"]
        categories[cat] = categories.get(cat, 0) + exp["amount"]
        statuses[st] = statuses.get(st, 0) + 1
        total += exp["amount"]

    print(f"\nTotal spend: ${total:,.2f}")
    print("\nBy category:")
    for cat, amt in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"  {cat:25s} ${amt:>10,.2f}")

    print("\nBy status:")
    for st, count in sorted(statuses.items(), key=lambda x: -x[1]):
        print(f"  {st:20s} {count:>3d}")

    print("\nSample users:")
    users_seen = set()
    for exp in expenses:
        uid = exp["user_id"]
        if uid not in users_seen:
            users_seen.add(uid)
            print(f"  {exp['user_name']:20s} ({exp['department']})")

    print("\n" + "=" * 60)
    print("To insert into database, run with DATABASE_URL set:")
    print("  DATABASE_URL=postgresql://... python scripts/seed_data.py --insert")
    print("=" * 60)


if __name__ == "__main__":
    main()
