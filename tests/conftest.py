from __future__ import annotations

import pytest

from hc_services import extensions
from hc_services.app import create_app
from hc_services.config import TestingConfig
from hc_services.extensions import Base, SessionLocal


@pytest.fixture()
def app():
    app = create_app(TestingConfig)
    with app.app_context():
        Base.metadata.drop_all(bind=extensions.engine)
        Base.metadata.create_all(bind=extensions.engine)
        yield app
        SessionLocal.remove()


@pytest.fixture()
def client(app):
    return app.test_client()
