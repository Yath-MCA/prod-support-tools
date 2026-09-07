import pytest
from fastapi.testclient import TestClient

from metadata_harvester.service.config import settings
from metadata_harvester.service.crossref import db
from metadata_harvester.service.crossref.harvester import naive_geo_parser


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test_crossref.db"
    monkeypatch.setattr(settings, "db_path", str(db_path))
    db.init_db()
    return db_path


# ---------------------------------------------------------------------------
# naive_geo_parser
# ---------------------------------------------------------------------------

def test_naive_geo_parser_three_parts():
    assert naive_geo_parser("City, State, Country") == ("City", "State", "Country")


def test_naive_geo_parser_one_part():
    assert naive_geo_parser("Country") == (None, None, "Country")


def test_naive_geo_parser_two_parts():
    assert naive_geo_parser("State, Country") == (None, "State", "Country")


def test_naive_geo_parser_empty_string():
    assert naive_geo_parser("") == (None, None, None)


def test_naive_geo_parser_none():
    assert naive_geo_parser(None) == (None, None, None)


def test_naive_geo_parser_more_than_three_parts_uses_last_three():
    assert naive_geo_parser("Dept, Building, City, State, Country") == ("City", "State", "Country")


# ---------------------------------------------------------------------------
# db.py
# ---------------------------------------------------------------------------

def test_insert_record_dedup(temp_db):
    assert db.insert_record("123 Main St, City, State, Country", "City", "State", "Country", "10.1/doi1") is True
    assert db.insert_record("123 Main St, City, State, Country", "City", "State", "Country", "10.1/doi1") is False

    with db.get_conn() as conn:
        count = conn.execute("SELECT COUNT(*) FROM crossref_location_registry").fetchone()[0]
    assert count == 1


def test_query_locations_filters_by_country(temp_db):
    db.insert_record("City, State, Argentina", "City", "State", "Argentina", "10.1/doi1")
    db.insert_record("City2, State2, Brazil", "City2", "State2", "Brazil", "10.1/doi2")

    results = db.query_locations("Argentina", 50)
    assert len(results) == 1
    assert results[0]["country"] == "Argentina"

    all_results = db.query_locations(None, 50)
    assert len(all_results) == 2


# ---------------------------------------------------------------------------
# app-level smoke tests (combined FastAPI app, no live network)
# ---------------------------------------------------------------------------

def test_crossref_locations_endpoint_returns_200(temp_db):
    from metadata_harvester.service.app import app
    client = TestClient(app)
    response = client.get("/crossref/locations")
    assert response.status_code == 200
    assert response.json() == []


def test_crossref_start_harvest_requires_valid_email(temp_db):
    from metadata_harvester.service.app import app
    client = TestClient(app)
    response = client.post(
        "/crossref/harvest/start",
        json={"crossref_token": "fake-token", "user_agent_email": "not-an-email"},
    )
    assert response.status_code == 422  # pydantic EmailStr validation failure
