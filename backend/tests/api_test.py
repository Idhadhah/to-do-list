from unittest.mock import patch

from tests.conftest import auth_header, signup
# 1. Signup and login

def test_signup_then_login_succeeds(client):
    signup_resp = client.post(
        "/signup", json={"email": "alice@example.com", "password": "correct-horse-1"}
    )
    assert signup_resp.status_code == 201
    assert "access_token" in signup_resp.json()

    login_resp = client.post(
        "/login", json={"email": "alice@example.com", "password": "correct-horse-1"}
    )
    assert login_resp.status_code == 200
    assert "access_token" in login_resp.json()


def test_login_with_wrong_password_is_rejected(client):
    client.post(
        "/signup", json={"email": "bob@example.com", "password": "correct-horse-1"}
    )

    login_resp = client.post(
        "/login", json={"email": "bob@example.com", "password": "wrong-password"}
    )
    assert login_resp.status_code == 401
    assert "access_token" not in login_resp.json()


# 2. Creating tasks requires auth

def test_create_task_while_logged_in_succeeds(client):
    token = signup(client)
    resp = client.post(
        "/tasks", json={"text": "buy milk"}, headers=auth_header(token)
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["text"] == "buy milk"
    assert body["done"] is False


def test_create_task_without_due_date_or_recurrence_uses_defaults(client):
    token = signup(client)
    resp = client.post("/tasks", json={"text": "buy milk"}, headers=auth_header(token))
    assert resp.status_code == 201
    body = resp.json()
    assert body["due_date"] is None
    assert body["recurrence"] == "none"


def test_create_task_with_due_date_and_recurrence(client):
    token = signup(client)
    resp = client.post(
        "/tasks",
        json={
            "text": "pay rent",
            "due_date": "2026-08-01T00:00:00",
            "recurrence": "monthly",
        },
        headers=auth_header(token),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["due_date"] == "2026-08-01T00:00:00"
    assert body["recurrence"] == "monthly"


def test_edit_task_updates_due_date_and_recurrence(client):
    token = signup(client)
    task = client.post(
        "/tasks", json={"text": "water plants"}, headers=auth_header(token)
    ).json()

    resp = client.put(
        f"/tasks/{task['id']}",
        json={"text": "water plants", "due_date": "2026-09-01T00:00:00", "recurrence": "weekly"},
        headers=auth_header(token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["due_date"] == "2026-09-01T00:00:00"
    assert body["recurrence"] == "weekly"


def test_create_task_without_auth_is_rejected(client):
    resp = client.post("/tasks", json={"text": "buy milk"})
    assert resp.status_code == 401


def test_create_task_with_bad_token_is_rejected(client):
    resp = client.post(
        "/tasks",
        json={"text": "buy milk"},
        headers=auth_header("this-is-not-a-real-jwt"),
    )
    assert resp.status_code == 401


# 3. Authorization boundary: users can never touch each other's tasks

def test_user_cannot_view_another_users_tasks_in_list(client):
    token_a = signup(client, "a@example.com")
    token_b = signup(client, "b@example.com")

    client.post("/tasks", json={"text": "A's task"}, headers=auth_header(token_a))

    b_tasks = client.get("/tasks", headers=auth_header(token_b)).json()
    assert b_tasks == []


def test_user_cannot_edit_another_users_task(client):
    token_a = signup(client, "a@example.com")
    token_b = signup(client, "b@example.com")

    b_task = client.post(
        "/tasks", json={"text": "B's private task"}, headers=auth_header(token_b)
    ).json()

    # A tries to PUT directly to B's task id, using A's own valid token.
    resp = client.put(
        f"/tasks/{b_task['id']}",
        json={"text": "hacked by A"},
        headers=auth_header(token_a),
    )
    assert resp.status_code == 404  # looks identical to "no such task"

    # Confirm B's task is untouched.
    b_tasks = client.get("/tasks", headers=auth_header(token_b)).json()
    assert b_tasks == [{"id": b_task["id"],"text": "B's private task","done": False,"due_date": None,"recurrence": "none",}]


def test_user_cannot_delete_another_users_task(client):
    token_a = signup(client, "a@example.com")
    token_b = signup(client, "b@example.com")

    b_task = client.post(
        "/tasks", json={"text": "B's private task"}, headers=auth_header(token_b)
    ).json()

    resp = client.delete(f"/tasks/{b_task['id']}", headers=auth_header(token_a))
    assert resp.status_code == 404

    # It's still there when B looks.
    b_tasks = client.get("/tasks", headers=auth_header(token_b)).json()
    assert len(b_tasks) == 1


def test_user_cannot_toggle_another_users_task(client):
    token_a = signup(client, "a@example.com")
    token_b = signup(client, "b@example.com")

    b_task = client.post(
        "/tasks", json={"text": "B's private task"}, headers=auth_header(token_b)
    ).json()

    resp = client.patch(f"/tasks/{b_task['id']}", headers=auth_header(token_a))
    assert resp.status_code == 404


# 4. Empty task text is rejected

def test_creating_task_with_empty_text_is_rejected(client):
    token = signup(client)
    resp = client.post("/tasks", json={"text": ""}, headers=auth_header(token))
    assert resp.status_code == 422


def test_editing_task_to_empty_text_is_rejected(client):
    token = signup(client)
    task = client.post(
        "/tasks", json={"text": "real task"}, headers=auth_header(token)
    ).json()

    resp = client.put(
        f"/tasks/{task['id']}", json={"text": ""}, headers=auth_header(token)
    )
    assert resp.status_code == 422

# Confirms the summary only includes the logged-in user's own tasks, never another user's.
def test_summary_only_reflects_own_tasks(client):
    token_a = signup(client, "a2@example.com")
    token_b = signup(client, "b2@example.com")

    client.post("/tasks", json={"text": "A's task"}, headers=auth_header(token_a))
    client.post("/tasks", json={"text": "B's task 1"}, headers=auth_header(token_b))
    client.post("/tasks", json={"text": "B's task 2"}, headers=auth_header(token_b))

    with patch("main.summarize_tasks") as mock_summarize:
        mock_summarize.return_value = {"summary": "You have 1 task.", "priority_order": []}
        resp = client.get("/tasks/summary", headers=auth_header(token_a))

    assert resp.status_code == 200
    called_tasks = mock_summarize.call_args[0][0]
    assert len(called_tasks) == 1
    assert called_tasks[0]["text"] == "A's task"


# Confirms an empty task list returns "No tasks yet." without calling Gemini at all.
def test_summary_with_no_tasks_returns_clean_response_without_calling_gemini(client):
    token = signup(client, "empty@example.com")
    with patch("main.summarize_tasks") as mock_summarize:
        resp = client.get("/tasks/summary", headers=auth_header(token))

    assert resp.status_code == 200
    assert resp.json()["summary"] == "No tasks yet."
    mock_summarize.assert_not_called()


# Confirms a Gemini failure returns a clean 502 instead of an unhandled crash.
def test_summary_handles_gemini_failure_gracefully(client):
    token = signup(client, "failtest@example.com")
    client.post("/tasks", json={"text": "some task"}, headers=auth_header(token))

    with patch("main.summarize_tasks", side_effect=ValueError("bad json")):
        resp = client.get("/tasks/summary", headers=auth_header(token))

    assert resp.status_code == 502