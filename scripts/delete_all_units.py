"""
Script to delete all cold storage units from the database
Run this from the project root: python scripts/delete_all_units.py
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models import ColdStorageUnit, TemperatureLog, TemperatureEntry
from extensions import db

def delete_all_units():
    """Delete all cold storage units and their related data"""
    app = create_app()
    
    with app.app_context():
        try:
            # Get count before deletion
            unit_count = ColdStorageUnit.query.count()
            log_count = TemperatureLog.query.count()
            entry_count = TemperatureEntry.query.count()
            
            print(f"Found {unit_count} units, {log_count} temperature logs, {entry_count} temperature entries")
            
            if unit_count == 0:
                print("No units to delete.")
                return
            
            # Confirm deletion
            response = input(f"\nAre you sure you want to delete ALL {unit_count} units? (yes/no): ")
            if response.lower() != 'yes':
                print("Deletion cancelled.")
                return
            
            # Delete in order to handle foreign key constraints
            # First delete temperature entries
            deleted_entries = TemperatureEntry.query.delete()
            print(f"Deleted {deleted_entries} temperature entries")
            
            # Then delete temperature logs
            deleted_logs = TemperatureLog.query.delete()
            print(f"Deleted {deleted_logs} temperature logs")
            
            # Finally delete units
            deleted_units = ColdStorageUnit.query.delete()
            print(f"Deleted {deleted_units} units")
            
            # Commit the changes
            db.session.commit()
            print("\n✓ All units and related data have been deleted successfully!")
            
        except Exception as e:
            db.session.rollback()
            print(f"\n✗ Error deleting units: {str(e)}")
            raise

if __name__ == '__main__':
    delete_all_units()
