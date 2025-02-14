import os
import pytest
from pathlib import Path

@pytest.fixture(autouse=True)
def setup_test_env():
    """Setup test environment variables if not already set."""
    if not os.getenv('AZURE_STORAGE_CONNECTION_STRING'):
        os.environ['AZURE_STORAGE_CONNECTION_STRING'] = 'DefaultEndpointsProtocol=https;AccountName=test;AccountKey=test;EndpointSuffix=core.windows.net'
    
    if not os.getenv('AZURE_STORAGE_CONTAINER_NAME'):
        os.environ['AZURE_STORAGE_CONTAINER_NAME'] = 'pdf-files'
    
    # Add project root to Python path
    project_root = Path(__file__).parent.parent
    if str(project_root) not in os.getenv('PYTHONPATH', ''):
        os.environ['PYTHONPATH'] = f"{project_root}:{os.getenv('PYTHONPATH', '')}" 