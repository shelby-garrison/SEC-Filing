from datetime import datetime
from typing import Dict, Any
from pydantic import BaseModel


class FilingRecord(BaseModel):
    
    record_identifier: str
    entity_name: str
    stock_symbol: str
    document_category: str
    submission_date: datetime
    content_text: str
    additional_info: Dict[str, Any]
    content_sections: Dict[str, str]  # Section name -> content mapping
    
    class Config:
        arbitrary_types_allowed = True
