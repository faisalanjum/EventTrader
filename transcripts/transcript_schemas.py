from pydantic import BaseModel
from typing import List, Dict, Optional, Any

class UnifiedTranscript(BaseModel):
    """Unified format for earnings call transcripts"""
    id: Optional[str] = None                # Make optional: Required by BaseProcessor
    symbols: Optional[List[str]] = None     # Make optional: Required by BaseProcessor
    created: Optional[str] = None           # Make optional: Required by BaseProcessor 
    updated: Optional[str] = None           # Make optional: Required by BaseProcessor
    formType: Optional[str] = None          # Make optional: Required by BaseProcessor
    
    # Essential transcript fields
    company_name: str
    fiscal_quarter: int
    fiscal_year: int
    calendar_quarter: Optional[int] = None
    calendar_year: Optional[int] = None
    conference_datetime: str
    fiscal_year_end_month: Optional[int] = 12
    fiscal_year_end_day: Optional[int] = 31

    # Ideally all should be made Optional
    speakers: Dict[str, str] = {}
    speaker_roles_LLM: Dict[str, str] = {}
    prepared_remarks: List[str] = []
    questions_and_answers: List[str] = []   
    qa_pairs: List[Dict[str, Any]] = []
    full_transcript: Optional[str] = None
    
    
    def print(self):
        """Print unified transcript format"""
        print("\n" + "="*80)
        print(f"ID: {self.id}")
        print(f"Symbol: {', '.join(self.symbols) if self.symbols else 'None'}")
        print(f"Company: {self.company_name}")
        print(f"Quarter: Q{self.fiscal_quarter} {self.fiscal_year}")
        print(f"Conference Date: {self.conference_datetime}")
        print(f"Speakers: {len(self.speakers)}")
        print(f"QA Pairs: {len(self.qa_pairs)}")
        print("="*80 + "\n") 