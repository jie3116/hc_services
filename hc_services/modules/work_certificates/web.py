from __future__ import annotations

from flask import Blueprint, render_template

bp = Blueprint("work_certificate_web", __name__)


@bp.get("/work-certificates")
def index():
    return render_template("work_certificates/index.html")
