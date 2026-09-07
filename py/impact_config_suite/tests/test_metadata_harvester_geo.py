import pytest
import responses

from metadata_harvester.service.config import settings
from metadata_harvester.service.geo import db
from metadata_harvester.service.geo.scheduler import run_harvest
from metadata_harvester.service.geo.sources.base import LocationRecord
from metadata_harvester.service.geo.sources.openalex import OPENALEX_URL, OpenAlexSource
from metadata_harvester.service.geo.sources.ror import ROR_URL, RorSource


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test_geo.db"
    monkeypatch.setattr(settings, "db_path", str(db_path))
    db.init_db()
    return db_path


# ---------------------------------------------------------------------------
# db.py
# ---------------------------------------------------------------------------

def test_insert_record_dedup(temp_db):
    record = LocationRecord(
        source="ror", source_id="ror-1", name="Test Univ",
        city="City", district="State", country="Country",
    )

    assert db.insert_record(record, "T") is True
    assert db.insert_record(record, "T") is False  # duplicate, safe no-op

    with db.get_conn() as conn:
        count = conn.execute("SELECT COUNT(*) FROM geo_location_registry").fetchone()[0]
    assert count == 1


def test_insert_record_requires_country(temp_db):
    record = LocationRecord(
        source="ror", source_id="ror-2", name="No Country",
        city=None, district=None, country=None,
    )
    assert db.insert_record(record, "N") is False


def test_record_exists(temp_db):
    record = LocationRecord(
        source="openalex", source_id="oa-1", name="X",
        city="C", district=None, country="Country",
    )
    assert db.record_exists("openalex", "oa-1") is False
    db.insert_record(record, "X")
    assert db.record_exists("openalex", "oa-1") is True


def test_progress_skip_logic(temp_db):
    assert db.is_letter_completed("ror", "A") is False
    db.mark_progress("ror", "A", fetched_count=5, completed=True)
    assert db.is_letter_completed("ror", "A") is True


def test_get_alpha_counts_reflects_inserts(temp_db):
    record = LocationRecord(
        source="openalex", source_id="oa-2", name="X",
        city="C", district=None, country="Country",
    )
    db.insert_record(record, "X")

    counts = db.get_alpha_counts()

    assert counts["X"] == 1
    assert counts["A"] == 0
    assert set(counts.keys()) == set(db.ALPHABET)


# ---------------------------------------------------------------------------
# scheduler.py
# ---------------------------------------------------------------------------

class FakeSource:
    def __init__(self, name, records_by_letter):
        self.name = name
        self._records_by_letter = records_by_letter
        self.calls = []

    def fetch_letter(self, letter, email):
        self.calls.append(letter)
        return self._records_by_letter.get(letter, [])


def test_run_harvest_covers_every_letter(temp_db):
    records_by_letter = {
        letter: [LocationRecord(
            source="fake", source_id=f"fake-{letter}", name=letter,
            city=None, district=None, country="Testland",
        )]
        for letter in db.ALPHABET
    }
    fake = FakeSource("fake", records_by_letter)

    run_harvest({"fake": fake}, email="test@example.com", num_workers=3)

    for letter in db.ALPHABET:
        assert db.is_letter_completed("fake", letter)
    assert sorted(fake.calls) == sorted(db.ALPHABET)


def test_run_harvest_skips_already_completed_letters(temp_db):
    db.mark_progress("fake", "A", fetched_count=1, completed=True)
    fake = FakeSource("fake", {letter: [] for letter in db.ALPHABET})

    run_harvest({"fake": fake}, email="test@example.com", num_workers=2)

    assert "A" not in fake.calls


def test_run_harvest_prioritizes_least_covered_letter(temp_db):
    for i in range(5):
        db.insert_record(
            LocationRecord(
                source="seed", source_id=f"seed-{i}", name="x",
                city=None, district=None, country="Testland",
            ),
            "A",
        )

    call_order = []

    class OrderTrackingSource:
        name = "fake"

        def fetch_letter(self, letter, email):
            call_order.append(letter)
            return []

    run_harvest({"fake": OrderTrackingSource()}, email="test@example.com", num_workers=1)

    assert call_order.index("B") < call_order.index("A")


# ---------------------------------------------------------------------------
# sources/*.py
# ---------------------------------------------------------------------------

@responses.activate
def test_ror_fetch_letter_parses_records():
    responses.add(
        responses.GET,
        ROR_URL,
        json={
            "items": [
                {
                    "id": "https://ror.org/12345",
                    "names": [{"value": "Test Institute", "types": ["ror_display"]}],
                    "locations": [{
                        "geonames_details": {
                            "name": "Testville",
                            "country_subdivision_name": "Test State",
                            "country_name": "Testland",
                        }
                    }],
                }
            ]
        },
        status=200,
    )
    responses.add(responses.GET, ROR_URL, json={"items": []}, status=200)

    records = RorSource().fetch_letter("T", "test@example.com")

    assert len(records) == 1
    r = records[0]
    assert r.source == "ror"
    assert r.source_id == "https://ror.org/12345"
    assert r.city == "Testville"
    assert r.district == "Test State"
    assert r.country == "Testland"


@responses.activate
def test_ror_fetch_letter_skips_orgs_without_location():
    responses.add(
        responses.GET,
        ROR_URL,
        json={"items": [{"id": "https://ror.org/no-loc", "names": [{"value": "No Loc"}], "locations": []}]},
        status=200,
    )
    responses.add(responses.GET, ROR_URL, json={"items": []}, status=200)

    records = RorSource().fetch_letter("N", "test@example.com")
    assert records == []


@responses.activate
def test_ror_fetch_letter_stops_on_http_error():
    responses.add(responses.GET, ROR_URL, status=500)

    records = RorSource().fetch_letter("E", "test@example.com")
    assert records == []


@responses.activate
def test_openalex_fetch_letter_parses_hint_and_filters_by_prefix():
    responses.add(
        responses.GET,
        OPENALEX_URL,
        json={
            "results": [
                {
                    "id": "https://openalex.org/I1",
                    "display_name": "Testland University",
                    "hint": "Testville, Test State, Testland",
                },
                {
                    "id": "https://openalex.org/I2",
                    "display_name": "Other University",
                    "hint": "Otherplace, Otherland",
                },
            ]
        },
        status=200,
    )

    records = OpenAlexSource().fetch_letter("T", "test@example.com")

    assert len(records) == 1  # "Other University" doesn't start with "T"
    r = records[0]
    assert r.source == "openalex"
    assert r.city == "Testville"
    assert r.district == "Test State"
    assert r.country == "Testland"


@responses.activate
def test_openalex_fetch_letter_skips_missing_country():
    responses.add(
        responses.GET,
        OPENALEX_URL,
        json={"results": [{"id": "https://openalex.org/I3", "display_name": "Testonly", "hint": ""}]},
        status=200,
    )
    records = OpenAlexSource().fetch_letter("T", "test@example.com")
    assert records == []
