import os
import sys

# Ensure this script runs with backend module path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker
from sqlalchemy.schema import DropTable
from sqlalchemy.ext.compiler import compiles

# Import all models to ensure metadata has them registered
from app.database.models import User, Calendar, Event, Task, WhatsAppThread, Base

@compiles(DropTable, "postgresql")
def _compile_drop_table(element, compiler, **kwargs):
    """
    Ensure we cascade when dropping tables in PostgreSQL to avoid
    dependency issues (like foreign keys).
    """
    return compiler.visit_drop_table(element) + " CASCADE"

def reset_database():
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        print("❌ Error: You must set the DATABASE_URL environment variable.")
        print("Example:")
        print("export DATABASE_URL='postgresql://user:password@host:port/dbname'")
        print("python reset_db_remote.py")
        sys.exit(1)
        
    print(f"🔄 Connecting to remote database at: {database_url.split('@')[-1]}")
    
    try:
        engine = create_engine(database_url)
        # Check connection
        with engine.connect() as conn:
            print("✅ Successfully connected to the database!")
            
        print("⚠️ Dropping ALL existing tables... This cannot be undone.")
        
        # We use an empty MetaData and reflect the existing db to drop everything
        # This handles cases where old tables exist that are not in our current models
        meta = MetaData()
        meta.reflect(bind=engine)
        meta.drop_all(bind=engine)
        
        print("✅ All existing tables dropped.")
        
        print("🔄 Creating new tables based on current local models...")
        # Create all tables registered in our Base metadata
        Base.metadata.create_all(bind=engine)
        
        print("✅ Remote database migration completed successfully!")
        print("🎉 Your remote database now has the exact same structure as your local database.")
        
    except Exception as e:
        print(f"❌ An error occurred: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    confirm = input("⚠️ WARNING: This will DELETE ALL DATA on the remote database. Are you sure you want to continue? (yes/no): ")
    if confirm.lower() == 'yes':
        reset_database()
    else:
        print("Operation cancelled.")
