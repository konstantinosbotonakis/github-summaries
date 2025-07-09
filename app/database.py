"""
Database configuration and connection management.
"""

import logging
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from databases import Database

from app.config import settings

logger = logging.getLogger(__name__)

# SQLAlchemy setup
engine = create_engine(
    settings.DATABASE_URL,
    poolclass=StaticPool,
    connect_args={
        "check_same_thread": False,
    } if "sqlite" in settings.DATABASE_URL else {},
    echo=settings.DEBUG,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create declarative base
Base = declarative_base()

# Async database connection
database = Database(settings.DATABASE_URL)

# Metadata for table creation
metadata = MetaData()


async def create_tables():
    """Create database tables."""
    try:
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise


async def connect_database():
    """Connect to the database."""
    try:
        await database.connect()
        logger.info("Connected to database")
    except Exception as e:
        logger.error(f"Error connecting to database: {e}")
        raise


async def disconnect_database():
    """Disconnect from the database."""
    try:
        await database.disconnect()
        logger.info("Disconnected from database")
    except Exception as e:
        logger.error(f"Error disconnecting from database: {e}")


def get_db():
    """
    Dependency to get database session.
    
    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db():
    """
    Get async database connection.
    
    Returns:
        Database: Async database connection
    """
    return database


class DatabaseManager:
    """Database manager for handling connections and operations."""
    
    def __init__(self):
        self.engine = engine
        self.database = database
        self.session_local = SessionLocal
    
    async def health_check(self) -> bool:
        """
        Check database health.
        
        Returns:
            bool: True if database is healthy, False otherwise
        """
        try:
            # Test connection with a simple query
            query = "SELECT 1"
            result = await self.database.fetch_one(query)
            return result is not None
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    async def get_connection_info(self) -> dict:
        """
        Get database connection information.
        
        Returns:
            dict: Connection information
        """
        try:
            query = "SELECT version()"
            result = await self.database.fetch_one(query)
            return {
                "status": "connected",
                "version": result[0] if result else "unknown",
                "url": settings.DATABASE_URL.split("@")[-1] if "@" in settings.DATABASE_URL else "unknown"
            }
        except Exception as e:
            logger.error(f"Error getting database info: {e}")
            return {
                "status": "error",
                "error": str(e)
            }


# Create database manager instance
db_manager = DatabaseManager()