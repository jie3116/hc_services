from __future__ import annotations


def test_work_certificate_web_page_renders(client):
    response = client.get("/work-certificates")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Surat Keterangan Kerja" in body
    assert 'id="create-request-form"' in body
    assert 'id="request-list"' in body
    assert 'id="app-alert"' in body
    assert "/static/work_certificates/styles.css" in body
    assert "/static/work_certificates/app.js" in body


def test_work_certificate_static_assets_are_available(client):
    css_response = client.get("/static/work_certificates/styles.css")
    js_response = client.get("/static/work_certificates/app.js")

    assert css_response.status_code == 200
    assert js_response.status_code == 200
    assert "empty-state" in css_response.get_data(as_text=True)
    assert "fetch" in js_response.get_data(as_text=True)
