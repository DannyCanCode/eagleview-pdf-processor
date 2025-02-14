import os
import pytest
from pdf_processor.storage import AzureBlobStorage
from pdf_processor.database import Database
from pdf_processor.config import get_settings

@pytest.mark.env
def test_environment_variables():
    """Test that all required environment variables are set"""
    settings = get_settings()
    required_vars = [
        'azure_storage_connection_string',
        'azure_storage_container_name',
        'postgres_user',
        'postgres_password',
        'postgres_host',
        'postgres_db'
    ]
    
    for var in required_vars:
        assert hasattr(settings, var), f"Missing setting: {var}"

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
    if not all([
        settings.postgres_user,
        settings.postgres_password,
        settings.postgres_host,
        settings.postgres_db
    ]):
        pytest.skip("Database credentials not configured")
    
    db = Database()
    with db.get_session() as session:
        result = session.execute("SELECT 1")
        assert result.scalar() == 1 