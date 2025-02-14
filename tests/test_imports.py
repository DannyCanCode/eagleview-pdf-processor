def test_can_import_config():
    """Test that we can import config module"""
    from pdf_processor.config import get_settings
    settings = get_settings()
    assert hasattr(settings, 'postgres_user')

def test_can_import_database():
    """Test that we can import database module"""
    from pdf_processor.database import Database
    db = Database()
    assert hasattr(db, 'get_test_session')

def test_can_import_storage():
    """Test that we can import storage module"""
    from pdf_processor.storage import AzureBlobStorage
    storage = AzureBlobStorage()
    assert hasattr(storage, 'get_container_client') 