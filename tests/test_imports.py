def test_can_import_config():
    """Test that we can import config module"""
    from pdf_processor.config import get_settings
    assert get_settings is not None

def test_can_import_database():
    """Test that we can import database module"""
    from pdf_processor.database import Database
    assert Database is not None

def test_can_import_storage():
    """Test that we can import storage module"""
    from pdf_processor.storage import AzureBlobStorage
    assert AzureBlobStorage is not None 