from sqlalchemy import create_engine, inspect, text

from app.scripts.add_adaptation_decision_records_table import upgrade


def test_migration_preserves_legacy_records_and_is_repeatable():
    engine = create_engine("sqlite://")
    with engine.begin() as db:
        db.execute(text('''CREATE TABLE adaptation_decision_records (
            id INTEGER PRIMARY KEY,
            target_date VARCHAR NOT NULL,
            original_workout_type VARCHAR NOT NULL,
            proposed_workout_type VARCHAR,
            proposal_decision VARCHAR NOT NULL,
            athlete_response VARCHAR NOT NULL,
            created_at TIMESTAMP NOT NULL
        )'''))
        db.execute(text('''INSERT INTO adaptation_decision_records VALUES
            (1, '2026-10-29', 'threshold', 'easy_run', 'replace_with_easy',
             'accepted', '2026-10-29 10:00:00'),
            (2, '2026-10-29', 'threshold', 'easy_run', 'replace_with_easy',
             'rejected', '2026-10-29 11:00:00')'''))
    upgrade(engine)
    upgrade(engine)
    with engine.connect() as db:
        rows = db.execute(text(
            "SELECT id, athlete_response, proposal_id FROM adaptation_decision_records ORDER BY id"
        )).all()
    assert rows == [(1, "accepted", None), (2, "rejected", None)]
    indexes = inspect(engine).get_indexes("adaptation_decision_records")
    assert any(index["column_names"] == ["proposal_id"] and index["unique"] for index in indexes)


def test_migration_creates_fresh_table():
    engine = create_engine("sqlite://")
    upgrade(engine)
    upgrade(engine)
    assert "proposal_id" in {
        column["name"] for column in inspect(engine).get_columns("adaptation_decision_records")
    }
