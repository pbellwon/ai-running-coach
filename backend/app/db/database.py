import os

from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import declarative_base, sessionmaker


DATABASE_URL = os.getenv(
    "DATABASE_URL"
)


if DATABASE_URL:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
    )

elif os.getenv("INSTANCE_UNIX_SOCKET"):
    database_url = URL.create(
        drivername="postgresql+psycopg",
        username=os.environ["DB_USER"],
        password=os.environ["DB_PASS"],
        database=os.environ["DB_NAME"],
        query={
            "host": os.environ["INSTANCE_UNIX_SOCKET"],
        },
    )

    engine = create_engine(
        database_url,
        pool_pre_ping=True,
    )

else:
    engine = create_engine(
        "sqlite:///./pace_mind.db",
        connect_args={
            "check_same_thread": False,
        },
        pool_pre_ping=True,
    )


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


Base = declarative_base()