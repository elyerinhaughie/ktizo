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

        # Add system_extensions, kernel_modules, factory_schematic_id columns if they don't exist
        for col_name in ('system_extensions', 'kernel_modules', 'factory_schematic_id'):
            if col_name not in columns:
                logger.info(f"Adding {col_name} column to cluster_settings table")
                with engine.connect() as conn:
                    conn.execute(text(f'ALTER TABLE cluster_settings ADD COLUMN {col_name} VARCHAR'))
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
    else:
        # Add per-device storage columns if they don't exist
        columns = [col['name'] for col in inspector.get_columns('devices')]
        storage_columns = {
            'install_disk': 'VARCHAR',
            'ephemeral_min_size': 'VARCHAR',
            'ephemeral_max_size': 'VARCHAR',
            'ephemeral_disk_selector': 'VARCHAR',
        }
        for col_name, col_type in storage_columns.items():
            if col_name not in columns:
                logger.info(f"Adding {col_name} column to devices table")
                with engine.connect() as conn:
                    conn.execute(text(f'ALTER TABLE devices ADD COLUMN {col_name} {col_type}'))
                    conn.commit()

    # Check if helm_releases table exists and add log_output column
    if 'helm_releases' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('helm_releases')]
        if 'log_output' not in columns:
            logger.info("Adding log_output column to helm_releases table")
            with engine.connect() as conn:
                conn.execute(text('ALTER TABLE helm_releases ADD COLUMN log_output TEXT'))
                conn.commit()

    logger.info("Database migration completed successfully")
