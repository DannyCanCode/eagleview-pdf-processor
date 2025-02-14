from setuptools import setup, find_packages

setup(
    name="pdf_processor",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "azure-storage-blob",
        "sqlalchemy",
        "psycopg2-binary",
        "python-dotenv",
        "pydantic",
        "pydantic-settings"
    ],
    extras_require={
        'test': [
            'pytest',
            'pytest-env',
            'pytest-cov',
            'pytest-asyncio'
        ]
    },
    python_requires='>=3.11',
) 