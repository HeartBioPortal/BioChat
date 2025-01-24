import os
import logging
import pytesseract
import pdfplumber
from pdf2image import convert_from_path
from tqdm import tqdm
from typing import Dict, List, Union
from pathlib import Path
import json
from datetime import datetime
from dataclasses import dataclass

@dataclass
class TextBlock:
    """Represents a coherent block of text with its properties."""
    text: str
    page_number: int
    y_position: float
    font_size: float = 0
    is_header: bool = False

class ContentAggregator:
    """Handles the aggregation and structuring of extracted content."""
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def _is_header(self, text: str, font_size: float) -> bool:
        """Determine if text represents a header."""
        if font_size > 12:
            return True
        if text.isupper() and len(text.split()) <= 4:
            return True
        header_keywords = ['synopsis', 'introduction', 'methods', 'results', 'discussion', 'conclusion']
        return any(keyword in text.lower() for keyword in header_keywords)

    def process_content(self, raw_elements: List[Dict], ocr_elements: List[Dict]) -> Dict:
        """Process both native PDF elements and OCR results into structured content."""
        # Combine native and OCR elements
        combined_elements = raw_elements.copy()
        for ocr_elem in ocr_elements:
            if not any(self._is_duplicate(ocr_elem, elem) for elem in raw_elements):
                combined_elements.append(ocr_elem)

        blocks = self._merge_text_elements(combined_elements)
        return self._organize_content(blocks)

    def _is_duplicate(self, ocr_elem: Dict, native_elem: Dict) -> bool:
        """Check if OCR element duplicates native PDF content."""
        return (ocr_elem['page_number'] == native_elem['page_number'] and
                abs(ocr_elem['bbox'][1] - native_elem['bbox'][1]) < 5)

    def _merge_text_elements(self, elements: List[Dict]) -> List[TextBlock]:
        """Merge individual text elements into coherent blocks."""
        sorted_elements = sorted(elements, key=lambda x: (x['page_number'], x['bbox'][1]))
        blocks = []
        current_block = None
        y_tolerance = 3

        for elem in sorted_elements:
            text = elem['content'].strip()
            if not text:
                continue

            y_pos = elem['bbox'][1]
            font_size = elem.get('size', 0)

            if (current_block is None or 
                elem['page_number'] != current_block.page_number or 
                abs(y_pos - current_block.y_position) > y_tolerance):
                
                if current_block:
                    blocks.append(current_block)
                current_block = TextBlock(
                    text=text,
                    page_number=elem['page_number'],
                    y_position=y_pos,
                    font_size=font_size,
                    is_header=self._is_header(text, font_size)
                )
            else:
                current_block.text += f" {text}"

        if current_block:
            blocks.append(current_block)
        return blocks

    def _organize_content(self, blocks: List[TextBlock]) -> Dict:
        """Organize text blocks into a structured document."""
        document = {
            'sections': [],
            'content_by_page': {},
            'text_blocks': []
        }

        current_section = None
        for block in blocks:
            # Initialize page content if needed
            if block.page_number not in document['content_by_page']:
                document['content_by_page'][block.page_number] = []

            # Add to page content
            document['content_by_page'][block.page_number].append(block.text)
            document['text_blocks'].append({
                'text': block.text,
                'page': block.page_number,
                'is_header': block.is_header
            })

            # Handle sections
            if block.is_header:
                current_section = {
                    'title': block.text,
                    'content': [],
                    'page_number': block.page_number
                }
                document['sections'].append(current_section)
            elif current_section is not None:
                current_section['content'].append(block.text)

        return document

class ModernPDFExtractor:
    """Main PDF extraction class with integrated OCR capabilities."""
    def __init__(self, use_ocr: bool = True):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        self.use_ocr = use_ocr
        self.content_aggregator = ContentAggregator()
        
        # Configure Tesseract
        if use_ocr:
            self._configure_tesseract()

    def _configure_tesseract(self):
        """Configure Tesseract OCR with proper paths."""
        tessdata_prefix = str(Path.home() / 'homebrew/share/tessdata')
        os.environ['TESSDATA_PREFIX'] = tessdata_prefix
        pytesseract.pytesseract.tesseract_cmd = str(Path.home() / 'homebrew/bin/tesseract')

    def extract_from_pdf(self, pdf_path: Union[str, Path]) -> Dict:
        """Extract and structure content from PDF."""
        pdf_path = Path(pdf_path)
        self.logger.info(f"Starting extraction from: {pdf_path}")

        try:
            # Extract metadata
            metadata = self._extract_metadata(pdf_path)
            
            # Extract native PDF content
            self.logger.info("Extracting native PDF content...")
            raw_elements = self._extract_native_content(pdf_path)
            
            # Apply OCR if enabled
            ocr_elements = []
            if self.use_ocr:
                self.logger.info("Applying OCR processing...")
                ocr_elements = self._apply_ocr(pdf_path)

            # Process and structure all content
            self.logger.info("Structuring content...")
            structured_content = self.content_aggregator.process_content(raw_elements, ocr_elements)
            
            return {
                'metadata': metadata,
                'content': structured_content
            }

        except Exception as e:
            self.logger.error(f"Extraction failed: {str(e)}")
            raise

    def _extract_metadata(self, pdf_path: Path) -> Dict:
        """Extract PDF metadata."""
        with pdfplumber.open(pdf_path) as pdf:
            return {
                'filename': pdf_path.name,
                'file_size': os.path.getsize(pdf_path),
                'num_pages': len(pdf.pages),
                'title': pdf.metadata.get('Title'),
                'author': pdf.metadata.get('Author'),
                'creation_date': pdf.metadata.get('CreationDate'),
                'extraction_date': datetime.now().isoformat()
            }

    def _extract_native_content(self, pdf_path: Path) -> List[Dict]:
        """Extract native PDF content."""
        elements = []
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(tqdm(pdf.pages, desc="Extracting native content"), 1):
                words = page.extract_words(
                    keep_blank_chars=True,
                    x_tolerance=3,
                    y_tolerance=3
                )
                for word in words:
                    elements.append({
                        'content': word.get('text', ''),
                        'bbox': (
                            word.get('x0', 0),
                            word.get('top', 0),
                            word.get('x1', 0),
                            word.get('bottom', 0)
                        ),
                        'page_number': page_num,
                        'size': word.get('size', 0),
                        'font': word.get('fontname', '')
                    })
        return elements

    def _apply_ocr(self, pdf_path: Path) -> List[Dict]:
        """Apply OCR to PDF pages."""
        ocr_elements = []
        images = convert_from_path(pdf_path)
        
        for i, image in enumerate(tqdm(images, desc="OCR Processing"), 1):
            try:
                ocr_data = pytesseract.image_to_data(
                    image,
                    output_type=pytesseract.Output.DICT,
                    config=f'--tessdata-dir "{str(Path.home() / 'homebrew/share/tessdata')}"'
                )
                
                for j in range(len(ocr_data['text'])):
                    if ocr_data['conf'][j] > 50:  # Confidence threshold
                        ocr_elements.append({
                            'content': ocr_data['text'][j],
                            'bbox': (
                                ocr_data['left'][j],
                                ocr_data['top'][j],
                                ocr_data['left'][j] + ocr_data['width'][j],
                                ocr_data['top'][j] + ocr_data['height'][j]
                            ),
                            'page_number': i,
                            'size': 0,
                            'confidence': float(ocr_data['conf'][j]) / 100
                        })
                        
            except Exception as e:
                self.logger.error(f"OCR failed for page {i}: {str(e)}")
                continue
                
        return ocr_elements

def extract_pdf_information(pdf_path: str, output_path: str) -> Dict:
    """Extract and save PDF information."""
    extractor = ModernPDFExtractor(use_ocr=True)
    
    try:
        extracted_data = extractor.extract_from_pdf(pdf_path)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(extracted_data, f, indent=2, ensure_ascii=False)
            
        print(f"Successfully extracted content to: {output_path}")
        return extracted_data
        
    except Exception as e:
        print(f"Extraction failed: {str(e)}")
        raise

if __name__ == '__main__':
    results = extract_pdf_information(
        "PDFs/grundy-et-al-2018-2018-aha-acc-aacvpr-aapa-abc-acpm-ada-ags-apha-aspc-nla-pcna-guideline-on-the-management-of-blood/grundy-et-al-2018-2018-aha-acc-aacvpr-aapa-abc-acpm-ada-ags-apha-aspc-nla-pcna-guideline-on-the-management-of-blood.pdf",
        "output.json"
    )

