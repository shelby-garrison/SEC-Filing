from typing import List, Dict, Optional
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from collections import defaultdict

from ..settings import app_settings


class DocumentIndex:
    
    def __init__(self):
        self.embedding_model = embedding_functions.DefaultEmbeddingFunction()
        
        self.database_client = chromadb.Client(Settings(
            persist_directory=app_settings.VECTOR_DATABASE_PATH,
            anonymized_telemetry=False
        ))
        
        self.document_collection = self.database_client.get_or_create_collection(
            name="sec_filings",
            embedding_function=self.embedding_model
        )
    
    def add_documents(self, documents: List[Dict]) -> None:
        if not documents:
            return
            
        document_texts = [doc["text"] for doc in documents]
        document_metadata = [doc["metadata"] for doc in documents]
        document_ids = [f"{doc['metadata']['filing_id']}_{doc['metadata'].get('chunk_index', 0)}" for doc in documents]
        
        self.document_collection.add(
            documents=document_texts,
            metadatas=document_metadata,
            ids=document_ids
        )
    
    def search(
        self,
        query: str,
        filter_metadata: Optional[Dict] = None,
        limit: int = 5
    ) -> Dict:
        search_criteria = self._construct_search_criteria(filter_metadata)
        
        search_results = self.document_collection.query(
            query_texts=[query],
            n_results=limit * 2, 
            where=search_criteria
        )
        
        #deduplicating results
        processed_results = self._process_search_results(search_results, limit)
        
        return processed_results
    
    def _construct_search_criteria(self, filter_metadata: Optional[Dict]) -> Optional[Dict]:
        if not filter_metadata:
            return None
            
        search_conditions = []
        
        for key, value in filter_metadata.items():
            if isinstance(value, dict) and "$in" in value:
                in_values = value["$in"]
                if len(in_values) == 1:
                    search_conditions.append({key: in_values[0]})
                else:
                    search_conditions.append({
                        "$or": [
                            {key: v} for v in in_values
                        ]
                    })
            else:
                search_conditions.append({key: value})
        
        if len(search_conditions) == 1:
            return search_conditions[0]
        
        return {"$and": search_conditions}
    
    def _process_search_results(
        self,
        search_results: Dict,
        limit: int
    ) -> Dict:
        if not search_results['documents'] or not search_results['documents'][0]:
            return {"documents": [[]], "metadatas": [[]]}
        
        # Combining results and deduplicating
        filtered_results = []
        seen_content_signatures = set()
        
        for document_content, document_metadata in zip(
            search_results['documents'][0],
            search_results['metadatas'][0]
        ):
            content_signature = document_content[:100]
            if content_signature not in seen_content_signatures:
                seen_content_signatures.add(content_signature)
                
                if document_metadata.get('has_metrics') == 'true':
                    currency_values = [float(x) for x in document_metadata.get('currency_amounts', '').split(',') if x]
                    percentage_values = [float(x) for x in document_metadata.get('percentages', '').split(',') if x]
                    document_metadata['metrics_summary'] = f"Found {len(currency_values)} currency amounts and {len(percentage_values)} percentage values"
                
                filtered_results.append((document_content, document_metadata))
                
            if len(filtered_results) >= limit:
                break
        
        docs, metas = zip(*filtered_results) if filtered_results else ([], [])
        
        return {
            "documents": [list(docs)],
            "metadatas": [list(metas)]
        }
