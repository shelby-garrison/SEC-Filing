from typing import Dict, List, Optional
import re
from datetime import datetime
from dateutil.parser import parse


class NaturalLanguageProcessor:
    
    
    def __init__(self):
       
        self.entity_name_mappings = {
            'Apple': 'AAPL',
            'Microsoft': 'MSFT',
            'Google': 'GOOGL',
            'Amazon': 'AMZN',
            # other companies can be added here
        }
        self.symbol_pattern = re.compile(r'\$?[A-Z]{1,5}(?=\s|$)')
        
    def analyze_query(self, query: str) -> Dict:
       
        return {
            "tickers": self._extract_stock_symbols(query),
            "dates": self._extract_date_references(query),
            "filing_types": self._extract_document_categories(query)
        }
        
    def _extract_stock_symbols(self, query: str) -> List[str]:
       
        for company_name, stock_symbol in self.entity_name_mappings.items():
            if company_name in query:
                return [stock_symbol]
        
        matches = [match.group().replace('$', '') for match in self.symbol_pattern.finditer(query)]
        return matches if matches else []
        
    def _extract_date_references(self, query: str) -> Dict[str, Optional[datetime]]:
      
        # TODO:  date extraction
        return {
            "start_date": None,
            "end_date": None
        }
        
    def _extract_document_categories(self, query: str) -> List[str]:
       
        document_categories = []
        if "10-K" in query:
            document_categories.append("10-K")
        if "10-Q" in query:
            document_categories.append("10-Q")
        if "8-K" in query:
            document_categories.append("8-K")
        if "DEF 14A" in query:
            document_categories.append("DEF 14A")
        return document_categories
