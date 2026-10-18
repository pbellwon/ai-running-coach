from __future__ import annotations

from sqlalchemy import inspect, text

from app.db.database import engine


TABLE_NAME = "adaptation_decision_records"


def main() -> None:
    inspector = inspect(engine)

    if TABLE_NAME in inspector.get_table_names():
        print(
            f"Table {TABLE_NAME} already exists."
        )
        return

    statement = """
    CREATE TABLE adaptation_decision_records (
        id SERIAL PRIMARY KEY,
        target_date VARCHAR NOT NULL,
        original_workout_type VARCHAR NOT NULL,
        proposed_workout_type VARCHAR NULL,
        proposal_decision VARCHAR NOT NULL,
        athlete_response VARCHAR NOT NULL,
        created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL
    )
    """

    index_statement = """
    CREATE INDEX ix_adaptation_decision_records_target_date
    ON adaptation_decision_records (target_date)
    """

    with engine.begin() as connection:
        connection.execute(
            text(statement)
        )

        connection.execute(
            text(index_statement)
        )

    print(
        f"Created table {TABLE_NAME}."
    )


if __name__ == "__main__":
    main()