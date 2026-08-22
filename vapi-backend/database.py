import datetime as dt
import re

from sqlalchemy import Boolean, Column, DateTime, Float, Index, Integer, String, create_engine, text
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
    
    # Automatic column migration for existing SQLite databases
    try:
        with engine.connect() as conn:
            result = conn.execute(text("PRAGMA table_info(shopping_items)")).fetchall()
            col_names = {row[1] for row in result}
            
            if "session_id" not in col_names:
                conn.execute(text("ALTER TABLE shopping_items ADD COLUMN session_id VARCHAR DEFAULT 'default'"))
            if "normalized_name" not in col_names:
                conn.execute(text("ALTER TABLE shopping_items ADD COLUMN normalized_name VARCHAR DEFAULT ''"))
            if "updated_at" not in col_names:
                conn.execute(text("ALTER TABLE shopping_items ADD COLUMN updated_at DATETIME"))
            if "canceled_at" not in col_names:
                conn.execute(text("ALTER TABLE shopping_items ADD COLUMN canceled_at DATETIME"))
            if "checked" not in col_names:
                conn.execute(text("ALTER TABLE shopping_items ADD COLUMN checked BOOLEAN DEFAULT 0"))
            if "canceled" not in col_names:
                conn.execute(text("ALTER TABLE shopping_items ADD COLUMN canceled BOOLEAN DEFAULT 0"))
            if "max_price" not in col_names:
                conn.execute(text("ALTER TABLE shopping_items ADD COLUMN max_price FLOAT"))
            conn.commit()
    except Exception as e:
        print(f"Migration notice: {e}")


def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
    print("Cartly Shopping Database initialized and seeded successfully.")