import json
import os
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Text, DateTime, ForeignKey, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session
from backend.models.schemas import FinalReport

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./storycoach.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


class SessionRecord(Base):
    __tablename__ = "sessions"

    id = Column(String, primary_key=True)
    venue = Column(String, nullable=True, default="generic_academic")
    doc_type = Column(String)
    audience_type = Column(String)
    goal_type = Column(String)
    raw_text = Column(Text)
    report_json = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    prior_session_id = Column(String, ForeignKey("sessions.id"), nullable=True)


def init_db():
    Base.metadata.create_all(bind=engine)
    _migrate_sessions_table()


def _migrate_sessions_table():
    inspector = inspect(engine)
    if "sessions" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("sessions")}
    with engine.begin() as connection:
        if "venue" not in columns:
            connection.execute(
                text("ALTER TABLE sessions ADD COLUMN venue VARCHAR DEFAULT 'generic_academic'")
            )


def save_session(
    report: FinalReport,
    doc_type: str,
    audience_type: str,
    goal_type: str,
    raw_text: str,
    venue: str = "generic_academic",
    prior_session_id: str | None = None,
):
    db: Session = SessionLocal()
    try:
        record = SessionRecord(
            id=report.session_id,
            venue=venue,
            doc_type=doc_type,
            audience_type=audience_type,
            goal_type=goal_type,
            raw_text=raw_text,
            report_json=report.model_dump_json(),
            prior_session_id=prior_session_id,
        )
        db.add(record)
        db.commit()
    finally:
        db.close()


def get_session(session_id: str) -> FinalReport | None:
    db: Session = SessionLocal()
    try:
        record = db.query(SessionRecord).filter(SessionRecord.id == session_id).first()
        if not record:
            return None
        return FinalReport(**json.loads(record.report_json))
    finally:
        db.close()


def get_session_record(session_id: str) -> SessionRecord | None:
    db: Session = SessionLocal()
    try:
        return db.query(SessionRecord).filter(SessionRecord.id == session_id).first()
    finally:
        db.close()
