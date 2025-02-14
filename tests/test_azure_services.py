import os
import pytest
from pdf_processor.storage import AzureBlobStorage
from pdf_processor.database import Database
from pdf_processor.config import settings

@pytest.mark.env
def test_environment_variables():
    """Test that all required environment variables are set"""
    required_vars = [
        'AZURE_STORAGE_CONNECTION_STRING',
        'AZURE_STORAGE_CONTAINER_NAME',
        'POSTGRES_USER',
        'POSTGRES_PASSWORD',
        'POSTGRES_HOST',
        'POSTGRES_DB'
    ]
    
    for var in required_vars:
        assert os.getenv(var) is not None, f"Missing environment variable: {var}"

@pytest.mark.storage
def test_azure_blob_storage_connection():
    """Test Azure Blob Storage connection"""
    if not os.getenv('AZURE_STORAGE_CONNECTION_STRING'):
        pytest.skip("Azure storage connection string not configured")
    
    storage = AzureBlobStorage()
    container_client = storage.get_container_client()
    list(container_client.list_blobs())

@pytest.mark.db
def test_database_connection():
    """Test PostgreSQL database connection"""
    if not all([
        os.getenv('POSTGRES_USER'),
        os.getenv('POSTGRES_PASSWORD'),
        os.getenv('POSTGRES_HOST'),
        os.getenv('POSTGRES_DB')
    ]):
        pytest.skip("Database credentials not configured")
    
    db = Database()
    with db.get_session() as session:
        result = session.execute("SELECT 1")
        assert result.scalar() == 1 