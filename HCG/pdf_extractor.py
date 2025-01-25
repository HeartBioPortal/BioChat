import os
import json
import base64
from pathlib import Path
from typing import Dict, List, Optional
import logging
from pdf2image import convert_from_path
import tempfile
from openai import OpenAI
from tqdm import tqdm
import time

class PDFProcessor:
    def __init__(self, pdf_dir: str, output_dir: str):
        """Initialize the PDF processor with directory paths."""
        self.pdf_dir = Path(pdf_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.setup_logging()
        self.client = OpenAI()
        
    def setup_logging(self):
        """Set up logging configuration."""
        logging.basicConfig(
            filename='pdf_processing.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

    def get_pdf_output_dir(self, pdf_path: Path) -> Path:
        """Create and return output directory for a specific PDF."""
        pdf_output_dir = self.output_dir / pdf_path.stem
        pdf_output_dir.mkdir(exist_ok=True)
        return pdf_output_dir

    def get_last_processed_page(self, pdf_output_dir: Path) -> int:
        """Determine the last successfully processed page."""
        existing_files = [f for f in pdf_output_dir.glob("*.json") if f.stem.isdigit()]
        if not existing_files:
            return 0
        return max(int(f.stem) for f in existing_files)

    def convert_pdf_to_images(self, pdf_path: Path) -> List[tempfile.NamedTemporaryFile]:
        """Convert PDF pages to images and return temporary files."""
        images = convert_from_path(pdf_path)
        temp_files = []
        
        for image in images:
            temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
            image.save(temp_file.name, 'PNG')
            temp_files.append(temp_file)
            
        return temp_files

    def analyze_image(self, image_path: str) -> Dict:
        """Send image to OpenAI API for analysis."""
        try:
            with open(image_path, "rb") as image_file:
                completion = self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": "Please analyze this image and provide a structured JSON response containing all the information visible in the image. Return only valid JSON without any additional text."},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/png;base64,{base64.b64encode(image_file.read()).decode()}"
                                    }
                                }
                            ]
                        }
                    ],
                    max_tokens=4096
                )
                
                # Clean and parse the response
                response_text = completion.choices[0].message.content.strip()
                try:
                    # Try to parse the response as JSON
                    return json.loads(response_text)
                except json.JSONDecodeError:
                    # If parsing fails, return the raw text in a structured format
                    return {
                        "raw_text": response_text,
                        "parsing_error": "Response was not valid JSON"
                    }
                    
        except Exception as e:
            logging.error(f"Error analyzing image {image_path}: {str(e)}")
            return {"error": str(e)}

    def process_single_pdf(self, pdf_path: Path):
        """Process a single PDF file."""
        logging.info(f"Processing PDF: {pdf_path}")
        pdf_output_dir = self.get_pdf_output_dir(pdf_path)
        last_processed_page = self.get_last_processed_page(pdf_output_dir)
        
        try:
            temp_files = self.convert_pdf_to_images(pdf_path)
            
            with tqdm(total=len(temp_files), initial=last_processed_page) as pbar:
                for page_num, temp_file in enumerate(temp_files[last_processed_page:], 
                                                   start=last_processed_page):
                    try:
                        result = self.analyze_image(temp_file.name)
                        
                        # Save individual page result
                        page_output_path = pdf_output_dir / f"{page_num + 1}.json"
                        with open(page_output_path, 'w') as f:
                            json.dump(result, f, indent=2)
                        
                        pbar.update(1)
                        time.sleep(1)  # Rate limiting
                    finally:
                        os.unlink(temp_file.name)
                        
        except Exception as e:
            logging.error(f"Error processing PDF {pdf_path}: {str(e)}")
            raise

    def process_all_pdfs(self):
        """Process all PDFs in the directory structure."""
        for root, _, files in os.walk(self.pdf_dir):
            for file in files:
                if file.lower().endswith('.pdf'):
                    pdf_path = Path(root) / file
                    try:
                        self.process_single_pdf(pdf_path)
                    except Exception as e:
                        logging.error(f"Failed to process {pdf_path}: {str(e)}")
                        continue

def main():
    """Main execution function."""
    pdf_processor = PDFProcessor(
        pdf_dir="PDFs",
        output_dir="OpenAI_outputs"
    )
    pdf_processor.process_all_pdfs()

if __name__ == "__main__":
    main()