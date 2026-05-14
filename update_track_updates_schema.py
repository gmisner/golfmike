#!/usr/bin/env python3
"""Update track_updates table schema to include aircraft_id"""

from sqlalchemy import create_engine, text
from sqlalchemy.engine.url import URL

connection_string = URL.create(
    drivername="postgresql+psycopg2",
    username="postgres",
    password="password",
    host="postgres",
    port=5432,
    database="postgres",
)

engine = create_engine(connection_string)

with engine.connect() as conn:
    print("Updating track_updates table schema...")
    
    # Add aircraft_id column if it doesn't exist
    try:
        conn.execute(text("""
            ALTER TABLE track_updates 
            ADD COLUMN IF NOT EXISTS aircraft_id VARCHAR(50)
        """))
        print("✅ Added aircraft_id column")
    except Exception as e:
        print(f"⚠️  Error adding column (might already exist): {e}")
    
    # Update existing records to have aircraft_id from flights table
    try:
        conn.execute(text("""
            UPDATE track_updates tu
            SET aircraft_id = f.aircraft_id
            FROM flights f
            WHERE tu.gufi = f.gufi
            AND (tu.aircraft_id IS NULL OR tu.aircraft_id = '')
        """))
        print("✅ Updated existing records with aircraft_id")
    except Exception as e:
        print(f"⚠️  Error updating records: {e}")
    
    # Make aircraft_id NOT NULL if all records have it
    try:
        conn.execute(text("""
            ALTER TABLE track_updates 
            ALTER COLUMN aircraft_id SET NOT NULL
        """))
        print("✅ Set aircraft_id to NOT NULL")
    except Exception as e:
        print(f"⚠️  Could not set NOT NULL (some records may be missing aircraft_id): {e}")
    
    # Add foreign key constraint (check if it exists first)
    try:
        check_result = conn.execute(text("""
            SELECT COUNT(*) FROM information_schema.table_constraints 
            WHERE constraint_name = 'fk_track_updates_aircraft' 
            AND table_name = 'track_updates'
        """))
        constraint_exists = check_result.scalar() > 0
        
        if not constraint_exists:
            conn.execute(text("""
                ALTER TABLE track_updates 
                ADD CONSTRAINT fk_track_updates_aircraft 
                FOREIGN KEY (aircraft_id) REFERENCES aircraft(aircraft_id)
            """))
            print("✅ Added foreign key constraint")
        else:
            print("✅ Foreign key constraint already exists")
    except Exception as e:
        print(f"⚠️  Error adding constraint: {e}")
    
    # Add index
    try:
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_track_updates_aircraft_id 
            ON track_updates(aircraft_id)
        """))
        print("✅ Added index on aircraft_id")
    except Exception as e:
        print(f"⚠️  Error adding index: {e}")
    
    conn.commit()
    print("\n✅ Schema update complete!")

