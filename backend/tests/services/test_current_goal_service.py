from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.database import Base
from app.services.current_goal_service import CurrentGoalService


def test_missing_confirmed_goal_has_no_hardcoded_race():
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)
    goal = CurrentGoalService(sessionmaker(bind=engine)).get()
    assert goal.goal_type == 'unconfigured'
    assert goal.target_date is None and goal.target_time_sec is None and goal.distance_km is None
    engine.dispose()
