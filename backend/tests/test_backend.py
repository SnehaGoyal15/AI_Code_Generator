from __future__ import annotations

import pytest


def register_user(client, name: str, email: str, password: str = "Password123!"):
    response = client.post(
        "/api/auth/register",
        json={"name": name, "email": email, "password": password},
    )
    assert response.status_code == 201, response.text
    return response.json()


def login_user(client, email: str, password: str = "Password123!"):
    response = client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200, response.text
    challenge = response.json()
    otp = challenge.get("debug_otp")
    assert challenge["verification_required"] is True
    assert otp, challenge

    verify_response = client.post(
        "/api/auth/verify-login-otp",
        json={"email": email, "otp": otp},
    )
    assert verify_response.status_code == 200, verify_response.text
    return verify_response.json()


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_health_endpoint_returns_200(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "message" in body
    assert "environment" in body


def test_unsupported_language_returns_400(client):
    response = client.post(
        "/api/generate",
        json={"prompt": "Write a function", "language": "Brainfuck", "code": None},
        headers=auth_headers(register_user(client, "Lang User", "lang@example.com")["access_token"]),
    )
    assert response.status_code == 400
    assert "Unsupported language" in response.json()["detail"]


def test_generate_rejects_empty_prompt(client):
    auth = register_user(client, "Prompt User", "prompt@example.com")
    response = client.post(
        "/api/generate",
        json={"prompt": "   ", "language": "Python", "code": None},
        headers=auth_headers(auth["access_token"]),
    )
    assert response.status_code == 400
    assert "Prompt is required" in response.json()["detail"]


def test_debug_rejects_empty_code(client):
    auth = register_user(client, "Debug User", "debug@example.com")
    response = client.post(
        "/api/debug",
        json={"prompt": "", "language": "Python", "code": "   "},
        headers=auth_headers(auth["access_token"]),
    )
    assert response.status_code == 400
    assert "Code is required" in response.json()["detail"]


def test_history_create_and_fetch_workflow(client):
    auth = register_user(client, "History User", "history@example.com")
    headers = auth_headers(auth["access_token"])

    ai_response = client.post(
        "/api/generate",
        json={"prompt": "Write a hello world program", "language": "Python", "code": None},
        headers=headers,
    )
    assert ai_response.status_code == 201, ai_response.text
    history_id = ai_response.json()["history_id"]

    history_list = client.get("/api/history", headers=headers)
    assert history_list.status_code == 200
    assert len(history_list.json()) == 1
    assert history_list.json()[0]["id"] == history_id

    record = client.get(f"/api/history/{history_id}", headers=headers)
    assert record.status_code == 200
    assert record.json()["prompt"] == "Write a hello world program"

    delete_response = client.delete(f"/api/history/{history_id}", headers=headers)
    assert delete_response.status_code == 204

    after_delete = client.get("/api/history", headers=headers)
    assert after_delete.status_code == 200
    assert after_delete.json() == []


def test_history_access_control_blocks_other_user(client):
    user_a = register_user(client, "User A", "usera@example.com")
    user_b = register_user(client, "User B", "userb@example.com")

    a_headers = auth_headers(user_a["access_token"])
    b_headers = auth_headers(user_b["access_token"])

    create_response = client.post(
        "/api/history",
        json={
            "prompt": "Create a safe helper",
            "language": "Python",
            "action_type": "generate",
            "input_code": None,
            "generated_code": "print('safe')",
            "explanation": "Mock",
            "time_complexity": "O(1)",
            "space_complexity": "O(1)",
            "suggestions": [],
            "quality_breakdown": [],
            "top_improvements": [],
        },
        headers=a_headers,
    )
    assert create_response.status_code == 201, create_response.text
    history_id = create_response.json()["id"]

    other_user_list = client.get("/api/history", headers=b_headers)
    assert other_user_list.status_code == 200
    assert other_user_list.json() == []

    other_user_record = client.get(f"/api/history/{history_id}", headers=b_headers)
    assert other_user_record.status_code == 404

    other_user_delete = client.delete(f"/api/history/{history_id}", headers=b_headers)
    assert other_user_delete.status_code == 404


def test_static_sql_destructive_query_detection(client):
    auth = register_user(client, "SQL User", "sql@example.com")
    response = client.post(
        "/api/debug",
        json={"prompt": "", "language": "SQL", "code": "DELETE FROM users;"},
        headers=auth_headers(auth["access_token"]),
    )
    assert response.status_code == 201, response.text
    body = response.json()
    messages = [item["message"] for item in body["static_checks"]]
    assert any("write/destructive" in message.lower() for message in messages)
    assert any("potentially destructive query" in message.lower() for message in messages)


def test_static_unmatched_brace_detection(client):
    auth = register_user(client, "Brace User", "brace@example.com")
    response = client.post(
        "/api/debug",
        json={"prompt": "", "language": "Java", "code": "public class Demo {"},
        headers=auth_headers(auth["access_token"]),
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert any("unmatched braces" in item["message"].lower() for item in body["static_checks"])


def test_auth_registration_and_login(client):
    register_response = register_user(client, "Auth User", "auth@example.com")
    assert register_response["token_type"] == "bearer"
    assert register_response["user"]["email"] == "auth@example.com"

    login_challenge = client.post(
        "/api/auth/login",
        json={"email": "auth@example.com", "password": "Password123!"},
    )
    assert login_challenge.status_code == 200, login_challenge.text
    challenge_body = login_challenge.json()
    assert challenge_body["verification_required"] is True
    assert challenge_body["debug_otp"]

    login_response = client.post(
        "/api/auth/verify-login-otp",
        json={"email": "auth@example.com", "otp": challenge_body["debug_otp"]},
    )
    assert login_response.status_code == 200, login_response.text
    login_response = login_response.json()
    assert login_response["token_type"] == "bearer"
    assert login_response["user"]["email"] == "auth@example.com"

    me_response = client.get("/api/auth/me", headers=auth_headers(login_response["access_token"]))
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "auth@example.com"


@pytest.mark.parametrize(
    "method,path,payload",
    [
        ("get", "/api/history", None),
        ("post", "/api/generate", {"prompt": "Write code", "language": "Python", "code": None}),
        ("post", "/api/debug", {"prompt": "", "language": "Python", "code": "print('x')"}),
    ],
)
def test_protected_routes_reject_requests_without_token(client, method, path, payload):
    if method == "get":
        response = client.request("GET", path)
    else:
        response = client.request(method.upper(), path, json=payload)
    assert response.status_code == 401
    assert "Authentication required" in response.json()["detail"]
