"""Simple database migration script"""
from sqlalchemy import text, inspect
from app.db.database import engine, Base
from app.db.models import ClusterSettings, Device
import logging

logger = logging.getLogger(__name__)

def migrate_database():
    """Run database migrations on startup"""
    inspector = inspect(engine)

    # Check if cluster_settings table exists
    if 'cluster_settings' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('cluster_settings')]

        # Add external_subnet column if it doesn't exist
        if 'external_subnet' not in columns:
            logger.info("Adding external_subnet column to cluster_settings table")
            with engine.connect() as conn:
                conn.execute(text('ALTER TABLE cluster_settings ADD COLUMN external_subnet VARCHAR'))
                conn.commit()

    # Check if network_settings table exists
    if 'network_settings' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('network_settings')]

        # Add strict_boot_mode column if it doesn't exist
        if 'strict_boot_mode' not in columns:
            logger.info("Adding strict_boot_mode column to network_settings table")
            with engine.connect() as conn:
                conn.execute(text('ALTER TABLE network_settings ADD COLUMN strict_boot_mode BOOLEAN DEFAULT 0'))
                conn.commit()

    # Check if devices table exists, if not create all tables
    if 'devices' not in inspector.get_table_names():
        logger.info("Creating missing tables (including devices table)")
        Base.metadata.create_all(bind=engine)

    logger.info("Database migration completed successfully")
