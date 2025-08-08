from typing import List, Optional, Dict
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import time
import json

from ..settings import app_settings
from ..data_models.filing_models import FilingRecord


class EDGARDataFetcher:
    
    def __init__(self):
        self.api_endpoint = "https://www.sec.gov"
        self.request_headers = {
            'User-Agent': 'Sample-SEC-Research-Tool/1.0 (kaustuv.baidya.cd.eee21@itbhu.ac.in)'  
        }
        
        self.request_interval = 0.1  # seconds between requests
        self.previous_request_time = 0
    
    def _enforce_rate_limiting(self):
        current_timestamp = time.time()
        time_elapsed = current_timestamp - self.previous_request_time
        if time_elapsed < self.request_interval:
            time.sleep(self.request_interval - time_elapsed)
        self.previous_request_time = time.time()

    def retrieve_filings(
        self,
        ticker: str,
        filing_types: List[str],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[FilingRecord]:
     
        try:
            self._enforce_rate_limiting()
            company_lookup_url = f"https://www.sec.gov/files/company_tickers.json"
            response = requests.get(company_lookup_url, headers=self.request_headers)
            response.raise_for_status()
            
            company_database = response.json()
            cik_number = None
            entity_name = None
            
            for entry in company_database.values():
                if entry['ticker'].upper() == ticker.upper():
                    cik_number = str(entry['cik_str']).zfill(10)
                    entity_name = entry['title']
                    break
            
            if not cik_number:
                raise ValueError(f"Could not find CIK for ticker {ticker}")
            
            self._enforce_rate_limiting()
            submissions_endpoint = f"https://data.sec.gov/submissions/CIK{cik_number}.json"
            response = requests.get(submissions_endpoint, headers=self.request_headers)
            response.raise_for_status()
            
            filing_data = response.json()
            recent_submissions = filing_data.get('filings', {}).get('recent', {})
            
            if not recent_submissions:
                return []
            
            filing_records = []
            for idx, form_type in enumerate(recent_submissions.get('form', [])):
                if form_type in filing_types:
                    submission_date = datetime.strptime(
                        recent_submissions['filingDate'][idx],
                        '%Y-%m-%d'
                    )
                    
                    if start_date and submission_date < start_date:
                        continue
                    if end_date and submission_date > end_date:
                        continue
                    
                    accession_id = recent_submissions['accessionNumber'][idx]
                    primary_filename = recent_submissions.get('primaryDocument', [''])[idx]
                    
                    
                    self._enforce_rate_limiting()
                    document_url = (
                        f"https://www.sec.gov/Archives/edgar/data/{cik_number.lstrip('0')}/"
                        f"{accession_id.replace('-', '')}/{primary_filename}"
                    )
                    
                    record = FilingRecord(
                        record_identifier=accession_id.replace('-', ''),
                        entity_name=entity_name,
                        stock_symbol=ticker,
                        document_category=form_type,
                        submission_date=submission_date,
                        content_text=self._fetch_document_content(document_url),
                        additional_info={
                            'cik': cik_number,
                            'accession_number': accession_id,
                            'file_number': recent_submissions.get('fileNumber', [''])[idx],
                        },
                        content_sections={}
                    )
                    filing_records.append(record)
                    
                    if len(filing_records) >= 5:
                        break
            
            return filing_records
            
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Error fetching SEC data: {str(e)}")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Error parsing SEC response: {str(e)}")
        except Exception as e:
            raise RuntimeError(f"Unexpected error: {str(e)}")
    
    def _fetch_document_content(self, url: str) -> str:
       
        try:
            self._enforce_rate_limiting()
            response = requests.get(url, headers=self.request_headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            document_content = ""
            
            for tag in ['TEXT', 'DOCUMENT', 'filing-content']:
                content = soup.find(tag)
                if content:
                    document_content = content.get_text(separator='\n', strip=True)
                    break
            
            if not document_content:
                document_content = soup.get_text(separator='\n', strip=True)
            
            
            document_content = document_content.replace('\n', ' ').replace('\r', ' ')
            document_content = ' '.join(document_content.split())  
            
            return document_content or "No content available"
            
        except Exception as e:
            print(f"Warning: Error fetching filing text: {str(e)}")
            return "No content available"
