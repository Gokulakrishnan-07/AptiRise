from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["app"] == "AptiRise"


def test_landing_page():
    response = client.get("/")
    assert response.status_code == 200
    assert "AptiRise" in response.text
    assert "Master Aptitude" in response.text


def test_login_page_renders():
    response = client.get("/login")
    assert response.status_code == 200
    assert "Sign in to AptiRise" in response.text


def test_register_and_login_flow():
    import uuid
    uid = uuid.uuid4().hex[:6]
    test_user = f"tester_{uid}"
    test_email = f"test_{uid}@example.com"

    # Register
    reg_resp = client.post("/api/auth/register", json={
        "username": test_user,
        "email": test_email,
        "password": "Password123!",
        "full_name": "Test Runner"
    })
    assert reg_resp.status_code == 200
    reg_data = reg_resp.json()
    assert "access_token" in reg_data
    token = reg_data["access_token"]

    # Login
    login_resp = client.post("/api/auth/login", json={
        "email": test_email,
        "password": "Password123!"
    })
    assert login_resp.status_code == 200
    login_data = login_resp.json()
    assert login_data["user"]["email"] == test_email

    # Access current user profile
    headers = {"Authorization": f"Bearer {token}"}
    me_resp = client.get("/api/auth/me", headers=headers)
    assert me_resp.status_code == 200
    assert me_resp.json()["username"] == test_user
