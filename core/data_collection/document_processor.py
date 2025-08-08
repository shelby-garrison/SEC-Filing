from typing import List, Dict
from bs4 import BeautifulSoup
from langchain.text_splitter import RecursiveCharacterTextSplitter
import re
import json

from ..data_models.filing_models import FilingRecord


class DocumentTextProcessor:
    
    def __init__(self):
        self.text_segmenter = RecursiveCharacterTextSplitter(
            chunk_size=1500, 
            chunk_overlap=300,
            separators=["\n\n", "\n", ".", " "]
        )
        
        self.section_identifiers = {
            'risk_factors': r'(Item\s*1A\.?\s*)?Risk\s*Factors',
            'mda': r'(Item\s*7\.?\s*)?Management\'?s?\s*Discussion\s*and\s*Analysis',
            'business': r'(Item\s*1\.?\s*)?Business',
            'financial_statements': r'(Item\s*8\.?\s*)?Financial\s*Statements',
            'market_risk': r'(Item\s*7A\.?\s*)?Quantitative\s*and\s*Qualitative\s*Disclosures\s*[Aa]bout\s*Market\s*Risk',
        }
    
    def _determine_section_type(self, text: str) -> str:
        text_lower = text.lower()
        for section_type, pattern in self.section_identifiers.items():
            if re.search(pattern, text, re.IGNORECASE):
                return section_type
        return 'other'

    def _normalize_text(self, text: str) -> str:
        # Remove excessive whitespace
        text = ' '.join(text.split())
        # Remove special characters but keep structure
        text = re.sub(r'[^\w\s\.,;:\-\(\)\'\"$%]', ' ', text)
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def process_document(self, document: FilingRecord) -> List[Dict]:
        text_segments = []
        
        if document.content_text:
            document_sections = self._partition_into_sections(document.content_text)
            
            for section_content, section_category in document_sections:
                processed_text = self._normalize_text(section_content)
                
                # Splitting into smaller chunks
                text_pieces = self.text_segmenter.split_text(processed_text)
                
                for i, text_piece in enumerate(text_pieces):
                    financial_data = self._extract_financial_metrics(text_piece)
                    
                    text_segments.append({
                        "text": text_piece,
                        "metadata": {
                            "filing_id": document.record_identifier,
                            "company_name": document.entity_name,
                            "ticker": document.stock_symbol,
                            "filing_type": document.document_category,
                            "filing_date": str(document.submission_date),
                            "section": section_category,
                            "chunk_index": i,
                            "total_chunks": len(text_pieces),
                            "currency_amounts": ','.join(map(str, financial_data.get('currency_amounts', []))),
                            "percentages": ','.join(map(str, financial_data.get('percentages', []))),
                            "has_metrics": "true" if any(financial_data.values()) else "false"
                        }
                    })
        
        return text_segments
    
    def _partition_into_sections(self, text: str) -> List[tuple]:
        document_sections = []
        current_content = ""
        current_category = "other"
        
        for line in text.split('\n'):
            section_category = self._determine_section_type(line)
            if section_category != 'other':
                if current_content:
                    document_sections.append((current_content, current_category))
                current_content = line
                current_category = section_category
            else:
                current_content += '\n' + line
        
        if current_content:
            document_sections.append((current_content, current_category))
        
        return document_sections
    
    def _extract_financial_metrics(self, text: str) -> Dict:
        financial_data = {
            'currency_amounts': [],
            'percentages': []
        }
        
        currency_matches = re.finditer(r'\$\s*(\d+(?:,\d{3})*(?:\.\d{2})?)\s*(million|billion|trillion)?', text)
        for match in currency_matches:
            amount = float(match.group(1).replace(',', ''))
            if match.group(2):
                multiplier = {'million': 1e6, 'billion': 1e9, 'trillion': 1e12}
                amount *= multiplier[match.group(2)]
            financial_data['currency_amounts'].append(amount)
        
        percentage_matches = re.finditer(r'(\d+(?:\.\d+)?)\s*%', text)
        financial_data['percentages'] = [float(m.group(1)) for m in percentage_matches]
        
        return financial_data
