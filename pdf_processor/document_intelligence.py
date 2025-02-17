import re
from azure.core.credentials import AzureKeyCredential
from azure.ai.formrecognizer import DocumentAnalysisClient
from pdf_processor.config import get_settings

class DocumentIntelligence:
    def __init__(self):
        settings = get_settings()
        self.endpoint = settings.document_intelligence_endpoint
        self.key = settings.document_intelligence_key
        self.client = DocumentAnalysisClient(
            endpoint=self.endpoint, 
            credential=AzureKeyCredential(self.key)
        )

    def _extract_areas_per_pitch(self, result):
        """Extract areas per pitch from tables and content."""
        areas_per_pitch = {}
        
        # First try to extract from tables
        for table in result.tables:
            # Check if this is the areas per pitch table
            is_pitch_table = False
            for cell in table.cells:
                if 'Areas per Pitch' in cell.content:
                    is_pitch_table = True
                    break
            
            if is_pitch_table:
                # Process the table row by row
                current_row = -1
                pitch = None
                area = None
                percentage = None
                
                for cell in table.cells:
                    if cell.row_index != current_row:
                        # New row - process previous row if complete
                        if pitch and area is not None and percentage is not None:
                            areas_per_pitch[pitch] = {
                                'area': area,
                                'percentage': percentage
                            }
                        # Reset for new row
                        current_row = cell.row_index
                        pitch = None
                        area = None
                        percentage = None
                    
                    # Try to identify cell type and extract value
                    content = cell.content.strip()
                    if '/' in content and all(part.isdigit() for part in content.split('/')):
                        pitch = content
                    elif content.endswith('%'):
                        try:
                            percentage = float(content.rstrip('%'))
                        except ValueError:
                            continue
                    elif content.replace(',', '').replace('.', '').isdigit():
                        try:
                            area = float(content.replace(',', ''))
                        except ValueError:
                            continue
        
        # If no table data, try to extract from content
        if not areas_per_pitch:
            # Look for areas per pitch section in content
            content = result.content
            section_match = re.search(r'Areas\s+per\s+Pitch.*?\n(.*?)(?=\n\s*\n|\Z)', content, re.DOTALL | re.IGNORECASE)
            if section_match:
                section_text = section_match.group(1)
                lines = [line.strip() for line in section_text.split('\n') if line.strip()]
                
                # Process lines in groups of 3 (pitch, area, percentage)
                for i in range(0, len(lines), 3):
                    if i + 2 < len(lines):
                        pitch_line = lines[i]
                        area_line = lines[i + 1]
                        percentage_line = lines[i + 2]
                        
                        # Validate and extract pitch
                        if '/' in pitch_line and all(part.isdigit() for part in pitch_line.split('/')):
                            pitch = pitch_line
                            
                            # Extract area
                            try:
                                area = float(area_line.replace(',', ''))
                            except ValueError:
                                continue
                            
                            # Extract percentage
                            if percentage_line.endswith('%'):
                                try:
                                    percentage = float(percentage_line.rstrip('%'))
                                    areas_per_pitch[pitch] = {
                                        'area': area,
                                        'percentage': percentage
                                    }
                                except ValueError:
                                    continue
        
        return areas_per_pitch

    async def analyze_document(self, document_bytes):
        """
        Analyze a document using Azure Document Intelligence
        
        Args:
            document_bytes (bytes): The document content in bytes
            
        Returns:
            dict: Extracted information from the document
        """
        try:
            poller = self.client.begin_analyze_document("prebuilt-document", document_bytes)
            result = poller.result()
            
            # Extract key-value pairs
            key_value_pairs = {}
            if hasattr(result, 'key_value_pairs'):
                for kv_pair in result.key_value_pairs:
                    if kv_pair.key and kv_pair.value:
                        # Clean up the key-value pairs
                        key = kv_pair.key.content.strip()
                        value = kv_pair.value.content.strip()
                        
                        # Remove leading equals signs and clean up values
                        if value.startswith('='):
                            value = value[1:].strip()
                        
                        key_value_pairs[key] = value
            
            # Extract areas per pitch
            areas_per_pitch = self._extract_areas_per_pitch(result)
            
            # Extract tables (excluding areas per pitch table for clarity)
            tables = []
            if hasattr(result, 'tables'):
                for table in result.tables:
                    # Skip the areas per pitch table
                    is_pitch_table = False
                    for cell in table.cells:
                        if 'Areas per Pitch' in cell.content:
                            is_pitch_table = True
                            break
                    
                    if not is_pitch_table:
                        table_data = []
                        for cell in table.cells:
                            table_data.append({
                                'text': cell.content,
                                'row_index': cell.row_index,
                                'column_index': cell.column_index
                            })
                        tables.append(table_data)
            
            # Structure the measurements
            measurements = {}
            for key, value in key_value_pairs.items():
                if any(term in key.lower() for term in ['area', 'pitch', 'ridge', 'valley', 'eave', 'rake', 'hip', 'flashing']):
                    # Clean up measurement values
                    if 'sq ft' in value:
                        value = value.replace('sq ft', '').strip()
                    if 'ft' in value:
                        value = value.replace('ft', '').strip()
                    measurements[key] = value
            
            # Get the raw content
            content = result.content if hasattr(result, 'content') else ""
            
            return {
                'report_info': {k: v for k, v in key_value_pairs.items() if any(term in k.lower() for term in ['report', 'order', 'date', 'address'])},
                'measurements': measurements,
                'areas_per_pitch': areas_per_pitch,
                'raw_analysis': {
                    'key_value_pairs': key_value_pairs,
                    'tables': tables,
                    'content': content
                }
            }
            
        except Exception as e:
            import traceback
            error_msg = f"Error analyzing document: {str(e)}\n{traceback.format_exc()}"
            raise Exception(error_msg) 