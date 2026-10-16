"""
API tests for the Healthcare Readmission MVP.

The tests run against the real PostgreSQL database configured in .env,
but nothing they do is kept: every test shares one connection whose
transaction is rolled back afterwards, so PATCH calls never persist.

Expected values are worked out independently (direct SQL or the scoring
rules restated below) rather than by calling the app's own code.

Run from the project root:
    python -m pytest tests -v
"""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import database  # noqa: E402
from main import app  # noqa: E402
from repositories import encounter_repository, intervention_repository  # noqa: E402

EXPECTED_ENCOUNTER_COUNT = 101_766
MISSING_ENCOUNTER_ID = -1

ENCOUNTER_FIELDS = {
    "encounter_id", "patient_nbr", "age", "time_in_hospital",
    "number_inpatient", "number_emergency", "number_outpatient",
    "num_medications", "num_lab_procedures",
    "discharge_disposition_id", "admission_type_id",
    "readmitted", "risk_score", "risk_level",
}
CARE_QUEUE_FIELDS = ENCOUNTER_FIELDS | {"intervention_status", "assigned_to", "notes"}
INTERVENTION_FIELDS = {
    "intervention_id", "encounter_id", "status",
    "assigned_to", "notes", "created_at", "updated_at",
}


# ---------------------------------------------------------------- fixtures

class _SharedConnection:
    """Stands in for get_connection(): hands out the test's connection
    without committing or closing it at the end of a `with` block."""

    def __init__(self, conn):
        self.conn = conn

    def __enter__(self):
        return self.conn

    def __exit__(self, *exc):
        return False


@pytest.fixture
def db(monkeypatch):
    conn = database.get_connection()
    shared = lambda: _SharedConnection(conn)
    monkeypatch.setattr(encounter_repository, "get_connection", shared)
    monkeypatch.setattr(intervention_repository, "get_connection", shared)
    yield conn
    conn.rollback()
    conn.close()


@pytest.fixture
def client(db):
    return TestClient(app)


def query(db, sql, params=()):
    with db.cursor() as cursor:
        cursor.execute(sql, params)
        return cursor.fetchall()


def scalar(db, sql, params=()):
    return query(db, sql, params)[0][0]


@pytest.fixture
def encounter_id(db):
    """An encounter that has no intervention yet."""
    return scalar(db, """
        SELECT e.encounter_id
        FROM patient_encounters e
        LEFT JOIN care_interventions i ON i.encounter_id = e.encounter_id
        WHERE i.encounter_id IS NULL AND e.risk_level = 'HIGH'
        ORDER BY e.risk_score DESC, e.encounter_id
        LIMIT 1
    """)


# The scoring rules, restated from the spec so the stored scores are
# checked against an independent copy rather than against risk_scoring.py.
def expected_risk_score(e):
    return (
        (3 if e["number_inpatient"] >= 3 else 0)
        + (2 if e["number_emergency"] >= 2 else 0)
        + (1 if e["number_outpatient"] >= 3 else 0)
        + (1 if e["time_in_hospital"] >= 7 else 0)
        + (1 if e["num_medications"] >= 20 else 0)
    )


def expected_risk_level(score):
    if score >= 5:
        return "HIGH"
    if score >= 3:
        return "MEDIUM"
    return "LOW"


# ------------------------------------------------------------------ health

def test_health_check(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "application": "Healthcare Readmission MVP",
    }


# -------------------------------------------------------------- encounters

def test_encounters_default_page_is_first_ten_by_id(client, db):
    response = client.get("/encounters")

    assert response.status_code == 200
    body = response.json()
    expected_ids = [row[0] for row in query(
        db, "SELECT encounter_id FROM patient_encounters ORDER BY encounter_id LIMIT 10"
    )]
    assert [e["encounter_id"] for e in body] == expected_ids
    assert all(set(e) == ENCOUNTER_FIELDS for e in body)


def test_encounters_pagination_is_contiguous_without_overlap(client):
    first = client.get("/encounters", params={"limit": 5, "offset": 0}).json()
    second = client.get("/encounters", params={"limit": 5, "offset": 5}).json()
    both = client.get("/encounters", params={"limit": 10, "offset": 0}).json()

    assert len(first) == len(second) == 5
    assert first + second == both


def test_encounters_offset_past_the_end_returns_empty_list(client):
    response = client.get("/encounters", params={"offset": EXPECTED_ENCOUNTER_COUNT})

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.parametrize("level", ["HIGH", "MEDIUM", "LOW"])
def test_encounters_filter_returns_only_that_risk_level(client, level):
    body = client.get("/encounters", params={"risk_level": level, "limit": 100}).json()

    assert len(body) == 100
    assert {e["risk_level"] for e in body} == {level}


@pytest.mark.parametrize("level", ["HIGH", "MEDIUM", "LOW"])
def test_stored_risk_scores_follow_the_scoring_rules(client, level):
    body = client.get("/encounters", params={"risk_level": level, "limit": 100}).json()

    for e in body:
        assert e["risk_score"] == expected_risk_score(e), e["encounter_id"]
        assert e["risk_level"] == expected_risk_level(e["risk_score"]), e["encounter_id"]


@pytest.mark.parametrize("params", [
    {"limit": 0},
    {"limit": 101},
    {"offset": -1},
    {"limit": "ten"},
    {"risk_level": "CRITICAL"},
    {"risk_level": "high"},
])
def test_encounters_rejects_invalid_query_parameters(client, params):
    assert client.get("/encounters", params=params).status_code == 422


def test_get_encounter_by_id_matches_database_row(client, db, encounter_id):
    response = client.get(f"/encounters/{encounter_id}")

    assert response.status_code == 200
    body = response.json()
    columns = sorted(ENCOUNTER_FIELDS)
    row = query(
        db,
        f"SELECT {', '.join(columns)} FROM patient_encounters WHERE encounter_id = %s",
        (encounter_id,),
    )[0]
    assert body == dict(zip(columns, row))


def test_get_encounter_unknown_id_returns_404(client):
    response = client.get(f"/encounters/{MISSING_ENCOUNTER_ID}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Encounter not found"}


def test_get_encounter_non_integer_id_returns_422(client):
    assert client.get("/encounters/abc").status_code == 422


# -------------------------------------------------------------- care queue

def test_care_queue_contains_only_high_and_medium_risk(client):
    body = client.get("/care-queue", params={"limit": 100}).json()

    assert len(body) == 100
    assert {e["risk_level"] for e in body} <= {"HIGH", "MEDIUM"}
    assert all(set(e) == CARE_QUEUE_FIELDS for e in body)


def test_care_queue_is_ordered_by_score_then_encounter_id(client):
    body = client.get("/care-queue", params={"limit": 100}).json()

    keys = [(-e["risk_score"], e["encounter_id"]) for e in body]
    assert keys == sorted(keys)


def test_care_queue_default_limit_is_twenty(client):
    assert len(client.get("/care-queue").json()) == 20


def test_care_queue_pages_are_contiguous(client):
    first = client.get("/care-queue", params={"limit": 20, "offset": 0}).json()
    second = client.get("/care-queue", params={"limit": 20, "offset": 20}).json()
    both = client.get("/care-queue", params={"limit": 40, "offset": 0}).json()

    assert first + second == both


def test_care_queue_size_matches_high_plus_medium_count(client, db):
    expected = scalar(
        db, "SELECT COUNT(*) FROM patient_encounters WHERE risk_level IN ('HIGH', 'MEDIUM')"
    )

    last_page = client.get("/care-queue", params={"limit": 100, "offset": expected - 1}).json()
    past_end = client.get("/care-queue", params={"limit": 100, "offset": expected}).json()

    assert len(last_page) == 1
    assert past_end == []


def test_care_queue_without_intervention_shows_pending_review(client, encounter_id):
    body = client.get("/care-queue/high", params={"limit": 100}).json()

    entry = next(e for e in body if e["encounter_id"] == encounter_id)
    assert entry["intervention_status"] == "PENDING_REVIEW"
    assert entry["assigned_to"] is None
    assert entry["notes"] is None


def test_care_queue_reflects_intervention_updates(client, encounter_id):
    client.patch(f"/interventions/{encounter_id}", json={
        "status": "ASSIGNED", "assigned_to": "Nurse Lee", "notes": "Call within 48h",
    })

    entry = next(e for e in client.get("/care-queue").json() if e["encounter_id"] == encounter_id)
    assert entry["intervention_status"] == "ASSIGNED"
    assert entry["assigned_to"] == "Nurse Lee"
    assert entry["notes"] == "Call within 48h"


def test_high_care_queue_contains_only_high_risk(client):
    body = client.get("/care-queue/high", params={"limit": 100}).json()

    assert len(body) == 100
    assert {e["risk_level"] for e in body} == {"HIGH"}


def test_high_care_queue_is_the_top_of_the_full_queue(client):
    # HIGH scores (>= 5) all outrank MEDIUM scores (3-4), so the HIGH queue
    # must be exactly the head of the combined queue.
    high = client.get("/care-queue/high", params={"limit": 50}).json()
    full = client.get("/care-queue", params={"limit": 50}).json()

    assert high == full


@pytest.mark.parametrize("path", ["/care-queue", "/care-queue/high"])
@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 101}, {"offset": -1}])
def test_care_queue_rejects_invalid_paging(client, path, params):
    assert client.get(path, params=params).status_code == 422


# ----------------------------------------------------------- interventions

def test_first_patch_creates_intervention(client, db, encounter_id):
    response = client.patch(f"/interventions/{encounter_id}", json={
        "status": "ASSIGNED", "assigned_to": "Nurse Lee",
    })

    assert response.status_code == 200
    body = response.json()
    assert set(body) == INTERVENTION_FIELDS
    assert body["encounter_id"] == encounter_id
    assert body["status"] == "ASSIGNED"
    assert body["assigned_to"] == "Nurse Lee"
    assert body["notes"] is None
    assert query(
        db,
        "SELECT status, assigned_to, notes FROM care_interventions WHERE encounter_id = %s",
        (encounter_id,),
    ) == [("ASSIGNED", "Nurse Lee", None)]


def test_patch_without_status_defaults_new_intervention_to_pending_review(client, encounter_id):
    body = client.patch(f"/interventions/{encounter_id}", json={"notes": "Needs review"}).json()

    assert body["status"] == "PENDING_REVIEW"
    assert body["notes"] == "Needs review"


def test_patch_updates_existing_intervention_in_place(client, db, encounter_id):
    created = client.patch(f"/interventions/{encounter_id}", json={"status": "ASSIGNED"}).json()
    updated = client.patch(f"/interventions/{encounter_id}", json={"status": "CONTACTED"}).json()

    assert updated["intervention_id"] == created["intervention_id"]
    assert updated["status"] == "CONTACTED"
    assert updated["created_at"] == created["created_at"]
    assert scalar(
        db, "SELECT COUNT(*) FROM care_interventions WHERE encounter_id = %s", (encounter_id,)
    ) == 1


def test_patch_only_changes_fields_that_were_sent(client, encounter_id):
    client.patch(f"/interventions/{encounter_id}", json={
        "status": "ASSIGNED", "assigned_to": "Nurse Lee", "notes": "Call within 48h",
    })

    body = client.patch(f"/interventions/{encounter_id}", json={"status": "CONTACTED"}).json()

    assert body["status"] == "CONTACTED"
    assert body["assigned_to"] == "Nurse Lee"
    assert body["notes"] == "Call within 48h"


def test_patch_with_explicit_null_clears_optional_field(client, encounter_id):
    client.patch(f"/interventions/{encounter_id}", json={
        "assigned_to": "Nurse Lee", "notes": "Call within 48h",
    })

    body = client.patch(f"/interventions/{encounter_id}", json={"notes": None}).json()

    assert body["notes"] is None
    assert body["assigned_to"] == "Nurse Lee"


@pytest.mark.parametrize("status", [
    "PENDING_REVIEW", "ASSIGNED", "CONTACTED", "FOLLOW_UP_SCHEDULED", "CLOSED",
])
def test_patch_accepts_every_valid_status(client, encounter_id, status):
    response = client.patch(f"/interventions/{encounter_id}", json={"status": status})

    assert response.status_code == 200
    assert response.json()["status"] == status


@pytest.mark.parametrize("payload, detail", [
    ({}, "No fields provided"),
    ({"status": None}, "Status cannot be null"),
])
def test_patch_rejects_empty_or_null_status(client, db, encounter_id, payload, detail):
    response = client.patch(f"/interventions/{encounter_id}", json=payload)

    assert response.status_code == 422
    assert response.json() == {"detail": detail}
    assert scalar(
        db, "SELECT COUNT(*) FROM care_interventions WHERE encounter_id = %s", (encounter_id,)
    ) == 0


@pytest.mark.parametrize("payload", [
    {"status": "DONE"},
    {"status": "assigned"},
    {"priority": "HIGH"},
    {"status": "ASSIGNED", "encounter_id": 1},
])
def test_patch_rejects_unknown_status_or_fields(client, db, encounter_id, payload):
    response = client.patch(f"/interventions/{encounter_id}", json=payload)

    assert response.status_code == 422
    assert scalar(
        db, "SELECT COUNT(*) FROM care_interventions WHERE encounter_id = %s", (encounter_id,)
    ) == 0


def test_patch_unknown_encounter_returns_404_and_saves_nothing(client, db):
    before = scalar(db, "SELECT COUNT(*) FROM care_interventions")

    response = client.patch(f"/interventions/{MISSING_ENCOUNTER_ID}", json={"status": "ASSIGNED"})

    assert response.status_code == 404
    assert response.json() == {"detail": "Encounter not found"}
    assert scalar(db, "SELECT COUNT(*) FROM care_interventions") == before


# -------------------------------------------------------------- operations

def test_all_csv_encounters_were_loaded(client):
    summary = client.get("/operations/summary").json()

    assert summary["total_encounters"] == EXPECTED_ENCOUNTER_COUNT


def test_operations_summary_matches_database(client, db):
    summary = client.get("/operations/summary").json()

    counts = dict(query(db, "SELECT risk_level, COUNT(*) FROM patient_encounters GROUP BY risk_level"))
    assert summary["high_risk"] == counts["HIGH"]
    assert summary["medium_risk"] == counts["MEDIUM"]
    assert summary["low_risk"] == counts["LOW"]
    assert summary["high_risk"] + summary["medium_risk"] + summary["low_risk"] \
        == summary["total_encounters"]


def test_operations_summary_counts_intervention_statuses(client, db):
    ids = [row[0] for row in query(db, """
        SELECT e.encounter_id
        FROM patient_encounters e
        LEFT JOIN care_interventions i ON i.encounter_id = e.encounter_id
        WHERE i.encounter_id IS NULL
        ORDER BY e.encounter_id
        LIMIT 3
    """)]
    before = client.get("/operations/summary").json()["intervention_status_counts"]

    client.patch(f"/interventions/{ids[0]}", json={"status": "ASSIGNED"})
    client.patch(f"/interventions/{ids[1]}", json={"status": "ASSIGNED"})
    client.patch(f"/interventions/{ids[2]}", json={"status": "CLOSED"})

    after = client.get("/operations/summary").json()["intervention_status_counts"]
    assert after.get("ASSIGNED", 0) == before.get("ASSIGNED", 0) + 2
    assert after.get("CLOSED", 0) == before.get("CLOSED", 0) + 1


def test_readmission_analysis_matches_database(client, db):
    body = client.get("/operations/readmission-analysis").json()

    assert [row["risk_level"] for row in body] == ["HIGH", "MEDIUM", "LOW"]

    expected = {
        level: (total, early)
        for level, total, early in query(db, """
            SELECT risk_level, COUNT(*), COUNT(*) FILTER (WHERE readmitted = '<30')
            FROM patient_encounters
            GROUP BY risk_level
        """)
    }
    for row in body:
        total, early = expected[row["risk_level"]]
        assert row["total_encounters"] == total
        assert row["readmitted_within_30_days"] == early
        assert row["early_readmission_rate_pct"] == round(100 * early / total, 2)


def test_readmission_analysis_covers_every_encounter(client):
    body = client.get("/operations/readmission-analysis").json()

    assert sum(row["total_encounters"] for row in body) == EXPECTED_ENCOUNTER_COUNT


def test_management_dashboard_combines_the_other_reports(client):
    dashboard = client.get("/management/dashboard").json()

    assert dashboard["overview"] == client.get("/operations/summary").json()
    assert dashboard["readmission_analysis"] == client.get("/operations/readmission-analysis").json()
    assert dashboard["priority_encounters"] == client.get("/care-queue", params={"limit": 10}).json()
