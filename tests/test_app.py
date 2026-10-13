from datetime import date

import pytest

from app import calculate_bmi, calculate_calories, create_app, is_int, membership_is_active


@pytest.fixture
def client(tmp_path):
    app = create_app(str(tmp_path / "test.db"))
    app.config["TESTING"] = True
    return app.test_client()


@pytest.fixture
def member(client):
    client.post("/clients", json={"name": "Arun", "age": 28, "weight": 80, "program": "FL"})
    return "Arun"


# ---------- pure logic ----------
@pytest.mark.parametrize("program,expected", [("FL", 1760), ("MG", 2800), ("BG", 2080)])
def test_calculate_calories(program, expected):
    assert calculate_calories(80, program) == expected


def test_calculate_calories_rejects_bad_input():
    with pytest.raises(ValueError):
        calculate_calories(80, "XX")
    with pytest.raises(ValueError):
        calculate_calories(0, "FL")


def test_calculate_bmi():
    assert calculate_bmi(70, 175) == 22.9
    with pytest.raises(ValueError):
        calculate_bmi(70, 0)


def test_is_int_rejects_booleans():
    assert is_int(5)
    assert not is_int(True)
    assert not is_int(5.0)


def test_membership_is_active():
    today = date(2026, 1, 1)
    assert membership_is_active("Active", None, today)
    assert membership_is_active("Active", "2026-06-30", today)
    assert not membership_is_active("Active", "2025-12-31", today)
    assert not membership_is_active("Expired", None, today)


# ---------- service endpoints ----------
def test_index_and_health(client):
    assert client.get("/").get_json()["service"] == "ACEest Fitness & Gym"
    assert client.get("/health").get_json() == {"status": "ok"}


def test_list_programs(client):
    assert client.get("/programs").get_json() == {
        "FL": "Fat Loss", "MG": "Muscle Gain", "BG": "Beginner"
    }


def test_get_program(client):
    res = client.get("/programs/mg")
    assert res.status_code == 200
    assert res.get_json()["target_kcal"] == 3200
    assert client.get("/programs/XX").status_code == 404


def test_bmi_endpoint(client):
    assert client.post("/bmi", json={"weight": 70, "height": 175}).get_json() == {"bmi": 22.9}
    assert client.post("/bmi", json={"weight": 70}).status_code == 400


def test_create_client(client):
    res = client.post("/clients", json={"name": "Priya", "weight": 60, "program": "BG"})
    assert res.status_code == 201
    body = res.get_json()
    assert body["calories"] == 1560
    assert body["membership_status"] == "Active"


@pytest.mark.parametrize("payload", [
    {"weight": 60, "program": "BG"},
    {"name": "X", "weight": 60, "program": "ZZ"},
    {"name": "X", "weight": -5, "program": "FL"},
])
def test_create_client_validation(client, payload):
    assert client.post("/clients", json=payload).status_code == 400


def test_duplicate_client(client, member):
    res = client.post("/clients", json={"name": member, "weight": 80, "program": "FL"})
    assert res.status_code == 409


def test_get_and_list_clients(client, member):
    assert client.get(f"/clients/{member}").get_json()["program"] == "FL"
    assert [c["name"] for c in client.get("/clients").get_json()] == [member]
    assert client.get("/clients/Nobody").status_code == 404


def test_delete_client(client, member):
    assert client.delete(f"/clients/{member}").status_code == 204
    assert client.get(f"/clients/{member}").status_code == 404


def test_membership(client, member):
    body = client.get(f"/clients/{member}/membership").get_json()
    assert body["status"] == "Active" and body["active"] is True


def test_progress(client, member):
    client.post(f"/clients/{member}/progress", json={"week": "W1", "adherence": 80})
    client.post(f"/clients/{member}/progress", json={"week": "W2", "adherence": 90})
    body = client.get(f"/clients/{member}/progress").get_json()
    assert len(body["entries"]) == 2
    assert body["average_adherence"] == 85.0


def test_progress_validation(client, member):
    res = client.post(f"/clients/{member}/progress", json={"week": "W1", "adherence": 150})
    assert res.status_code == 400
    assert client.post("/clients/Nobody/progress", json={}).status_code == 404


def test_workouts(client, member):
    res = client.post(f"/clients/{member}/workouts",
                      json={"type": "Strength", "duration_min": 60, "date": "2026-03-01"})
    assert res.status_code == 201
    workouts = client.get(f"/clients/{member}/workouts").get_json()
    assert workouts[0]["workout_type"] == "Strength"


def test_workout_validation(client, member):
    assert client.post(f"/clients/{member}/workouts",
                       json={"type": "Yoga", "duration_min": 30}).status_code == 400
    assert client.post(f"/clients/{member}/workouts",
                       json={"type": "Cardio", "duration_min": 0}).status_code == 400


def test_boolean_values_are_rejected(client, member):
    assert client.post(f"/clients/{member}/progress",
                       json={"week": "W1", "adherence": True}).status_code == 400
    assert client.post(f"/clients/{member}/workouts",
                       json={"type": "Cardio", "duration_min": True}).status_code == 400
