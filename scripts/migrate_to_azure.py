import os
import asyncio
from dotenv import load_dotenv
import httpx
from pdf_processor.storage import AzureBlobStorage
from supabase import create_client, Client

# Load environment variables
load_dotenv()

# Initialize Supabase client
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

# Initialize Azure Blob Storage
azure_storage = AzureBlobStorage()

async def migrate_files():
    """Migrate files from Supabase Storage to Azure Blob Storage."""
    try:
        print("Starting migration from Supabase to Azure Blob Storage...")
        
        # List all files in Supabase storage
        response = supabase.storage.from_("pdfs").list()
        
        if not response:
            print("No files found in Supabase storage.")
            return
        
        print(f"Found {len(response)} files to migrate.")
        
        async with httpx.AsyncClient() as client:
            for file in response:
                try:
                    # Get file URL from Supabase
                    file_url = supabase.storage.from_("pdfs").get_public_url(file["name"])
                    
                    # Download file from Supabase
                    print(f"Downloading {file['name']} from Supabase...")
                    response = await client.get(file_url)
                    response.raise_for_status()
                    
                    # Upload to Azure Blob Storage
                    print(f"Uploading {file['name']} to Azure Blob Storage...")
                    file_content = response.content
                    azure_url = await azure_storage.upload_pdf(file_content, file["name"])
                    
                    print(f"Successfully migrated {file['name']}")
                    print(f"Azure URL: {azure_url}")
                    
                except Exception as e:
                    print(f"Error migrating file {file['name']}: {str(e)}")
                    continue
        
        print("Migration completed!")
        
    except Exception as e:
        print(f"Error during migration: {str(e)}")

if __name__ == "__main__":
    asyncio.run(migrate_files()) 