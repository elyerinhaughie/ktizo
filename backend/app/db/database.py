from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pathlib import Path
import os

# Database file location
# Use DATA_DIR environment variable if set, otherwise use ~/.ktizo/data
data_dir_env = os.getenv("DATA_DIR")
if data_dir_env:
    DB_DIR = Path(data_dir_env)
else:
    # Default to ~/.ktizo/data
    DB_DIR = Path.home() / ".ktizo" / "data"

DB_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_URL = f"sqlite:///{DB_DIR}/ktizo.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """Dependency for getting database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize database tables and run migrations"""
    from app.db.models import NetworkSettings, ClusterSettings, Device, HelmRelease, HelmRepository
    from app.db.migrate import migrate_database

    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)

    # Run migrations for existing tables
    migrate_database()
