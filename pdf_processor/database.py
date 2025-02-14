from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pdf_processor.config import get_settings
from typing import Generator

class Database:
    def __init__(self):
        self.settings = get_settings()
        self.engine = self._create_engine()
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.Base = declarative_base()

    def _create_engine(self):
        """Create SQLAlchemy engine with connection URL."""
        DATABASE_URL = (
            f"postgresql://{self.settings.postgres_user}:{self.settings.postgres_password}"
            f"@{self.settings.postgres_host}:{self.settings.postgres_port}/{self.settings.postgres_db}"
        )
        return create_engine(DATABASE_URL)

    def get_session(self) -> Generator[Session, None, None]:
        """Get database session as a generator (for FastAPI dependency injection)."""
        db = self.SessionLocal()
        try:
            yield db
        finally:
            db.close()

    def get_test_session(self) -> Session:
        """Get a direct database session (for testing)."""
        return self.SessionLocal() 