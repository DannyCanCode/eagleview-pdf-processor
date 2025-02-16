from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import fitz
import time
from datetime import datetime
from pdf_processor.extractor import create_extractor
from pdf_processor.models import ProcessingResponse
from pdf_processor.storage import AzureBlobStorage
from pdf_processor.database import Database
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
    """Root endpoint."""
    return {"status": "healthy", "service": "eagleview-pdf-processor"}

@app.get("/health")
async def health_check():
    """Health check endpoint that frontend expects."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "eagleview-pdf-processor"
    }

@app.get("/reports/{report_id}")
async def get_report(report_id: str):
    """Get report details by ID."""
    try:
        # Get the report data from Azure Blob Storage
        blob_name = f"{report_id}.json"
        try:
            report_data = await azure_storage.get_json_data(blob_name)
            if not report_data:
                raise HTTPException(status_code=404, detail=f"Report {report_id} not found")
        except Exception as e:
            # If JSON not found, try to get from PDF processing
            pdf_blob_name = f"{report_id}.pdf"
            pdf_data = await azure_storage.get_pdf(pdf_blob_name)
            if not pdf_data:
                raise HTTPException(status_code=404, detail=f"Report {report_id} not found")
            
            # Process PDF and extract measurements
            measurements = await pdf_extractor.process_pdf(pdf_data)
            
            # Store the measurements for future requests
            report_data = {
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
                "areas_per_pitch": measurements.get("areas_per_pitch", {}),
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
            await azure_storage.store_json_data(blob_name, report_data)

        return report_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving report: {str(e)}")

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
            
        # Read file contents
        contents = await file.read()
        
        # Upload file to Azure Blob Storage with consistent naming
        pdf_blob_name = f"{report_id}.pdf"
        file_url = await azure_storage.upload_pdf(contents, pdf_blob_name)
        
        # Extract measurements and address
        measurements = await pdf_extractor.process_pdf(contents)
        
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
            "areas_per_pitch": measurements.get("areas_per_pitch", {}),
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
        
        # Store the full data for future retrieval with consistent naming
        json_blob_name = f"{report_id}.json"
        await azure_storage.store_json_data(json_blob_name, response_data)
        
        return ProcessingResponse(**response_data)
        
    except Exception as e:
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
        contents = await file.read()
        
        # Upload file to Azure Blob Storage for testing
        file_url = await azure_storage.upload_pdf(contents, f"test_{file.filename}")
        
        # Process the PDF
        result = await pdf_extractor.process_pdf(contents)
        
        return {
            "success": True,
            "filename": file.filename,
            "file_url": file_url,
            "measurements": result,
            "patterns_used": list(pdf_extractor.patterns.keys())
        }
    except Exception as e:
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
        blobs = container_client.list_blobs()
        
        # Filter for PDF files and get their corresponding JSON data
        reports = []
        for blob in blobs:
            if blob.name.endswith('.pdf'):
                report_id = blob.name.replace('.pdf', '')
                try:
                    # Try to get the JSON data for this report
                    json_data = await azure_storage.get_json_data(f"{report_id}.json")
                    if json_data:
                        reports.append({
                            "id": report_id,
                            "filename": json_data.get("filename"),
                            "created_at": blob.creation_time.isoformat(),
                            "measurements": json_data.get("measurements", {}),
                            "total_area": json_data.get("total_area"),
                            "address_info": json_data.get("address_info", {})
                        })
                except:
                    # If JSON not found, add basic info
                    reports.append({
                        "id": report_id,
                        "filename": blob.name,
                        "created_at": blob.creation_time.isoformat()
                    })
        
        # Sort by creation time, newest first
        reports.sort(key=lambda x: x["created_at"], reverse=True)
        
        return {
            "success": True,
            "reports": reports
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing reports: {str(e)}")

# Note: We don't need the if __name__ == "__main__" block anymore
# as we're using Gunicorn/Uvicorn for deployment 