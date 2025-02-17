from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import fitz
import time
from datetime import datetime
from pdf_processor.extractor import create_extractor
from pdf_processor.models import ProcessingResponse
from pdf_processor.storage import AzureBlobStorage
from pdf_processor.database import Database
from pdf_processor.config import get_settings
import os

# Initialize FastAPI app
app = FastAPI(title="EagleView PDF Processor")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
pdf_extractor = create_extractor()
azure_storage = AzureBlobStorage()
db = Database()

@app.get("/")
async def root():
    """Root endpoint with detailed environment diagnostics."""
    settings = get_settings()
    storage_info = {
        "container_name": settings.azure_storage_container_name,
        "has_connection_string": bool(settings.azure_storage_connection_string),
        "connection_string_length": len(settings.azure_storage_connection_string) if settings.azure_storage_connection_string else 0,
        "environment_variables": {
            k: "[HIDDEN]" if "key" in k.lower() or "password" in k.lower() or "connection" in k.lower() 
            else v for k, v in os.environ.items() 
            if k.startswith(("AZURE_", "POSTGRES_"))
        }
    }
    
    # Test storage connection
    try:
        container_client = azure_storage.get_container_client()
        blobs = list(container_client.list_blobs())
        storage_info["connection_test"] = "success"
        storage_info["blob_count"] = len(blobs)
        storage_info["sample_blobs"] = [b.name for b in blobs[:5]] if blobs else []
        storage_info["client_type"] = str(type(azure_storage.blob_service_client))
    except Exception as e:
        storage_info["connection_test"] = "failed"
        storage_info["error"] = str(e)
    
    return {
        "status": "healthy",
        "service": "eagleview-pdf-processor",
        "storage": storage_info,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/health")
async def health_check():
    """Health check endpoint with detailed diagnostics."""
    try:
        settings = get_settings()
        diagnostics = {
            "status": "healthy",
            "service": "eagleview-pdf-processor",
            "environment": {
                "container_name": settings.azure_storage_container_name,
                "has_connection_string": bool(settings.azure_storage_connection_string),
            },
            "storage_tests": {}
        }
        
        # Test 1: Initialize storage client
        try:
            print("\nDEBUG: Testing storage client initialization")
            storage = AzureBlobStorage()
            diagnostics["storage_tests"]["init"] = "success"
        except Exception as e:
            print(f"DEBUG: Storage client initialization failed: {str(e)}")
            diagnostics["storage_tests"]["init"] = {"status": "failed", "error": str(e)}
            return diagnostics
        
        # Test 2: List container contents
        try:
            print("\nDEBUG: Testing container listing")
            container_client = storage.get_container_client()
            blobs = list(container_client.list_blobs())
            diagnostics["storage_tests"]["list_blobs"] = {
                "status": "success",
                "blob_count": len(blobs),
                "sample_blobs": [b.name for b in blobs[:5]]
            }
        except Exception as e:
            print(f"DEBUG: Container listing failed: {str(e)}")
            diagnostics["storage_tests"]["list_blobs"] = {"status": "failed", "error": str(e)}
        
        # Test 3: Try to read a specific blob
        try:
            print("\nDEBUG: Testing blob reading")
            # Try to read the most recent blob from the list
            if blobs:
                test_blob = blobs[0].name
                if test_blob.endswith('.json'):
                    json_data = await storage.get_json_data(test_blob)
                    diagnostics["storage_tests"]["read_blob"] = {
                        "status": "success",
                        "blob_name": test_blob,
                        "has_content": bool(json_data)
                    }
                else:
                    pdf_data = await storage.get_pdf(test_blob)
                    diagnostics["storage_tests"]["read_blob"] = {
                        "status": "success",
                        "blob_name": test_blob,
                        "content_size": len(pdf_data) if pdf_data else 0
                    }
            else:
                diagnostics["storage_tests"]["read_blob"] = {
                    "status": "skipped",
                    "reason": "no blobs found"
                }
        except Exception as e:
            print(f"DEBUG: Blob reading failed: {str(e)}")
            diagnostics["storage_tests"]["read_blob"] = {"status": "failed", "error": str(e)}
        
        return diagnostics
    except Exception as e:
        print(f"DEBUG: Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }

@app.get("/reports/{report_id}")
async def get_report(report_id: str):
    """Get report details by ID with enhanced error handling."""
    try:
        diagnostics = {
            "report_id": report_id,
            "steps": [],
            "errors": []
        }
        
        # Get the report data from Azure Blob Storage
        blob_name = f"{report_id}.json"
        try:
            print(f"\nDEBUG: Attempting to get JSON data for {blob_name}")
            diagnostics["steps"].append("Checking JSON blob")
            
            # First check if JSON blob exists
            try:
                json_blob_client = azure_storage.blob_service_client.get_blob_client(
                    container=azure_storage.container_name,
                    blob=blob_name
                )
                json_properties = json_blob_client.get_blob_properties()
                print(f"DEBUG: Found JSON blob. Size: {json_properties.size} bytes")
                diagnostics["steps"].append(f"Found JSON blob ({json_properties.size} bytes)")
            except Exception as e:
                error_msg = f"JSON blob not found or error: {str(e)}"
                print(f"DEBUG: {error_msg}")
                diagnostics["errors"].append(error_msg)
                raise
            
            # Try to get JSON data
            report_data = await azure_storage.get_json_data(blob_name)
            if report_data:
                print("DEBUG: Successfully retrieved JSON data")
                diagnostics["steps"].append("Retrieved JSON data successfully")
                return {
                    "success": True,
                    "data": report_data,
                    "diagnostics": diagnostics
                }
        except Exception as e:
            error_msg = f"Error getting JSON data: {str(e)}"
            print(f"DEBUG: {error_msg}")
            diagnostics["errors"].append(error_msg)
        
        # If JSON not found or error occurred, try to get from PDF processing
        pdf_blob_name = f"{report_id}.pdf"
        print(f"\nDEBUG: Attempting to get PDF data for {pdf_blob_name}")
        diagnostics["steps"].append("Checking PDF blob")
        
        try:
            # First check if PDF blob exists
            pdf_blob_client = azure_storage.blob_service_client.get_blob_client(
                container=azure_storage.container_name,
                blob=pdf_blob_name
            )
            pdf_properties = pdf_blob_client.get_blob_properties()
            print(f"DEBUG: Found PDF blob. Size: {pdf_properties.size} bytes")
            diagnostics["steps"].append(f"Found PDF blob ({pdf_properties.size} bytes)")
        except Exception as e:
            error_msg = f"PDF blob not found or error: {str(e)}"
            print(f"DEBUG: {error_msg}")
            diagnostics["errors"].append(error_msg)
            return {
                "success": False,
                "error": f"Report {report_id} not found",
                "diagnostics": diagnostics
            }
        
        # Try to get PDF data
        pdf_data = await azure_storage.get_pdf(pdf_blob_name)
        if not pdf_data:
            error_msg = "PDF data could not be retrieved"
            print(f"DEBUG: {error_msg}")
            diagnostics["errors"].append(error_msg)
            return {
                "success": False,
                "error": f"Report {report_id} not found",
                "diagnostics": diagnostics
            }
        
        print("DEBUG: Successfully retrieved PDF data, processing...")
        diagnostics["steps"].append("Retrieved PDF data successfully")
        
        # Process PDF and extract measurements
        try:
            measurements = await pdf_extractor.process_pdf(pdf_data)
            print("DEBUG: Successfully processed PDF")
            diagnostics["steps"].append("Processed PDF successfully")
        except Exception as e:
            error_msg = f"Error processing PDF: {str(e)}"
            print(f"DEBUG: {error_msg}")
            diagnostics["errors"].append(error_msg)
            raise
        
        # Format areas per pitch data
        areas_per_pitch = {}
        for key, value in measurements.items():
            if key.startswith('area_pitch_'):
                pitch = key.replace('area_pitch_', '').replace('_', '/')
                percentage = measurements.get(f'percentage_pitch_{pitch.replace("/", "_")}', {}).get('value', 0)
                areas_per_pitch[pitch] = {
                    'area': value.get('value', 0),
                    'percentage': percentage
                }
        
        # Create response data
        response_data = {
            "success": True,
            "filename": pdf_blob_name,
            "measurements": {
                "predominant_pitch": measurements.get("predominant_pitch"),
                "penetrations_area": measurements.get("penetrations_area"),
                "penetrations_perimeter": measurements.get("penetrations_perimeter"),
                "total_area": measurements.get("total_area"),
                "ridges": measurements.get("ridges"),
                "valleys": measurements.get("valleys"),
                "eaves": measurements.get("eaves"),
                "rakes": measurements.get("rakes"),
                "hips": measurements.get("hips"),
                "step_flashing": measurements.get("step_flashing"),
                "flashing": measurements.get("flashing"),
                "drip_edge": measurements.get("drip_edge")
            },
            "areas_per_pitch": areas_per_pitch,
            "address_info": {
                "street_address": measurements.get("street_address"),
                "city": measurements.get("city"),
                "state": measurements.get("state"),
                "zip_code": measurements.get("zip_code")
            },
            "total_area": measurements.get("total_area", {}).get("value"),
            "patterns_used": [
                "total_area", "predominant_pitch", "ridges", "valleys",
                "eaves", "rakes", "hips", "step_flashing", "flashing",
                "penetrations_area", "penetrations_perimeter", "drip_edge"
            ]
        }
        
        # Try to store the JSON data, but don't fail if it doesn't work
        try:
            print(f"\nDEBUG: Attempting to store JSON data as {blob_name}")
            diagnostics["steps"].append("Storing JSON data")
            await azure_storage.store_json_data(blob_name, response_data)
            print("DEBUG: Successfully stored JSON data")
            diagnostics["steps"].append("Stored JSON data successfully")
        except Exception as e:
            error_msg = f"Error storing JSON data: {str(e)}"
            print(f"DEBUG: {error_msg}")
            diagnostics["errors"].append(error_msg)
            # Continue even if storing JSON fails
        
        return {
            "success": True,
            "data": response_data,
            "diagnostics": diagnostics
        }
    except Exception as e:
        print(f"DEBUG: Unexpected error: {str(e)}")
        diagnostics["errors"].append(f"Unexpected error: {str(e)}")
        return {
            "success": False,
            "error": f"Error retrieving report: {str(e)}",
            "diagnostics": diagnostics
        }

@app.post("/process-pdf")
async def process_pdf(
    file: UploadFile,
    report_id: str = None,
) -> ProcessingResponse:
    """Process an EagleView PDF report and extract measurements."""
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    try:
        # Generate report_id if not provided
        if not report_id:
            timestamp = int(time.time())
            report_id = f"report_{timestamp}"
        
        print(f"Processing report with ID: {report_id}")
        
        # Read file contents
        contents = await file.read()
        
        # Upload file to Azure Blob Storage with report ID as name
        pdf_blob_name = f"{report_id}.pdf"
        print(f"Uploading PDF as: {pdf_blob_name}")
        file_url = await azure_storage.upload_pdf(contents, pdf_blob_name)
        
        # Extract measurements and address
        print("\nDEBUG: Starting PDF processing")
        measurements = await pdf_extractor.process_pdf(contents)
        
        # Debug logging for measurements
        print("\nDEBUG: Raw measurements from PDF:")
        for key, value in measurements.items():
            print(f"{key}: {value}")
        
        # Format areas per pitch data
        print("\nDEBUG: Starting areas per pitch formatting")
        areas_per_pitch = {}
        for key, value in measurements.items():
            print(f"Checking key: {key}")
            if key.startswith('area_pitch_'):
                pitch = key.replace('area_pitch_', '').replace('_', '/')
                print(f"Found pitch: {pitch}")
                percentage_key = f"percentage_pitch_{pitch.replace('/', '_')}"
                print(f"Looking for percentage with key: {percentage_key}")
                percentage = measurements.get(percentage_key, {}).get('value', 0)
                print(f"Found percentage: {percentage}")
                areas_per_pitch[pitch] = {
                    'area': value.get('value', 0),
                    'percentage': percentage
                }
                print(f"Added to areas_per_pitch: {pitch} -> {areas_per_pitch[pitch]}")
        
        print("\nDEBUG: Final areas_per_pitch:")
        print(areas_per_pitch)
        
        # Create the response in the exact format needed
        response_data = {
            "success": True,
            "filename": file.filename,
            "measurements": {
                "predominant_pitch": measurements.get("predominant_pitch"),
                "penetrations_area": measurements.get("penetrations_area"),
                "penetrations_perimeter": measurements.get("penetrations_perimeter"),
                "total_area": measurements.get("total_area"),
                "ridges": measurements.get("ridges"),
                "valleys": measurements.get("valleys"),
                "eaves": measurements.get("eaves"),
                "rakes": measurements.get("rakes"),
                "hips": measurements.get("hips"),
                "step_flashing": measurements.get("step_flashing"),
                "flashing": measurements.get("flashing"),
                "drip_edge": measurements.get("drip_edge")
            },
            "areas_per_pitch": areas_per_pitch,
            "address_info": {
                "street_address": measurements.get("street_address"),
                "city": measurements.get("city"),
                "state": measurements.get("state"),
                "zip_code": measurements.get("zip_code")
            },
            "total_area": measurements.get("total_area", {}).get("value"),
            "patterns_used": [
                "total_area", "predominant_pitch", "ridges", "valleys",
                "eaves", "rakes", "hips", "step_flashing", "flashing",
                "penetrations_area", "penetrations_perimeter", "drip_edge"
            ]
        }
        
        print("\nDEBUG: Final response data:")
        print(response_data)
        
        # Store the full data for future retrieval
        json_blob_name = f"{report_id}.json"
        print(f"Storing JSON data as: {json_blob_name}")
        await azure_storage.store_json_data(json_blob_name, response_data)
        
        return ProcessingResponse(**response_data)
        
    except Exception as e:
        print(f"\nDEBUG: Error in process_pdf: {str(e)}")
        error_response = ProcessingResponse(
            success=False,
            filename=file.filename,
            measurements={},
            error=str(e)
        )
        return error_response

@app.post("/test")
async def test_pdf(file: UploadFile):
    """Test endpoint to verify PDF extraction."""
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    try:
        print("\nDEBUG: Starting PDF test processing")
        contents = await file.read()
        
        # Upload file to Azure Blob Storage for testing
        file_url = await azure_storage.upload_pdf(contents, f"test_{file.filename}")
        print(f"DEBUG: Uploaded test file to: {file_url}")
        
        # Process the PDF with debug logging
        print("\nDEBUG: Starting PDF measurement extraction")
        result = await pdf_extractor.process_pdf(contents)
        print("\nDEBUG: Measurement extraction complete")
        print(f"DEBUG: Areas per pitch data: {result.get('areas_per_pitch', {})}")
        
        return {
            "success": True,
            "filename": file.filename,
            "file_url": file_url,
            "measurements": result,
            "patterns_used": list(pdf_extractor.patterns.keys())
        }
    except Exception as e:
        print(f"DEBUG: Error in test_pdf: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "filename": file.filename
        }

@app.get("/reports")
async def list_reports():
    """List all reports with their measurements and metadata.
    Returns a list of all processed PDF reports with their extracted data."""
    try:
        # Get all PDF files from the container
        container_client = azure_storage.get_container_client()
        
        # List all blobs in the container
        print("DEBUG: Listing all blobs in container...")
        all_blobs = []
        try:
            blob_list = container_client.list_blobs()
            for blob in blob_list:
                print(f"DEBUG: Found blob: {blob.name}")
                all_blobs.append(blob)
        except Exception as e:
            print(f"DEBUG: Error listing blobs: {str(e)}")
            return {
                "success": False,
                "error": f"Error listing blobs: {str(e)}",
                "diagnostics": {
                    "container_name": azure_storage.container_name,
                    "has_connection_string": bool(azure_storage.connection_string)
                }
            }
        
        print(f"DEBUG: Found total {len(all_blobs)} blobs")
        
        # Filter for PDF files and get their corresponding JSON data
        reports = []
        for blob in all_blobs:
            print(f"DEBUG: Processing blob: {blob.name}")
            if blob.name.endswith('.pdf'):
                report_id = blob.name.replace('.pdf', '')
                print(f"DEBUG: Found PDF file with report_id: {report_id}")
                try:
                    # Try to get the JSON data for this report
                    json_blob_name = f"{report_id}.json"
                    print(f"DEBUG: Checking for JSON data: {json_blob_name}")
                    
                    # First check if JSON blob exists
                    try:
                        json_blob_client = azure_storage.blob_service_client.get_blob_client(
                            container=azure_storage.container_name,
                            blob=json_blob_name
                        )
                        json_properties = json_blob_client.get_blob_properties()
                        print(f"DEBUG: Found JSON blob. Size: {json_properties.size} bytes")
                    except Exception as e:
                        print(f"DEBUG: JSON blob not found or error: {str(e)}")
                        reports.append({
                            "id": report_id,
                            "filename": blob.name,
                            "created_at": blob.creation_time.isoformat(),
                            "json_status": f"error: {str(e)}"
                        })
                        continue
                    
                    # Try to get JSON data
                    json_data = await azure_storage.get_json_data(json_blob_name)
                    if json_data:
                        print(f"DEBUG: Successfully read JSON data for report {report_id}")
                        reports.append({
                            "id": report_id,
                            "filename": json_data.get("filename"),
                            "created_at": blob.creation_time.isoformat(),
                            "measurements": json_data.get("measurements", {}),
                            "total_area": json_data.get("total_area"),
                            "address_info": json_data.get("address_info", {}),
                            "areas_per_pitch": json_data.get("areas_per_pitch", {})
                        })
                    else:
                        print(f"DEBUG: No JSON data found for report {report_id}")
                        reports.append({
                            "id": report_id,
                            "filename": blob.name,
                            "created_at": blob.creation_time.isoformat(),
                            "json_status": "no data"
                        })
                except Exception as e:
                    print(f"DEBUG: Error processing JSON for report {report_id}: {str(e)}")
                    reports.append({
                        "id": report_id,
                        "filename": blob.name,
                        "created_at": blob.creation_time.isoformat(),
                        "error": str(e)
                    })
        
        # Sort by creation time, newest first
        reports.sort(key=lambda x: x["created_at"], reverse=True)
        
        print(f"DEBUG: Returning {len(reports)} reports")
        return {
            "success": True,
            "reports": reports,
            "diagnostics": {
                "total_blobs": len(all_blobs),
                "pdf_count": len([b for b in all_blobs if b.name.endswith('.pdf')]),
                "json_count": len([b for b in all_blobs if b.name.endswith('.json')]),
                "container_name": azure_storage.container_name,
                "has_connection_string": bool(azure_storage.connection_string)
            }
        }
    except Exception as e:
        print(f"DEBUG: Error listing reports: {str(e)}")
        return {
            "success": False,
            "error": f"Error listing reports: {str(e)}",
            "diagnostics": {
                "container_name": azure_storage.container_name,
                "has_connection_string": bool(azure_storage.connection_string)
            }
        }

@app.get("/storage-test/{report_id}")
async def test_storage(report_id: str):
    """Test storage operations for a specific report."""
    try:
        print(f"\nDEBUG: Testing storage for report {report_id}")
        results = {
            "report_id": report_id,
            "tests": {}
        }
        
        # Test 1: Check if JSON exists
        json_blob_name = f"{report_id}.json"
        print(f"DEBUG: Testing JSON blob: {json_blob_name}")
        try:
            blob_client = azure_storage.blob_service_client.get_blob_client(
                container=azure_storage.container_name,
                blob=json_blob_name
            )
            properties = blob_client.get_blob_properties()
            results["tests"]["json_exists"] = {
                "status": "success",
                "size": properties.size,
                "last_modified": properties.last_modified.isoformat()
            }
        except Exception as e:
            print(f"DEBUG: Error checking JSON blob: {str(e)}")
            results["tests"]["json_exists"] = {
                "status": "failed",
                "error": str(e)
            }
        
        # Test 2: Check if PDF exists
        pdf_blob_name = f"{report_id}.pdf"
        print(f"DEBUG: Testing PDF blob: {pdf_blob_name}")
        try:
            blob_client = azure_storage.blob_service_client.get_blob_client(
                container=azure_storage.container_name,
                blob=pdf_blob_name
            )
            properties = blob_client.get_blob_properties()
            results["tests"]["pdf_exists"] = {
                "status": "success",
                "size": properties.size,
                "last_modified": properties.last_modified.isoformat()
            }
        except Exception as e:
            print(f"DEBUG: Error checking PDF blob: {str(e)}")
            results["tests"]["pdf_exists"] = {
                "status": "failed",
                "error": str(e)
            }
        
        # Test 3: Try to read JSON content
        if results["tests"].get("json_exists", {}).get("status") == "success":
            print("DEBUG: Testing JSON content reading")
            try:
                json_data = await azure_storage.get_json_data(json_blob_name)
                results["tests"]["json_content"] = {
                    "status": "success",
                    "has_content": bool(json_data),
                    "content_preview": str(json_data)[:100] if json_data else None
                }
            except Exception as e:
                print(f"DEBUG: Error reading JSON content: {str(e)}")
                results["tests"]["json_content"] = {
                    "status": "failed",
                    "error": str(e)
                }
        
        # Test 4: Try to read PDF content
        if results["tests"].get("pdf_exists", {}).get("status") == "success":
            print("DEBUG: Testing PDF content reading")
            try:
                pdf_data = await azure_storage.get_pdf(pdf_blob_name)
                results["tests"]["pdf_content"] = {
                    "status": "success",
                    "content_size": len(pdf_data) if pdf_data else 0
                }
            except Exception as e:
                print(f"DEBUG: Error reading PDF content: {str(e)}")
                results["tests"]["pdf_content"] = {
                    "status": "failed",
                    "error": str(e)
                }
        
        return results
    except Exception as e:
        print(f"DEBUG: Storage test failed: {str(e)}")
        return {
            "status": "failed",
            "error": str(e)
        }

@app.get("/test-storage")
async def test_storage_connection():
    """Test the Azure Blob Storage connection."""
    try:
        settings = get_settings()
        results = {
            "environment": {
                "container_name": settings.azure_storage_container_name,
                "has_connection_string": bool(settings.azure_storage_connection_string),
            },
            "tests": {}
        }
        
        # Test 1: Initialize storage client
        try:
            print("\nDEBUG: Testing storage client initialization")
            storage = AzureBlobStorage()
            results["tests"]["init"] = {
                "status": "success",
                "client_type": str(type(storage.blob_service_client))
            }
        except Exception as e:
            print(f"DEBUG: Storage client initialization failed: {str(e)}")
            results["tests"]["init"] = {
                "status": "failed",
                "error": str(e)
            }
            return results
        
        # Test 2: List container contents
        try:
            print("\nDEBUG: Testing container listing")
            container_client = storage.get_container_client()
            blobs = list(container_client.list_blobs())
            results["tests"]["list_blobs"] = {
                "status": "success",
                "blob_count": len(blobs),
                "sample_blobs": [b.name for b in blobs[:5]] if blobs else []
            }
        except Exception as e:
            print(f"DEBUG: Container listing failed: {str(e)}")
            results["tests"]["list_blobs"] = {
                "status": "failed",
                "error": str(e)
            }
        
        # Test 3: Try to read a specific blob
        if blobs:
            try:
                print("\nDEBUG: Testing blob reading")
                test_blob = blobs[0].name
                blob_client = storage.blob_service_client.get_blob_client(
                    container=storage.container_name,
                    blob=test_blob
                )
                properties = blob_client.get_blob_properties()
                results["tests"]["read_blob"] = {
                    "status": "success",
                    "blob_name": test_blob,
                    "size": properties.size,
                    "last_modified": properties.last_modified.isoformat()
                }
            except Exception as e:
                print(f"DEBUG: Blob reading failed: {str(e)}")
                results["tests"]["read_blob"] = {
                    "status": "failed",
                    "error": str(e)
                }
        else:
            results["tests"]["read_blob"] = {
                "status": "skipped",
                "reason": "no blobs found"
            }
        
        return results
    except Exception as e:
        print(f"DEBUG: Storage test failed: {str(e)}")
        return {
            "status": "failed",
            "error": str(e)
        }

# Note: We don't need the if __name__ == "__main__" block anymore
# as we're using Gunicorn/Uvicorn for deployment 