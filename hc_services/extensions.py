from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, scoped_session, sessionmaker


class Base(DeclarativeBase):
    pass


SessionLocal = scoped_session(sessionmaker(autoflush=False, expire_on_commit=False))
engine = None


def init_db(app):
    global engine
    engine = create_engine(app.config["SQLALCHEMY_DATABASE_URI"], future=True)
    SessionLocal.configure(bind=engine)
    Base.metadata.create_all(bind=engine)


def shutdown_session(exception=None):
    SessionLocal.remove()
