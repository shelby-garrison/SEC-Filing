import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import json
from collections import defaultdict

from core.data_collection.edgar_fetcher import EDGARDataFetcher
from core.data_collection.document_processor import DocumentTextProcessor
from core.data_storage.document_index import DocumentIndex
from core.query_engine.nlp_processor import NaturalLanguageProcessor


class FilingAnalysisEngine: 
   
    
    def __init__(self):
        
        print("1. Initializing components...")
        self.data_fetcher = EDGARDataFetcher()
        self.text_processor = DocumentTextProcessor()
        self.document_index = DocumentIndex()
        self.technology_entities = ["AAPL", "MSFT", "GOOGL", "META", "AMZN"]
        self.banking_entities = ["JPM", "BAC", "GS", "MS", "WFC"]
        print("✓ Components initialized successfully")

    def retrieve_and_analyze_data(self, historical_days: int = 365) -> None:
        
        complete_entity_list = self.technology_entities + self.banking_entities
        document_categories = ["10-K", "10-Q", "8-K"]
        
        print("\n2. Fetching and processing company filings...")
        self._retrieve_and_process_entity_data(
            symbols=complete_entity_list,
            document_categories=document_categories,
            historical_days=historical_days
        )

    def _retrieve_and_process_entity_data(
        self,
        symbols: List[str],
        document_categories: List[str],
        historical_days: int
    ) -> None:
        current_timestamp = datetime.now()
        past_timestamp = current_timestamp - timedelta(days=historical_days)
        
        for symbol in symbols:
            print(f"\nProcessing {symbol}...")
            try:
                filing_records = self.data_fetcher.retrieve_filings(
                    ticker=symbol,
                    filing_types=document_categories,
                    start_date=past_timestamp,
                    end_date=current_timestamp
                )
                print(f"✓ Fetched {len(filing_records)} filings for {symbol}")
                
                for filing_record in filing_records:
                    print(f"Processing {filing_record.document_category} from {filing_record.submission_date}")
                    text_segments = self.text_processor.process_document(filing_record)
                    if text_segments:
                        self.document_index.add_documents(text_segments)
                        print(f"✓ Added {len(text_segments)} chunks to vector store")
                    else:
                        print(f"! No valid chunks extracted from {symbol} {filing_record.document_category}")
                        
            except Exception as e:
                print(f"! Error processing {symbol}: {str(e)}")

    def investigate_subject(
        self,
        subject_matter: str,
        target_entities: Optional[List[str]] = None,
        document_categories: Optional[List[str]] = None,
        result_limit: int = 10
    ) -> Dict:
        filter_criteria = {}
        if target_entities:
            filter_criteria["ticker"] = {"$in": target_entities}
        if document_categories:
            filter_criteria["filing_type"] = {"$in": document_categories}
            
        search_results = self.document_index.search(
            query=subject_matter,
            filter_metadata=filter_criteria,
            limit=result_limit
        )
        
        return self._categorize_findings(search_results)

    def _categorize_findings(self, search_results: Dict) -> Dict:
        categorized_data = defaultdict(list)
        
        if not search_results['documents'] or not search_results['documents'][0]:
            return {}
            
        for document_content, document_metadata in zip(search_results['documents'][0], search_results['metadatas'][0]):
            entity_symbol = document_metadata['ticker']
            document_type = document_metadata['filing_type']
            document_date = document_metadata['filing_date']
            content_section = document_metadata.get('section', 'main')
            
            # Extracting metrics
            metrics_description = ""
            if document_metadata.get('has_metrics') == 'true':
                monetary_values = [float(x) for x in document_metadata.get('currency_amounts', '').split(',') if x]
                ratio_values = [float(x) for x in document_metadata.get('percentages', '').split(',') if x]
                if monetary_values or ratio_values:
                    metrics_description = f"\nMetrics found: {len(monetary_values)} currency amounts, {len(ratio_values)} percentages"
            
            categorized_data[entity_symbol].append({
                'content': document_content,
                'filing_type': document_type,
                'filing_date': document_date,
                'section': content_section,
                'metrics_summary': metrics_description
            })
        
        return dict(categorized_data)

    def execute_interactive_session(self) -> None:
        while True:
            print("\nAvailable company groups:")
            print("1. Tech companies (AAPL, MSFT, GOOGL, META, AMZN)")
            print("2. Financial companies (JPM, BAC, GS, MS, WFC)")
            print("3. All companies")
            
            group_selection = input("\nSelect company group (1/2/3): ").strip()
            
            if group_selection == "1":
                selected_entities = self.technology_entities
            elif group_selection == "2":
                selected_entities = self.banking_entities
            else:
                selected_entities = self.technology_entities + self.banking_entities
            
            print("\nAvailable filing types:")
            print("1. 10-K (Annual reports)")
            print("2. 10-Q (Quarterly reports)")
            print("3. 8-K (Current reports)")
            print("4. All filing types")
            
            filing_selection = input("\nSelect filing type (1/2/3/4): ").strip()
            
            if filing_selection == "1":
                selected_categories = ["10-K"]
            elif filing_selection == "2":
                selected_categories = ["10-Q"]
            elif filing_selection == "3":
                selected_categories = ["8-K"]
            else:
                selected_categories = ["10-K", "10-Q", "8-K"]
            
            user_inquiry = input("\nEnter your question: ").strip()
            
            print(f"\nAnalyzing: {user_inquiry}")
            print(f"Context: Analysis for {', '.join(selected_entities)}")
            
            analysis_results = self.investigate_subject(
                subject_matter=user_inquiry,
                target_entities=selected_entities,
                document_categories=selected_categories
            )
            
            if analysis_results:
                print("\nKey findings by company:")
                for entity, insights in analysis_results.items():
                    print(f"\n{entity}:")
                    for i, insight in enumerate(insights, 1):
                        print(f"\nInsight {i} ({insight['filing_type']} - {insight['filing_date']}):")
                        print(f"Section: {insight['section']}")
                        print(f"- {insight['content'][:500]}...")
                        if insight['metrics_summary']:
                            print(insight['metrics_summary'])
            else:
                print("\n! No relevant information found")
            
            print("-" * 80)
            
            if input("\nWould you like to ask another question? (y/n): ").lower().strip() != 'y':
                break


def main():
    try:
        analysis_engine = FilingAnalysisEngine()
        analysis_engine.retrieve_and_analyze_data()
        analysis_engine.execute_interactive_session()
        
    except Exception as e:
        print(f"\nError during analysis: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return
    
    print("\n✓ Analysis completed successfully!")


if __name__ == "__main__":
    main()