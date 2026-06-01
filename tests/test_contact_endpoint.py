from unittest.mock import AsyncMock, patch

from models.db_models import ContactSubmission


def test_contact_valid_submission(client, db_session):
    with patch("routers.contact.send_contact_notification", new_callable=AsyncMock):
        resp = client.post("/contact/", json={
            "name": "Alice",
            "email": "alice@example.com",
            "message": "Hello Sashko!",
        })
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

    row = db_session.query(ContactSubmission).first()
    assert row is not None
    assert row.name == "Alice"


def test_contact_missing_fields(client):
    resp = client.post("/contact/", json={"name": "Bob"})
    assert resp.status_code == 422


def test_contact_invalid_email(client):
    resp = client.post("/contact/", json={
        "name": "Eve",
        "email": "not-an-email",
        "message": "Hi",
    })
    assert resp.status_code == 422


def test_contact_strips_html(client, db_session):
    with patch("routers.contact.send_contact_notification", new_callable=AsyncMock):
        resp = client.post("/contact/", json={
            "name": "<b>Hacker</b>",
            "email": "h@test.com",
            "message": "<script>alert(1)</script>Real message",
        })
    assert resp.status_code == 200
    row = db_session.query(ContactSubmission).first()
    assert "<" not in row.name
    assert "<script>" not in row.message

