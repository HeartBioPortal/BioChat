import subprocess
import os

def convert_pdf_to_xml(pdf_path):
    """Convert PDF to XML using pdf2xml"""
    # Get output path by replacing .pdf extension with .xml
    output_path = os.path.splitext(pdf_path)[0] + '.xml'
    
    # Run pdf2xml (assuming it's installed)
    try:
        subprocess.run(['pdftohtml', '-xml', pdf_path, output_path], check=True)
        
        # Read the generated XML
        with open(output_path, 'r', encoding='utf-8') as f:
            xml_content = f.read()
            
        # Clean up the temporary file
        os.remove(output_path)
        
        return xml_content
        
    except subprocess.CalledProcessError as e:
        raise Exception(f"Error converting PDF to XML: {str(e)}")

if __name__ == '__main__':
    pdf_path = 'PDFs/chan-et-al-2017-acc-aha-special-report-clinical-practice-guideline-implementation-strategies-a-summary-of-systematic.pdf'
    xml = convert_pdf_to_xml(pdf_path)
    with open('output.xml', 'w') as f:
        f.write(xml)