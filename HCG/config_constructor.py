from pathlib import Path
import xml.etree.ElementTree as ET
from collections import defaultdict
from typing import Dict, Any, List
import re
import json

class ConfigConstructor:
    """Analyzes XML files to automatically determine parsing configurations."""
    
    def __init__(self, pdfs_dir: str = 'PDFs'):
        self.pdfs_dir = Path(pdfs_dir)
        self.configs: List[Dict[str, Any]] = []

    def analyze_directory(self) -> None:
        """Walk through PDF directories and analyze XML files."""
        for dir_path in self.pdfs_dir.iterdir():
            if dir_path.is_dir():
                xml_files = list(dir_path.glob('*.xml'))
                if xml_files:
                    # Analyze the first XML file found 
                    config = self.analyze_xml(xml_files[0], dir_path)
                    if config:
                        self.configs.append(config)

    def analyze_xml(self, xml_path: Path, dir_path: Path) -> Dict[str, Any]:
        """Analyze a single XML file to determine its configuration parameters."""
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            
            # Initialize config with basic info
            config = {
                'directory': str(dir_path),
                'guideline_xml': xml_path.name,
                'cit_version': self.detect_citation_version(root),
                'guideline_version': self.detect_guideline_version(root),
                'left_margins': self.analyze_left_margins(root)
            }
            
            return config
            
        except ET.ParseError:
            print(f"Failed to parse XML file: {xml_path}")
            return {}

    def detect_citation_version(self, root: ET.Element) -> int:
        """Detect citation format version based on reference patterns."""
        # Look for citation patterns in text nodes
        text_nodes = root.findall('.//text')
        citations = []
        for node in text_nodes:
            text = ''.join(node.itertext()).strip()
            if re.search(r'S\d+[\d,\s.-]+', text):
                return 1
            elif re.search(r'\(\d+\)', text):
                return 2
        return 1  # Default to version 1

    def detect_guideline_version(self, root: ET.Element) -> int:
        """Determine guideline format version based on document structure."""
        # Look for characteristic patterns of different versions
        text_nodes = root.findall('.//text')
        recommendation_pattern = 0
        
        for node in text_nodes:
            text = ''.join(node.itertext()).strip()
            if "recommendations for" in text.lower():
                recommendation_pattern += 1
                
        if recommendation_pattern > 5:
            return 2
        return 1  # Default to version 1

    def analyze_left_margins(self, root: ET.Element) -> Dict[str, int]:
        """Analyze left margins to determine layout parameters."""
        margins = []
        for node in root.findall('.//text'):
            try:
                left = int(node.get('left', 0))
                if left > 0:
                    margins.append(left)
            except (ValueError, TypeError):
                continue
                
        if not margins:
            return {'left_down': 63, 'left_up': 80}  # Default values
            
        margins = sorted(set(margins))
        
        # Find common left margin clusters
        clusters = defaultdict(int)
        for m in margins:
            clusters[m // 10 * 10] += 1
            
        # Get the two most common margin ranges
        common_margins = sorted(clusters.items(), key=lambda x: x[1], reverse=True)[:2]
        if len(common_margins) >= 2:
            return {
                'left_down': common_margins[0][0],
                'left_up': common_margins[1][0]
            }
        return {'left_down': 63, 'left_up': 80}  # Default values

    def save_config(self, output_file: str = 'constructed_config.py') -> None:
        """Save the constructed configurations to a Python file."""
        with open(output_file, 'w') as f:
            f.write("# Auto-generated configuration file\n\n")
            f.write("SCRAPING = [\n")
            for config in self.configs:
                f.write(f"    {{\n")
                for key, value in config.items():
                    if isinstance(value, str):
                        f.write(f"        '{key}': '{value}',\n")
                    else:
                        f.write(f"        '{key}': {value},\n")
                f.write("    },\n")
            f.write("]\n")

def main():
    constructor = ConfigConstructor()
    constructor.analyze_directory()
    constructor.save_config()

if __name__ == "__main__":
    main()