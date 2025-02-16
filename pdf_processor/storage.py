from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
from azure.core.exceptions import ResourceExistsError
import os
import json
from typing import Optional, BinaryIO, Dict, Any
from datetime import datetime, timedelta
from pdf_processor.config import get_settings
import logging

logger = logging.getLogger(__name__)

class AzureBlobStorage:
    def __init__(self):
        settings = get_settings()
        self.connection_string = settings.azure_storage_connection_string
        self.container_name = settings.azure_storage_container_name
        self.blob_service_client = BlobServiceClient.from_connection_string(self.connection_string)
        self._ensure_container_exists()

    def _ensure_container_exists(self):
        """Ensure the container exists, create it if it doesn't."""
        try:
            container_client = self.blob_service_client.create_container(self.container_name)
            logger.info(f"Created container: {self.container_name}")
        except ResourceExistsError:
            logger.info(f"Container {self.container_name} already exists")
        except Exception as e:
            logger.error(f"Error ensuring container exists: {str(e)}")
            raise

    def get_container_client(self):
        """Get the container client for testing."""
        return self.blob_service_client.get_container_client(self.container_name)

    async def upload_pdf(self, file: BinaryIO, filename: str) -> str:
        """
        Upload a PDF file to Azure Blob Storage.
        
        Args:
            file: The file-like object containing the PDF data
            filename: The name to give the file in storage
            
        Returns:
            str: The URL of the uploaded file
        """
        try:
            # Create a unique filename with timestamp
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            blob_name = f"{timestamp}_{filename}"
            
            # Get the blob client
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            
            # Upload the file
            blob_client.upload_blob(file, overwrite=True)
            
            # Get the blob URL
            blob_url = blob_client.url
            
            logger.info(f"Successfully uploaded file {blob_name}")
            return blob_url
            
        except Exception as e:
            logger.error(f"Error uploading file {filename}: {str(e)}")
            raise

    async def get_pdf(self, blob_name: str) -> Optional[bytes]:
        """
        Retrieve a PDF file from Azure Blob Storage.
        
        Args:
            blob_name: The name of the blob to retrieve
            
        Returns:
            Optional[bytes]: The file contents if found, None otherwise
        """
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            
            # Download the blob
            blob_data = blob_client.download_blob()
            return await blob_data.content_as_bytes()
            
        except Exception as e:
            logger.error(f"Error retrieving file {blob_name}: {str(e)}")
            return None

    async def delete_pdf(self, blob_name: str) -> bool:
        """
        Delete a PDF file from Azure Blob Storage.
        
        Args:
            blob_name: The name of the blob to delete
            
        Returns:
            bool: True if deletion was successful, False otherwise
        """
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            
            blob_client.delete_blob()
            logger.info(f"Successfully deleted file {blob_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting file {blob_name}: {str(e)}")
            return False

    def generate_sas_url(self, blob_name: str, expiry_hours: int = 24) -> Optional[str]:
        """
        Generate a Shared Access Signature (SAS) URL for a blob.
        
        Args:
            blob_name: The name of the blob
            expiry_hours: Number of hours until the SAS token expires
            
        Returns:
            Optional[str]: The SAS URL if successful, None otherwise
        """
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            
            # Generate SAS token
            expiry = datetime.utcnow() + timedelta(hours=expiry_hours)
            sas_token = blob_client.generate_shared_access_signature(
                permission="read",
                expiry=expiry
            )
            
            # Combine the blob URL with the SAS token
            sas_url = f"{blob_client.url}?{sas_token}"
            return sas_url
            
        except Exception as e:
            logger.error(f"Error generating SAS URL for {blob_name}: {str(e)}")
            return None

    async def store_json_data(self, blob_name: str, data: Dict[str, Any]) -> bool:
        """
        Store JSON data in Azure Blob Storage.
        
        Args:
            blob_name: The name of the blob
            data: Dictionary to store as JSON
            
        Returns:
            bool: True if storage was successful, False otherwise
        """
        try:
            # Convert data to JSON string
            json_str = json.dumps(data)
            
            # Get the blob client
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            
            # Upload the JSON data
            blob_client.upload_blob(json_str, overwrite=True)
            logger.info(f"Successfully stored JSON data in {blob_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing JSON data in {blob_name}: {str(e)}")
            return False

    async def get_json_data(self, blob_name: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve JSON data from Azure Blob Storage.
        
        Args:
            blob_name: The name of the blob to retrieve
            
        Returns:
            Optional[Dict[str, Any]]: The JSON data if found, None otherwise
        """
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            
            # Download the blob
            blob_data = blob_client.download_blob()
            json_str = await blob_data.content_as_text()
            
            # Parse JSON
            return json.loads(json_str)
            
        except Exception as e:
            logger.error(f"Error retrieving JSON data from {blob_name}: {str(e)}")
            return None 