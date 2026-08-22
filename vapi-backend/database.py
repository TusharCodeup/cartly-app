import datetime as dt
import re

from sqlalchemy import Boolean, Column, DateTime, Float, Index, Integer, String, create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

DATABASE_URL = "sqlite:///./cartly_shopping_db.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def _normalize(raw: str) -> str:
    """Same normalization backend.py uses for matching -- kept here too so
    seeded rows are consistent with anything added later at runtime."""
    s = re.sub(r"\s+", " ", raw.strip().lower())
    if len(s) > 3 and s.endswith("s") and not s.endswith("ss"):
        s = s[:-1]
    return s


class ShoppingItem(Base):
    __tablename__ = "shopping_items"

    id = Column(Integer, primary_key=True, index=True)

    # NEW: scopes each row to one caller/session (normally VAPI's call id).
    # Without this, every caller reads and writes the same global list.
    session_id = Column(String, index=True, nullable=False, default="default")

    name = Column(String, index=True, nullable=False)

    # NEW: lowercased/singularized match key. backend.py matches on this
    # (not on `name`) so "add almond milk" can't get merged into an
    # existing "milk" row, and "remove apple" can't accidentally delete
    # "pineapple" too.
    normalized_name = Column(String, index=True, nullable=False)

    quantity = Column(Float, default=1.0)
    unit = Column(String, default="", nullable=True)
    category = Column(String, default="Other")
    max_price = Column(Float, nullable=True)
    checked = Column(Boolean, default=False)
    canceled = Column(Boolean, default=False)
    created_at = Column(DateTime, default=dt.datetime.utcnow)

    # NEW: updated on every edit; used for general auditing.
    updated_at = Column(DateTime, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow)
    # NEW: when an item was removed. The replenishment engine measures
    # "days since removed" from this, not from created_at.
    canceled_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_session_active", "session_id", "canceled"),
        Index("ix_session_normname", "session_id", "normalized_name"),
    )


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    # Seed initial items if database table is completely empty
    db = SessionLocal()
    try:
        count = db.query(ShoppingItem).count()
        if count == 0:
            sample_items = [
                ShoppingItem(name="Whole Milk", quantity=2.0, unit="bottles", category="Dairy", max_price=3.79),
                ShoppingItem(name="Sourdough Loaf", quantity=1.0, unit="loaf", category="Bakery", max_price=4.99),
                ShoppingItem(name="Organic Strawberries", quantity=1.0, unit="1 lb box", category="Produce", max_price=4.49),
                ShoppingItem(name="Free-Range Chicken Breast", quantity=1.5, unit="lb", category="Meat", max_price=9.99),
            ]
            for item in sample_items:
                item.session_id = "default"
                item.normalized_name = _normalize(item.name)
            db.add_all(sample_items)
            db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
    print("Cartly Shopping Database initialized and seeded successfully.")