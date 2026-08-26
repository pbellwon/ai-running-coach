from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
)
from .database import Base


class WorkoutDB(Base):
    __tablename__ = "workouts"

    id = Column(Integer, primary_key=True, index=True)

    source_file = Column(String, unique=True, index=True)
    start_time = Column(DateTime, index=True)

    sport = Column(String)

    distance_km = Column(Float)
    duration_sec = Column(Float)

    avg_hr = Column(Float)
    max_hr = Column(Float)

    avg_pace_sec_per_km = Column(Float)

    records_count = Column(Integer)
    laps_count = Column(Integer)

    activity_name = Column(String)
    description = Column(Text)

    external_type = Column(String)
    source_platform = Column(String)

    training_load = Column(Float)
    rpe = Column(Float)
    race = Column(Boolean)

    interval_summary = Column(Text)

    declared_workout_type = Column(String)

    declared_session_role = Column(String)


class DailyAthleteStateDB(Base):
    __tablename__ = "daily_athlete_states"

    id = Column(Integer, primary_key=True, index=True)

    date = Column(DateTime, unique=True, index=True)

    resting_hr = Column(Float)
    hrv = Column(Float)
    hrv_sdnn = Column(Float)

    sleep_sec = Column(Float)
    sleep_score = Column(Float)
    sleep_quality = Column(Float)
    avg_sleeping_hr = Column(Float)

    ctl = Column(Float)
    atl = Column(Float)
    ramp_rate = Column(Float)

    weight_kg = Column(Float)
    vo2max = Column(Float)
    steps = Column(Integer)

    soreness = Column(Float)
    fatigue = Column(Float)
    stress = Column(Float)
    mood = Column(Float)
    motivation = Column(Float)
    readiness = Column(Float)

    spo2 = Column(Float)


class SyncStateDB(Base):
    __tablename__ = "sync_state"

    id = Column(Integer, primary_key=True, index=True)

    sync_name = Column(
        String,
        unique=True,
        nullable=False,
        index=True,
    )

    last_success_at = Column(
        DateTime,
        nullable=False,
    )


class LapDB(Base):
    __tablename__ = "laps"

    id = Column(Integer, primary_key=True)

    workout_file = Column(String, index=True)

    lap_number = Column(Integer)

    distance_m = Column(Float)

    elapsed_time_sec = Column(Float)

    avg_hr = Column(Float)

    max_hr = Column(Float)


class RecordDB(Base):
    __tablename__ = "records"

    id = Column(Integer, primary_key=True)

    workout_file = Column(String, index=True)

    timestamp = Column(DateTime)

    latitude = Column(Float)

    longitude = Column(Float)

    altitude = Column(Float)

    heart_rate = Column(Float)

    cadence = Column(Float)

    speed = Column(Float)