from pathlib import Path
from typing import Dict, List, Any, Optional, Iterator, Tuple
import xml.etree.ElementTree as ET
from dataclasses import dataclass
import json
import re
from collections import defaultdict

@dataclass
class GuidelineData:
    """Data structure for guideline recommendations."""
    title: str
    subtitle: str 
    recommendations: List[Dict[str, Any]]

class XMLParser:
    """Base class for parsing XML files."""
    
    def __init__(self, xml_path: Path):
        self.xml_path = xml_path
        self.tree = self._load_xml()
        
    def _load_xml(self) -> ET.ElementTree:
        """Load and parse XML file."""
        try:
            return ET.parse(self.xml_path)
        except ET.ParseError as e:
            raise ValueError(f"Failed to parse XML file {self.xml_path}: {e}")

    def get_text_from_node(self, node: ET.Element) -> str:
        """Extract all text from an XML node."""
        return ''.join(node.itertext()).strip()

    def get_next_nodes(self, tree: List[ET.Element], current_index: int, count: int = 2) -> List[ET.Element]:
        """Get next n nodes from a list of nodes starting from current_index."""
        try:
            return tree[current_index + 1:current_index + 1 + count]
        except IndexError:
            return []

class GuidelineParser(XMLParser):
    """Parser for clinical guidelines XML."""
    
    def __init__(self, xml_path: Path, config: Dict[str, Any]):
        super().__init__(xml_path)
        self.config = config
        self.recommendations: List[GuidelineData] = []
        
    def parse(self) -> List[GuidelineData]:
        """Parse the guideline document and extract recommendations."""
        root = self.tree.getroot()
        
        # Get all text nodes
        all_nodes = list(root.findall('.//text'))
        
        if self.config['guideline_version'] == 1:
            return self._parse_v1(all_nodes)
        else:
            return self._parse_v2(all_nodes)

    def _parse_v1(self, nodes: List[ET.Element]) -> List[GuidelineData]:
        """Parse version 1 format guidelines."""
        current_data = None
        
        for i, node in enumerate(nodes):
            text = self.get_text_from_node(node)
            left = int(node.get('left', '0'))
            
            # Check if this is a recommendation section title
            if (self.config['left_down'] <= left <= self.config['left_up'] and 
                'recommendation' in text.lower()):
                if current_data and current_data.recommendations:
                    self.recommendations.append(current_data)
                current_data = GuidelineData(text, "", [])
                
            # Check for recommendation rows (COR, LOE, text)
            elif current_data and text in {'IIa', 'IIb'}:
                recommendation = self._parse_recommendation_row(nodes, i)
                if recommendation:
                    current_data.recommendations.append(recommendation)
                    
        if current_data and current_data.recommendations:
            self.recommendations.append(current_data)
            
        return self.recommendations

    def _parse_v2(self, nodes: List[ET.Element]) -> List[GuidelineData]:
        """Parse version 2 format guidelines."""
        current_data = None
        
        for i, node in enumerate(nodes):
            text = self.get_text_from_node(node)
            
            if 'recommendations for' in text.lower():
                if current_data and current_data.recommendations:
                    self.recommendations.append(current_data)
                current_data = GuidelineData(text, "", [])
                
            elif current_data and text in {'IIa', 'IIb'}:
                recommendation = self._parse_recommendation_row(nodes, i)
                if recommendation:
                    current_data.recommendations.append(recommendation)
                    
        if current_data and current_data.recommendations:
            self.recommendations.append(current_data)
            
        return self.recommendations

    def _parse_recommendation_row(self, nodes: List[ET.Element], current_index: int) -> Optional[Dict[str, Any]]:
        """Parse a single recommendation row."""
        try:
            next_nodes = self.get_next_nodes(nodes, current_index)
            if len(next_nodes) < 2:
                return None
                
            cor = self.get_text_from_node(nodes[current_index])
            loe = self.get_text_from_node(next_nodes[0])
            
            # For recommendation text, we might need to combine multiple nodes
            text = self.get_recommendation_text(nodes, current_index + 2)
            
            if not all([cor, loe, text]):
                return None
                
            citations = self._extract_citations(text)
                
            return {
                'COR': cor,
                'LOE': loe,
                'recommendation': text,
                'citations': citations
            }
            
        except Exception as e:
            print(f"Error parsing recommendation row: {e}")
            return None

    def get_recommendation_text(self, nodes: List[ET.Element], start_index: int) -> str:
        """Get full recommendation text which might span multiple nodes."""
        text_parts = []
        i = start_index
        
        while i < len(nodes):
            node = nodes[i]
            text = self.get_text_from_node(node)
            
            # Stop if we hit a new COR value or section
            if text in {'IIa', 'IIb'} or 'recommendation' in text.lower():
                break
                
            if text:
                text_parts.append(text)
                
            # If we hit a period and have collected some text, we can stop
            if text.endswith('.') and text_parts:
                break
                
            i += 1
            
        return ' '.join(text_parts)

    def _extract_citations(self, text: str) -> List[str]:
        """Extract citation references from recommendation text."""
        if self.config['cit_version'] == 1:
            # Look for patterns like S6.3.3-1—S6.3.3-7 or S6.3.3-1
            pattern = r'(S[\d.]+[-]\d+)(?:—(S[\d.]+[-]\d+))?'
            citations = []
            matches = re.finditer(pattern, text)
            
            for match in matches:
                if match.group(2):  # We have a range
                    start_cite = match.group(1)
                    end_cite = match.group(2)
                    citations.extend(self._expand_s_citation_range(start_cite, end_cite))
                else:  # Single citation
                    citations.append(match.group(1))
                    
            return citations
        else:
            pattern = r'\((\d+(?:[-–]\d+)?(?:,\s*\d+(?:[-–]\d+)?)*)\)'
            citations = []
            matches = re.finditer(pattern, text)
            
            for match in matches:
                citation = match.group(1)
                citations.extend(self._expand_numeric_citation_range(citation))
                
            return citations

    def _expand_s_citation_range(self, start_cite: str, end_cite: str) -> List[str]:
        """Expand S-prefixed citation ranges into individual citations."""
        try:
            # Extract the base part (e.g., 'S6.3.3') and number part (e.g., '1')
            start_base = start_cite[:start_cite.rindex('-')]
            start_num = int(start_cite[start_cite.rindex('-')+1:])
            
            # For end citation, use same base if not provided
            if not end_cite.startswith('S'):
                end_base = start_base
                end_num = int(end_cite)
            else:
                end_base = end_cite[:end_cite.rindex('-')]
                end_num = int(end_cite[end_cite.rindex('-')+1:])
            
            # If bases are different, return just the start and end
            if start_base != end_base:
                return [start_cite, end_cite]
                
            # Generate range of citations
            return [f"{start_base}-{i}" for i in range(start_num, end_num + 1)]
            
        except (ValueError, IndexError) as e:
            print(f"Error expanding citation range {start_cite}—{end_cite}: {e}")
            return [start_cite, end_cite]

    def _expand_numeric_citation_range(self, citation: str) -> List[str]:
        """Expand numeric citation ranges into individual citations."""
        citations = []
        parts = citation.strip().split(',')
        
        for part in parts:
            if '-' in part or '–' in part:
                try:
                    start, end = re.split('[-–]', part.strip())
                    start_num = int(start)
                    end_num = int(end)
                    citations.extend(str(i) for i in range(start_num, end_num + 1))
                except ValueError:
                    citations.append(part.strip())
            else:
                citations.append(part.strip())
                
        return citations

class GuidelineProcessor:
    """Process and save guideline data."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.directory = Path(config['directory'])
        
    def process(self):
        """Process guideline and save results."""
        guideline_path = self.directory / self.config['guideline_xml']
        
        # Parse guidelines
        parser = GuidelineParser(guideline_path, self.config)
        guidelines = parser.parse()
        
        # Filter out empty recommendations
        guidelines = [g for g in guidelines if g.recommendations]
        
        # Convert to serializable format
        result = [
            {
                'title': g.title,
                'subtitle': g.subtitle,
                'recommendations': g.recommendations
            }
            for g in guidelines
        ]
        
        # Save results
        output_file = self.directory / 'parsed_guidelines.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

def main():
    # Import constructed config
    from constructed_config import SCRAPING
    
    # Process each guideline
    for config in SCRAPING:
        try:
            processor = GuidelineProcessor(config)
            processor.process()
            print(f"Successfully processed {config['directory']}")
        except Exception as e:
            print(f"Error processing {config['directory']}: {e}")

if __name__ == "__main__":
    main()