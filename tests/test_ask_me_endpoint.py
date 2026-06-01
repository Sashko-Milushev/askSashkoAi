from models.db_models import UnansweredQuestion


def test_ask_me_saves_question(client, db_session):
    resp = client.post("/contact/ask-me", json={
        "question": "What is your favourite book?",
        "email": "reader@test.com",
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

    row = db_session.query(UnansweredQuestion).first()
    assert row is not None
    assert row.question == "What is your favourite book?"
    assert row.email == "reader@test.com"
    assert row.resolved is False


def test_ask_me_without_email(client, db_session):
    resp = client.post("/contact/ask-me", json={"question": "Tell me more."})
    assert resp.status_code == 200
    row = db_session.query(UnansweredQuestion).first()
    assert row.email is None


def test_ask_me_empty_question(client):
    resp = client.post("/contact/ask-me", json={"question": "   "})
    assert resp.status_code == 422

