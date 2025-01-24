from pathlib import Path
import xml.etree.ElementTree as ET
from collections import defaultdict
from typing import Dict, Any, List
import re
import json

class ConfigConstructor:
    def __init__(self, pdfs_dir: str = 'PDFs'):
        self.pdfs_dir = Path(pdfs_dir)
        self.configs: List[Dict[str, Any]] = []

    def analyze_xml(self, xml_path: Path, dir_path: Path) -> Dict[str, Any]:
        tree = ET.parse(xml_path)
        root = tree.getroot()

        # Find tables
        tables = self.find_tables(root)
        if not tables:
            return {}

        # Get left margins from first recommendation table found
        left_margins = self.get_table_margins(tables[0])
        if not left_margins:
            return {}

        config = {
            'directory': str(dir_path),
            'guideline_xml': xml_path.name,
            'cit_version': self.detect_citation_version(root),
            'guideline_version': self.detect_guideline_version(root),
            'left_down': left_margins['cor_margin'],
            'left_up': left_margins['text_margin']
        }
        return config

    def find_tables(self, root: ET.Element) -> List[List[ET.Element]]:
        """Find recommendation tables in the document."""
        tables = []
        current_table = []
        in_table = False

        for node in root.findall('.//text'):
            text = ''.join(node.itertext()).strip()
            
            # Detect table start
            if ('table' in text.lower() and any(x in text.lower() for x in ['recommendations', 'recommendation'])):
                in_table = True
                current_table = []
                continue

            # Collect table elements
            if in_table:
                if 'synopsis' in text.lower():  # Table typically ends before synopsis
                    in_table = False
                    if current_table:
                        tables.append(current_table)
                else:
                    current_table.append(node)

        return tables

    def get_table_margins(self, table_nodes: List[ET.Element]) -> Dict[str, int]:
        """Analyze table structure to get correct margins."""
        cor_margins = []
        text_margins = []
        
        for i, node in enumerate(table_nodes):
            text = ''.join(node.itertext()).strip()
            left = int(node.get('left', '0'))
            
            # Look for COR values
            if text in {'1', '2a', '2b', '3', 'IIa', 'IIb', 'III'}:
                cor_margins.append(left)
                
                # If we found a COR value, the recommendation text usually follows
                for next_node in table_nodes[i+1:i+3]:
                    next_text = ''.join(next_node.itertext()).strip()
                    if next_text and any(c.isdigit() for c in next_text):
                        text_margins.append(int(next_node.get('left', '0')))
                        break

        if not cor_margins or not text_margins:
            return {}

        return {
            'cor_margin': min(cor_margins),
            'text_margin': min(text_margins)
        }

    def detect_citation_version(self, root: ET.Element) -> int:
        for node in root.findall('.//text'):
            text = ''.join(node.itertext()).strip()
            if re.search(r'S\d+[\d,\s.-]+', text):
                return 1
        return 2

    def detect_guideline_version(self, root: ET.Element) -> int:
        table_found = False
        recommendation_pattern = 0
        
        for node in root.findall('.//text'):
            text = ''.join(node.itertext()).strip()
            if 'table' in text.lower() and 'recommendations' in text.lower():
                table_found = True
            elif table_found and "recommendations for" in text.lower():
                recommendation_pattern += 1
        
        return 2 if recommendation_pattern > 5 else 1

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