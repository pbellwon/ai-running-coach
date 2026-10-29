"""Create or upgrade the decision table without changing historical records."""

from sqlalchemy import inspect, text

from app.db.database import engine
from app.db.models import AdaptationDecisionRecordDB


def upgrade(db_engine) -> None:
    table = AdaptationDecisionRecordDB.__table__
    table.create(bind=db_engine, checkfirst=True)

    columns = {column["name"] for column in inspect(db_engine).get_columns(table.name)}
    with db_engine.begin() as connection:
        if "proposal_id" not in columns:
            connection.execute(text(
                "ALTER TABLE adaptation_decision_records "
                "ADD COLUMN proposal_id VARCHAR(64) NULL"
            ))
        connection.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS "
            "ix_adaptation_decision_records_proposal_id "
            "ON adaptation_decision_records (proposal_id)"
        ))


def main() -> None:
    upgrade(engine)
    print("Adaptation decision table is up to date.")


if __name__ == "__main__":
    main()
