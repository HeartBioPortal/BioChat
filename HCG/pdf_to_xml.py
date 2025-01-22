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
    pdf_dir = 'PDFs'
    for pdf_file in os.listdir(pdf_dir):
        if pdf_file.endswith('.pdf'):
            pdf_path = os.path.join(pdf_dir, pdf_file)
            xml_content = convert_pdf_to_xml(pdf_path)
            
            # Create a new directory with the name of the PDF (without extension)
            pdf_name = os.path.splitext(pdf_file)[0]
            output_dir = os.path.join(pdf_dir, pdf_name)
            os.makedirs(output_dir, exist_ok=True)
            
            # Move the PDF to the new directory
            new_pdf_path = os.path.join(output_dir, pdf_file)
            os.rename(pdf_path, new_pdf_path)
            
            # Write the XML content to a file in the new directory
            xml_path = os.path.join(output_dir, pdf_name + '.xml')
            with open(xml_path, 'w', encoding='utf-8') as f:
                f.write(xml_content)