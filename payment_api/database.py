import os

from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import declarative_base, sessionmaker

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Credit_Card.settings")
import django

django.setup()

from django.conf import settings

database_settings = settings.DATABASES["default"]
if database_settings["ENGINE"].endswith("sqlite3"):
    database_url = URL.create(
        "sqlite",
        database=str(database_settings["NAME"]),
    )
    engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
    )
else:
    database_url = URL.create(
        "mysql+mysqldb",
        username=database_settings["USER"],
        password=database_settings["PASSWORD"],
        host=database_settings["HOST"],
        port=int(database_settings["PORT"]),
        database=database_settings["NAME"],
    )
    engine = create_engine(database_url, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
