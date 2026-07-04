from sqlalchemy import Column, Integer, Float, String, DateTime
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