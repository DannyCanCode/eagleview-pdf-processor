import os
from dotenv import load_dotenv
import psycopg2
from psycopg2 import OperationalError

def test_connection():
    try:
        # Load environment variables from .env file
        load_dotenv()
        
        # Get database connection parameters from environment variables
        host = os.getenv('POSTGRES_HOST')
        database = os.getenv('POSTGRES_DB')
        user = os.getenv('POSTGRES_USER')
        password = os.getenv('POSTGRES_PASSWORD')
        port = os.getenv('POSTGRES_PORT', '5432')
        
        # Print raw environment variables for debugging
        print("\nEnvironment variables:")
        print(f"POSTGRES_HOST: {os.getenv('POSTGRES_HOST')}")
        print(f"POSTGRES_USER: {os.getenv('POSTGRES_USER')}")
        print(f"POSTGRES_PASSWORD: {'*' * len(os.getenv('POSTGRES_PASSWORD'))}")
        print(f"POSTGRES_DB: {os.getenv('POSTGRES_DB')}")
        print(f"POSTGRES_PORT: {os.getenv('POSTGRES_PORT')}\n")
        
        # Try to establish a connection
        print("Attempting to connect to the database...")
        print(f"Host: {host}")
        print(f"Database: {database}")
        print(f"User: {user}")
        print(f"Port: {port}")
        print(f"SSL Mode: require")
        
        # Create connection with minimal SSL verification
        conn = psycopg2.connect(
            dbname=database,
            user=user,
            password=password,
            host=host,
            port=port,
            sslmode='require'
        )
        
        print("Successfully connected to the database!")
        
        # Test the connection by executing a simple query
        cursor = conn.cursor()
        cursor.execute('SELECT version();')
        version = cursor.fetchone()
        print(f"PostgreSQL version: {version[0]}")
        
        cursor.close()
        conn.close()
        print("Connection closed successfully.")
        
    except OperationalError as e:
        print(f"Error connecting to the database: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    test_connection() 