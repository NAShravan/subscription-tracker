"""Seed Person B's database with demo subscriptions.

Usage:  python seed_data.py
Only seeds when the subscriptions table is empty (idempotent behaviour).
"""
from datetime import date, timedelta

from database import Base, SessionLocal, engine
from crud import create_subscription, list_subscriptions

DEMO_SUBSCRIPTIONS = [
    # name, category, plan, amount, frequency, days_until_renewal, payment, tags, notes
    ("Netflix", "Streaming", "Premium 4K", 649.0, "monthly", 12, "UPI Autopay", "family,ott,4k", ""),
    ("Spotify", "Music", "Premium Individual", 119.0, "monthly", 5, "Credit Card", "music,student", ""),
    ("Amazon Prime", "Streaming", "Annual", 1499.0, "yearly", 90, "Credit Card", "ott,shopping,delivery", "Includes Prime Video + delivery"),
    ("Adobe Creative Cloud", "Software", "All Apps", 12000.0, "yearly", 200, "Credit Card", "design,work", ""),
    ("Cult.fit Elite", "Fitness", "Quarterly", 1500.0, "quarterly", 25, "UPI Autopay", "health,gym", ""),
    ("iCloud+ 200GB", "Cloud", "200GB", 75.0, "monthly", 18, "Apple ID", "storage,backup", ""),
    ("The Hindu e-Paper", "News", "Digital", 500.0, "quarterly", 60, "UPI", "news,daily-read", ""),
    ("Xbox Game Pass Ultimate", "Gaming", "Monthly", 549.0, "monthly", 8, "UPI Autopay", "games,xcloud", "Cancelled candidate"),
    ("Coursera Plus", "Education", "Annual", 35000.0, "yearly", 150, "Credit Card", "learning,work", ""),
    ("Old Music App", "Music", "Legacy", 99.0, "monthly", 3, "UPI", "legacy", "No longer used - inactive"),
]


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if list_subscriptions(db, limit=1):
            print("Subscriptions already exist; seeding skipped.")
            return
        today = date.today()
        for name, category, plan, amount, frequency, due_in, payment, tags, notes in DEMO_SUBSCRIPTIONS:
            create_subscription(
                db,
                name=name,
                category=category,
                plan=plan,
                amount=amount,
                currency="INR",
                billing_frequency=frequency,
                next_renewal_date=today + timedelta(days=due_in),
                payment_method=payment,
                tags=tags.split(","),
                active=(name != "Old Music App"),
                notes=notes,
            )
        print(f"Seeded {len(DEMO_SUBSCRIPTIONS)} demo subscriptions.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
