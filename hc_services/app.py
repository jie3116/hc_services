from __future__ import annotations

from flask import Flask, jsonify

from hc_services.config import Config
from hc_services.extensions import init_db, shutdown_session
from hc_services.modules.work_certificates.routes import bp as work_certificates_bp
from hc_services.modules.work_certificates.web import bp as work_certificates_web_bp


def create_app(config_object: type[Config] | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_object or Config)

    init_db(app)
    app.teardown_appcontext(shutdown_session)

    app.register_blueprint(work_certificates_bp, url_prefix="/api/v1/work-certificates")
    app.register_blueprint(work_certificates_web_bp)

    @app.get("/health")
    def health():
        return jsonify({"data": {"status": "ok"}, "meta": {}, "errors": []})

    return app
