import os
import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from pdf_processor.storage import AzureBlobStorage
from pdf_processor.database import Database
from pdf_processor.config import get_settings

def test_settings_loaded():
    """Test that settings are loaded correctly"""
    settings = get_settings()
    print("\nSettings values (excluding passwords):")
    for field in settings.model_fields:
        value = getattr(settings, field)
        if 'password' not in field.lower():
            print(f"{field} = {value}")
    
    # Test required settings are present
    assert settings.postgres_user, "postgres_user not set"
    assert settings.postgres_password, "postgres_password not set"
    assert settings.postgres_host, "postgres_host not set"
    assert settings.postgres_db, "postgres_db not set"
    assert settings.azure_storage_connection_string, "azure_storage_connection_string not set"

@pytest.mark.storage
def test_azure_blob_storage_connection():
    """Test Azure Blob Storage connection"""
    settings = get_settings()
    if not settings.azure_storage_connection_string:
        pytest.skip("Azure storage connection string not configured")
    
    storage = AzureBlobStorage()
    container_client = storage.get_container_client()
    list(container_client.list_blobs())

@pytest.mark.db
def test_database_connection():
    """Test PostgreSQL database connection"""
    settings = get_settings()
    
    # Print debug information about database configuration
    print("\nDatabase connection details (excluding sensitive info):")
    print(f"Host: {settings.postgres_host}")
    print(f"Port: {settings.postgres_port}")
    print(f"Database: {settings.postgres_db}")
    print(f"User: {settings.postgres_user}")
    
    if not all([
        settings.postgres_user,
        settings.postgres_password,
        settings.postgres_host,
        settings.postgres_db
    ]):
        pytest.skip("Database credentials not configured")
    
    db = Database()
    session = db.get_test_session()
    try:
        # Try to connect and execute query
        try:
            result = session.execute(text("SELECT 1"))
            assert result.scalar() == 1
        except OperationalError as e:
            if "could not translate host name" in str(e):
                pytest.skip(f"Could not resolve database host: {settings.postgres_host}")
            raise
    finally:
        session.close() 