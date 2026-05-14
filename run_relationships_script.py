#!/usr/bin/env python3
"""
Script to run the improved relationships SQL script
"""

from sqlalchemy import create_engine, text
from sqlalchemy.engine.url import URL

# Database connection
connection_string = URL.create(
    drivername="postgresql+psycopg2",
    username="postgres",
    password="password",
    host="postgres",
    port=5432,
    database="postgres",
)

engine = create_engine(connection_string)

# Read and execute SQL script
with open('create_improved_relationships.sql', 'r') as f:
    sql_script = f.read()

try:
    with engine.begin() as conn:  # Use begin() for transaction management
        # Split script into logical sections
        # First, execute all CREATE TABLE statements
        # Then CREATE INDEX statements
        # Then CREATE VIEW statements
        # Finally CREATE FUNCTION statements
        
        # Remove comments and split by semicolon, but preserve function definitions
        lines = sql_script.split('\n')
        statements = []
        current_statement = []
        in_function = False
        
        for line in lines:
            stripped = line.strip()
            # Skip empty lines and comments
            if not stripped or stripped.startswith('--'):
                continue
            
            current_statement.append(line)
            
            # Check if we're in a function definition
            if 'CREATE OR REPLACE FUNCTION' in stripped.upper():
                in_function = True
            
            # Function ends with $$ LANGUAGE
            if in_function and '$$ LANGUAGE' in stripped:
                statements.append('\n'.join(current_statement))
                current_statement = []
                in_function = False
            # Regular statement ends with semicolon (but not if in function)
            elif not in_function and stripped.endswith(';'):
                statements.append('\n'.join(current_statement))
                current_statement = []
        
        # Add any remaining statement
        if current_statement:
            statements.append('\n'.join(current_statement))
        
        # Execute statements
        for i, statement in enumerate(statements, 1):
            statement = statement.strip()
            if not statement:
                continue
            
            # Remove trailing semicolon if present (except for functions)
            if not in_function and statement.endswith(';'):
                statement = statement[:-1]
            
            try:
                conn.execute(text(statement))
                # Show what was executed
                preview = statement.replace('\n', ' ')[:80]
                print(f"✅ [{i}/{len(statements)}] Executed: {preview}...")
            except Exception as e:
                error_msg = str(e)
                # Some errors are expected (already exists, etc.)
                if any(phrase in error_msg.lower() for phrase in ["already exists", "duplicate", "does not exist"]):
                    print(f"⚠️  [{i}/{len(statements)}] Skipped: {error_msg[:60]}...")
                else:
                    print(f"❌ [{i}/{len(statements)}] Error: {error_msg[:100]}")
                    print(f"   Statement preview: {statement[:100]}...")
                    # Don't fail completely, continue with other statements
        
        print("\n✅ Database relationships script execution completed!")
        
except Exception as e:
    print(f"❌ Error running script: {e}")
    import traceback
    traceback.print_exc()

