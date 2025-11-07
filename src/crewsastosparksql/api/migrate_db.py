import os
from pathlib import Path
from crewsastosparksql.api.database import engine, Base

DB_DIR = Path(__file__).parent.parent.parent.parent / "data"
DB_FILE = DB_DIR / "crewsas.db"

if DB_FILE.exists():
    print(f"Removing old database: {DB_FILE}")
    os.remove(DB_FILE)

print("Creating new database with updated schema...")
Base.metadata.create_all(bind=engine)
print("Database migrated successfully")
