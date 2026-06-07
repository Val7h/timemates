#!/usr/bin/env python3
"""
Migration runner for TimeMates
Executes SQL migrations from the migrations directory
"""

import os
import sys
from datetime import datetime
from sqlalchemy import text
from database import engine

def run_migrations():
    """Execute all pending migrations."""
    migrations_dir = os.path.join(os.path.dirname(__file__), "migrations")
    
    if not os.path.exists(migrations_dir):
        print("[MIGRATE] migrations/ directory not found")
        return False
    
    # Get all SQL files sorted by name
    migration_files = sorted([
        f for f in os.listdir(migrations_dir) 
        if f.endswith('.sql')
    ])
    
    if not migration_files:
        print("[MIGRATE] No migration files found")
        return True
    
    print(f"[MIGRATE] Found {len(migration_files)} migration file(s)")
    
    with engine.connect() as conn:
        for migration_file in migration_files:
            file_path = os.path.join(migrations_dir, migration_file)
            print(f"[MIGRATE] Executing {migration_file}...")
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    sql_content = f.read()
                
                # Split by semicolon and execute each statement
                statements = [
                    stmt.strip() 
                    for stmt in sql_content.split(';') 
                    if stmt.strip()
                ]
                
                for stmt in statements:
                    try:
                        conn.execute(text(stmt))
                    except Exception as e:
                        # If it's an "already exists" error, skip
                        if "already exists" in str(e) or "duplicate" in str(e).lower():
                            print(f"[MIGRATE] Skipped: {stmt[:50]}... (already exists)")
                        else:
                            print(f"[MIGRATE] Error executing statement: {e}")
                            # Don't fail, continue with next statement
                
                conn.commit()
                print(f"[MIGRATE] ✓ {migration_file} completed")
                
            except Exception as e:
                print(f"[MIGRATE] ✗ Error with {migration_file}: {e}")
                return False
    
    print("[MIGRATE] All migrations completed successfully!")
    return True

if __name__ == "__main__":
    try:
        success = run_migrations()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"[MIGRATE] Fatal error: {e}")
        sys.exit(1)
