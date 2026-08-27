from __future__ import annotations

import os


class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")
    TESTING = False
    DEFAULT_PAGE_SIZE = 20
    MAX_PAGE_SIZE = 100


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite+pysqlite:///:memory:"
