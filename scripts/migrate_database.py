#!/usr/bin/env python3
# netWORKS - Database Migration Script

import os
import sys
import logging
import argparse
from pathlib import Path

# Add the parent directory to the sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import our database modules
from core.database.bridge_db_manager import BridgeDatabaseManager

def setup_logging():
    """Set up logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("database_migration.log")
        ]
    )
    return logging.getLogger(__name__)

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Migrate netWORKS database to object-based format")
    
    parser.add_argument(
        "--source", 
        default="data/device_database.db", 
        help="Source database path (default: data/device_database.db)"
    )
    
    parser.add_argument(
        "--dest", 
        default="@data/device_database_new.db", 
        help="Destination database path (default: @data/device_database_new.db)"
    )
    
    parser.add_argument(
        "--backup", 
        action="store_true", 
        help="Create a backup of the source database"
    )
    
    parser.add_argument(
        "--replace", 
        action="store_true", 
        help="Replace the source database with the new one after migration"
    )
    
    return parser.parse_args()

def main():
    """Main migration function."""
    logger = setup_logging()
    args = parse_arguments()
    
    source_path = args.source
    dest_path = args.dest
    
    # Check if source database exists
    if not os.path.exists(source_path):
        logger.error(f"Source database not found: {source_path}")
        return 1
    
    # Create backup if requested
    if args.backup:
        import shutil
        backup_path = f"{source_path}.bak"
        logger.info(f"Creating backup at {backup_path}")
        try:
            shutil.copy2(source_path, backup_path)
            logger.info("Backup created successfully")
        except Exception as e:
            logger.error(f"Failed to create backup: {str(e)}")
            return 1
    
    # Perform migration
    logger.info(f"Starting migration from {source_path} to {dest_path}")
    try:
        bridge_db = BridgeDatabaseManager.migrate_from_legacy_db(source_path, dest_path)
        logger.info("Migration completed successfully")
        
        # Log some statistics
        device_count = len(bridge_db.get_devices())
        logger.info(f"Migrated {device_count} devices")
        
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}", exc_info=True)
        return 1
    
    # Replace source database if requested
    if args.replace:
        try:
            logger.info("Replacing source database with new database")
            if os.path.exists(source_path):
                os.remove(source_path)
            os.rename(dest_path, source_path)
            logger.info("Source database replaced successfully")
        except Exception as e:
            logger.error(f"Failed to replace source database: {str(e)}")
            return 1
    
    logger.info("Migration process completed")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 