import re
import logging
from typing import Dict, List, Optional, Tuple, Union
import fitz  # PyMuPDF

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RoofingMeasurement:
    """Represents a single roofing measurement with value, unit, and metadata."""
    def __init__(self, value: Union[float, str], unit: str, count: Optional[int] = None):
        self.value = value  # Can be float or string (for pitch ratios)
        self.unit = unit
        self.count = count

    def to_dict(self) -> Dict:
        result = {"value": self.value, "unit": self.unit}
        if self.count is not None:
            result["count"] = self.count
        return result

class PDFMeasurementExtractor:
    """Extracts measurements from roofing PDF reports."""
    
    def __init__(self):
        # Define all measurement patterns
        self.patterns = {
            'total_area': re.compile(r'Total\s+Area\s*\(All\s+Pitches\)\s*=\s*(\d+,?\d*)\s*sq\s*ft', re.IGNORECASE),
            'predominant_pitch': re.compile(r'Predominant\s+Pitch\s*=\s*(\d+/\d+)', re.IGNORECASE),
            'ridges': re.compile(r'(?:Total\s+)?Ridges\s*=\s*(\d+)\s*ft\s*\((\d+)\s*Ridges?\)', re.IGNORECASE),
            'valleys': re.compile(r'(?:Total\s+)?Valleys\s*=\s*(\d+)\s*ft\s*\((\d+)\s*Valleys?\)', re.IGNORECASE),
            'eaves': re.compile(r'(?:Total\s+)?Eaves(?:/Starter)?[‡†]?\s*=\s*(\d+)\s*ft\s*\((\d+)\s*Eaves?\)', re.IGNORECASE),
            'rakes': re.compile(r'(?:Total\s+)?Rakes[†]?\s*=\s*(\d+)\s*ft\s*\((\d+)\s*Rakes?\)', re.IGNORECASE),
            'hips': re.compile(r'(?:Total\s+)?Hips\s*=\s*(\d+)\s*ft\s*\((\d+)\s*Hips?\)\.?', re.IGNORECASE),
            'step_flashing': re.compile(r'(?:Total\s+)?Step\s+flashing\s*=\s*(\d+)\s*ft\s*\((\d+)\s*Lengths?\)', re.IGNORECASE),
            'flashing': re.compile(r'(?:^|\n)\s*Flashing\s*=\s*(\d+)\s*ft\s*\((\d+)\s*Lengths?\)', re.IGNORECASE),
            'penetrations_area': re.compile(r'Total\s+Penetrations\s+Area\s*=\s*(\d+)\s*sq\s*ft', re.IGNORECASE),
            'penetrations_perimeter': re.compile(r'Total\s+Penetrations\s+Perimeter\s*=\s*(\d+)\s*ft', re.IGNORECASE),
            'drip_edge': re.compile(r'Drip\s+Edge\s*\(Eaves\s*\+\s*Rakes\)\s*=\s*(\d+)\s*ft\s*\((\d+)\s*Lengths?\)', re.IGNORECASE),
        }
        # Add address pattern
        self.address_pattern = re.compile(r'([^,]+),\s*([^,]+),\s*([A-Z]{2})\s+(\d{5}(?:-\d{4})?)')

    def _clean_value(self, value: str) -> float:
        """Clean and convert measurement value to float."""
        return float(value.replace(',', '').replace(' ', ''))

    def _extract_count(self, text: str, feature: str) -> Optional[int]:
        """Extract count of features (e.g., number of ridges)."""
        pattern = re.compile(rf'\((\d+)\s*{feature}s?\)', re.IGNORECASE)
        match = pattern.search(text)
        return int(match.group(1)) if match else None

    async def extract_text(self, doc: fitz.Document) -> Tuple[str, List]:
        """Extract text and blocks from all pages of the PDF."""
        full_text = []
        all_blocks = []
        for page in doc:
            text = page.get_text("text")
            blocks = page.get_text("blocks")
            full_text.append(text)
            all_blocks.extend(blocks)
            
        return "\n".join(full_text), all_blocks

    def _find_all_measurements(self, pattern: re.Pattern, text: str, page_num: int, measure_type: str = None) -> List[Dict]:
        """Find all occurrences of a measurement in text."""
        measurements = []
        for match in pattern.finditer(text):
            value = match.group(1)
            if not value:
                continue
                
            measurement = {
                "value": value if measure_type == 'predominant_pitch' else self._clean_value(value),
                "match_start": match.start(),
                "match_end": match.end(),
                "page": page_num
            }
            
            # Extract count if available
            if len(match.groups()) > 1 and match.group(2):
                measurement["count"] = int(match.group(2))
                
            measurements.append(measurement)
        return measurements

    def _consolidate_measurements(self, found_measurements: List[Dict]) -> Dict:
        """Consolidate multiple measurements into a single total with count."""
        if not found_measurements:
            return None
            
        # Get the unique values
        unique_values = set(m['value'] for m in found_measurements)
        
        # If there's only one unique value, use that
        if len(unique_values) == 1:
            total_value = found_measurements[0]['value']
        else:
            # Sum up all values if they're different
            total_value = sum(m['value'] for m in found_measurements)
            
        # Get the maximum count if any measurement has a count
        max_count = max((m.get('count', 0) for m in found_measurements), default=None)
        
        # If no count was found but we have multiple measurements, use the count of measurements
        if max_count is None and len(found_measurements) > 1:
            max_count = len(unique_values)  # Use unique values count to avoid counting duplicates
            
        return {
            "value": total_value,
            "count": max_count if max_count else None,
            "page": found_measurements[0]['page']
        }

    def _parse_areas_per_pitch(self, text: str, blocks: List) -> Dict[str, Dict[str, float]]:
        """Parse the Areas per Pitch section using block structure."""
        areas_per_pitch = {}
        
        # First find the section header block
        header_found = False
        table_blocks = []
        
        for block in blocks:
            block_text = block[4]  # Text content is at index 4
            logger.info(f"Processing block: {block_text}")
            
            if 'Areas per Pitch' in block_text:
                header_found = True
                logger.info("Found Areas per Pitch header")
                continue
                
            if header_found and ('Structure Complexity' in block_text or 'Waste Calculation' in block_text):
                break
                
            if header_found:
                table_blocks.append(block_text)
        
        if not table_blocks:
            logger.warning("No table blocks found after Areas per Pitch header")
            return areas_per_pitch
            
        logger.info(f"Found table blocks: {table_blocks}")
        
        # Find the blocks containing pitches, areas, and percentages
        pitches = []
        areas = []
        percentages = []
        
        for block in table_blocks:
            # Split block into lines
            lines = block.strip().split('\n')
            
            # Check each line
            for line in lines:
                if re.match(r'\d+/\d+', line):
                    pitches.extend(re.findall(r'\d+/\d+', line))
                elif re.match(r'\d+(?:,\d*)?\.?\d*$', line):
                    areas.append(self._clean_value(line))
                elif re.match(r'\d+\.?\d*%', line):
                    percentages.append(float(line.rstrip('%')))
        
        logger.info(f"Found pitches: {pitches}")
        logger.info(f"Found areas: {areas}")
        logger.info(f"Found percentages: {percentages}")
        
        # Combine the data
        for i in range(min(len(pitches), len(areas), len(percentages))):
            areas_per_pitch[pitches[i]] = {
                'area': areas[i],
                'percentage': percentages[i]
            }
            logger.info(f"Added pitch data: {pitches[i]} -> area={areas[i]}, percentage={percentages[i]}%")
        
        # Validate the data
        if areas_per_pitch:
            total_percentage = sum(data['percentage'] for data in areas_per_pitch.values())
            total_area = sum(data['area'] for data in areas_per_pitch.values())
            logger.info(f"Total percentage: {total_percentage}%, Total area: {total_area}")
            
            if not (99.0 <= total_percentage <= 101.0):
                logger.warning(f"Total percentage {total_percentage}% is not approximately 100%")
        
        return areas_per_pitch

    def _parse_suggested_waste(self, text: str) -> Optional[Dict[str, float]]:
        """Parse suggested waste section."""
        # Try to find the Waste Calculation section
        waste_section = re.search(r'Waste\s+Calculation.*?(?=Additional|\Z)', text, re.DOTALL | re.IGNORECASE)
        if not waste_section:
            logger.warning("Could not find Waste Calculation section")
            return None
            
        waste_text = waste_section.group(0)
        logger.info(f"Found waste calculation section:\n{waste_text}")
        
        # Look for the Suggested row
        # First find the row with percentages
        percentages = re.findall(r'(\d+)%', waste_text)
        # Find the row with areas
        areas = re.findall(r'Area\s*\(Sq\s*ft\)\s*(\d+(?:,\d*)?)', waste_text)
        # Find the row with squares
        squares = re.findall(r'Squares\s*\*\s*(\d+\.\d+)', waste_text)
        
        logger.info(f"Found waste percentages: {percentages}")
        logger.info(f"Found waste areas: {areas}")
        logger.info(f"Found waste squares: {squares}")
        
        # Look for "Suggested" marker to find which index to use
        suggested_index = None
        lines = waste_text.split('\n')
        for i, line in enumerate(lines):
            if 'Suggested' in line:
                # Count non-empty lines before this to find the index
                suggested_index = sum(1 for l in lines[:i] if l.strip() and any(c.isdigit() for c in l))
                break
        
        if suggested_index is not None and suggested_index < len(percentages):
            try:
                percentage = float(percentages[suggested_index])
                area = float(areas[suggested_index].replace(',', ''))
                squares = float(squares[suggested_index])
                
                waste_data = {
                    'percentage': percentage,
                    'area': area,
                    'squares': squares
                }
                logger.info(f"Found suggested waste: {waste_data}")
                return waste_data
            except (ValueError, IndexError) as e:
                logger.error(f"Error parsing suggested waste values: {e}")
                return None
        else:
            logger.warning("Could not find suggested waste values in table")
            
        return None

    def _extract_address(self, text: str) -> Dict[str, str]:
        """Extract address components from text."""
        match = self.address_pattern.search(text)
        if match:
            return {
                'street_address': match.group(1).strip(),
                'city': match.group(2).strip(),
                'state': match.group(3).strip(),
                'zip_code': match.group(4).strip()
            }
        return {}

    async def process_pdf(self, pdf_content: bytes) -> Dict[str, Union[RoofingMeasurement, Dict]]:
        """Process PDF content and extract all measurements."""
        try:
            measurements = {}
            
            with fitz.open(stream=pdf_content, filetype="pdf") as doc:
                text, blocks = await self.extract_text(doc)
                page_num = 1  # Default to page 1 for now
                
                logger.info("Starting measurement extraction")
                
                # Extract address from first page
                address_info = self._extract_address(text)
                if address_info:
                    measurements.update({
                        'street_address': address_info.get('street_address'),
                        'city': address_info.get('city'),
                        'state': address_info.get('state'),
                        'zip_code': address_info.get('zip_code')
                    })
                
                # Extract standard measurements
                for measure_type, pattern in self.patterns.items():
                    found_measurements = self._find_all_measurements(pattern, text, page_num, measure_type)
                    if found_measurements:
                        logger.info(f"Found {measure_type}: {found_measurements}")
                    else:
                        logger.warning(f"No measurements found for {measure_type}")
                    
                    if found_measurements:
                        if measure_type == 'predominant_pitch':
                            m = found_measurements[0]
                            measurements[measure_type] = RoofingMeasurement(
                                m['value'],
                                'ratio'
                            )
                        else:
                            consolidated = self._consolidate_measurements(found_measurements)
                            if consolidated:
                                unit = 'sq_ft' if 'area' in measure_type else 'ft'
                                measurements[measure_type] = RoofingMeasurement(
                                    consolidated['value'],
                                    unit,
                                    consolidated['count']
                                )
                
                # Extract areas per pitch using block structure
                areas_per_pitch = self._parse_areas_per_pitch(text, blocks)
                if areas_per_pitch:
                    logger.info(f"Found areas per pitch: {areas_per_pitch}")
                    for pitch, data in areas_per_pitch.items():
                        pitch_key = f"area_pitch_{pitch.replace('/', '_')}"
                        measurements[pitch_key] = RoofingMeasurement(data['area'], 'sq_ft')
                        percentage_key = f"percentage_pitch_{pitch.replace('/', '_')}"
                        measurements[percentage_key] = RoofingMeasurement(data['percentage'], 'percent')
                else:
                    logger.warning("No areas per pitch found")
                
                # Extract suggested waste
                suggested_waste = self._parse_suggested_waste(text)
                if suggested_waste:
                    logger.info(f"Found suggested waste: {suggested_waste}")
                    measurements['suggested_waste_percentage'] = RoofingMeasurement(
                        suggested_waste['percentage'], 'percent'
                    )
                    measurements['suggested_waste_area'] = RoofingMeasurement(
                        suggested_waste['area'], 'sq_ft'
                    )
                    measurements['suggested_waste_squares'] = RoofingMeasurement(
                        suggested_waste['squares'], 'squares'
                    )
                else:
                    logger.warning("No suggested waste found")
                
                # Validate total area (required)
                if 'total_area' not in measurements:
                    logger.error("Required measurement 'total_area' not found")
                    raise ValueError("Total Roof Area measurement is required but not found")
                
                # Convert measurements to dictionary format
                return {
                    k: v.to_dict() if isinstance(v, RoofingMeasurement) else v
                    for k, v in measurements.items()
                }
        
        except Exception as e:
            logger.error(f"Error processing PDF: {str(e)}")
            raise

def create_extractor() -> PDFMeasurementExtractor:
    """Factory function to create a new PDFMeasurementExtractor instance."""
    return PDFMeasurementExtractor() 