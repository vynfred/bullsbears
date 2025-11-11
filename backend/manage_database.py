#!/usr/bin/env python3
"""
Database Management Script for BullsBears Candidate Tracking System
Provides utilities for database operations, migrations, and maintenance
"""

import asyncio
import asyncpg
import sys
import os
from datetime import datetime, timedelta

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.core.config import settings


async def check_database_status():
    """Check database connection and table status"""
    print("🔍 Checking database status...")
    
    try:
        conn = await asyncpg.connect(settings.database_url)
        
        # Check PostgreSQL version
        version = await conn.fetchval("SELECT version()")
        print(f"✅ Database connected: {version.split(',')[0]}")
        
        # Check candidate tracking tables
        tables_query = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name LIKE '%candidate%'
        ORDER BY table_name
        """
        
        tables = await conn.fetch(tables_query)
        print(f"\n📊 Candidate Tracking Tables ({len(tables)}):")
        for table in tables:
            # Get row count
            count = await conn.fetchval(f"SELECT COUNT(*) FROM {table['table_name']}")
            print(f"   • {table['table_name']}: {count} rows")
        
        await conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Database check failed: {e}")
        return False


async def run_migration(migration_file: str):
    """Run a specific migration file"""
    print(f"🔄 Running migration: {migration_file}")
    
    migration_path = os.path.join(os.path.dirname(__file__), 'database', 'migrations', migration_file)
    
    if not os.path.exists(migration_path):
        print(f"❌ Migration file not found: {migration_path}")
        return False
    
    try:
        conn = await asyncpg.connect(settings.database_url)
        
        # Read and execute migration
        with open(migration_path, 'r') as f:
            migration_sql = f.read()
        
        await conn.execute(migration_sql)
        await conn.close()
        
        print(f"✅ Migration completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False


async def rollback_migration(rollback_file: str):
    """Run a rollback migration"""
    print(f"🔄 Running rollback: {rollback_file}")
    
    rollback_path = os.path.join(os.path.dirname(__file__), 'database', 'migrations', rollback_file)
    
    if not os.path.exists(rollback_path):
        print(f"❌ Rollback file not found: {rollback_path}")
        return False
    
    try:
        conn = await asyncpg.connect(settings.database_url)
        
        # Read and execute rollback
        with open(rollback_path, 'r') as f:
            rollback_sql = f.read()
        
        await conn.execute(rollback_sql)
        await conn.close()
        
        print(f"✅ Rollback completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Rollback failed: {e}")
        return False


async def show_recent_candidates(limit: int = 10):
    """Show recent candidates"""
    print(f"📋 Recent Candidates (last {limit}):")
    
    try:
        conn = await asyncpg.connect(settings.database_url)
        
        query = """
        SELECT candidate_id, ticker, predictor_agent, agent_confidence, 
               prediction_type, selected_by_arbitrator, created_at
        FROM pick_candidates 
        ORDER BY created_at DESC 
        LIMIT $1
        """
        
        candidates = await conn.fetch(query, limit)
        
        if not candidates:
            print("   No candidates found")
        else:
            print(f"   {'ID':<4} {'Ticker':<6} {'Agent':<25} {'Conf':<5} {'Type':<8} {'Selected':<8} {'Created'}")
            print("   " + "-" * 80)
            
            for candidate in candidates:
                selected = "✅" if candidate['selected_by_arbitrator'] else "❌"
                created = candidate['created_at'].strftime("%m/%d %H:%M")
                
                print(f"   {candidate['candidate_id']:<4} {candidate['ticker']:<6} "
                      f"{candidate['predictor_agent'][:24]:<25} {candidate['agent_confidence']:<5} "
                      f"{candidate['prediction_type']:<8} {selected:<8} {created}")
        
        await conn.close()
        
    except Exception as e:
        print(f"❌ Failed to show candidates: {e}")


async def cleanup_old_data(days: int = 90):
    """Clean up old candidate data"""
    print(f"🧹 Cleaning up data older than {days} days...")
    
    try:
        conn = await asyncpg.connect(settings.database_url)
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Delete old price tracking data
        price_deleted = await conn.fetchval(
            "DELETE FROM candidate_price_tracking WHERE created_at < $1 RETURNING COUNT(*)",
            cutoff_date
        )
        
        # Delete old candidates
        candidates_deleted = await conn.fetchval(
            "DELETE FROM pick_candidates WHERE created_at < $1 RETURNING COUNT(*)",
            cutoff_date
        )
        
        # Delete old analysis data
        analysis_deleted = await conn.fetchval(
            "DELETE FROM candidate_retrospective_analysis WHERE created_at < $1 RETURNING COUNT(*)",
            cutoff_date
        )
        
        await conn.close()
        
        print(f"✅ Cleanup completed:")
        print(f"   • Price tracking records deleted: {price_deleted or 0}")
        print(f"   • Candidates deleted: {candidates_deleted or 0}")
        print(f"   • Analysis records deleted: {analysis_deleted or 0}")
        
    except Exception as e:
        print(f"❌ Cleanup failed: {e}")


async def backup_database():
    """Create a database backup"""
    print("💾 Creating database backup...")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"backup_bullsbears_{timestamp}.sql"
    
    try:
        # Use pg_dump to create backup
        import subprocess
        
        cmd = [
            'pg_dump',
            '-h', 'localhost',
            '-U', 'vynfred',
            '-d', 'bullsbears',
            '-f', backup_file,
            '--no-password'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ Backup created: {backup_file}")
            
            # Show file size
            file_size = os.path.getsize(backup_file) / 1024  # KB
            print(f"   File size: {file_size:.1f} KB")
        else:
            print(f"❌ Backup failed: {result.stderr}")
            
    except Exception as e:
        print(f"❌ Backup failed: {e}")


def print_help():
    """Print help information"""
    print("""
🗄️  BullsBears Database Management Tool

Usage: python3 manage_database.py <command> [options]

Commands:
  status                    - Check database connection and table status
  migrate [file]            - Run migration (default: 002_optimized_agent_schema.sql)
  rollback                  - Rollback candidate tracking migration
  candidates [limit]        - Show recent candidates (default: 10)
  cleanup [days]            - Clean up old data (default: 90 days)
  backup                    - Create database backup
  help                      - Show this help message

Examples:
  python3 manage_database.py status
  python3 manage_database.py migrate
  python3 manage_database.py migrate 002_optimized_agent_schema.sql
  python3 manage_database.py candidates 20
  python3 manage_database.py cleanup 30
  python3 manage_database.py backup
    """)


async def main():
    """Main function"""
    if len(sys.argv) < 2:
        print_help()
        return
    
    command = sys.argv[1].lower()
    
    if command == 'status':
        await check_database_status()
        
    elif command == 'migrate':
        # Check if we have a specific migration file argument
        if len(sys.argv) > 2:
            migration_file = sys.argv[2]
        else:
            migration_file = '002_optimized_agent_schema.sql'  # Default to new schema
        await run_migration(migration_file)
        
    elif command == 'rollback':
        await rollback_migration('001_rollback_candidate_tracking_tables.sql')
        
    elif command == 'candidates':
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        await show_recent_candidates(limit)
        
    elif command == 'cleanup':
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 90
        await cleanup_old_data(days)
        
    elif command == 'backup':
        await backup_database()
        
    elif command == 'help':
        print_help()
        
    else:
        print(f"❌ Unknown command: {command}")
        print_help()


if __name__ == "__main__":
    asyncio.run(main())
