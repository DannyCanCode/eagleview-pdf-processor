import os
import sys

def test_simple():
    """A simple test to verify pytest is working"""
    print("\nPython version:", sys.version)
    print("Current working directory:", os.getcwd())
    print("Python path:", sys.path)
    print("Environment variables:", {k: v for k, v in os.environ.items() if k.startswith(('AZURE_', 'POSTGRES_'))})
    assert True 