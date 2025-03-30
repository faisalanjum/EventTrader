from utils.feature_flags import VALID_FORM_TYPES, FORM_TYPES_REQUIRING_XML, FORM_TYPES_REQUIRING_SECTIONS

from pydantic import BaseModel, field_validator, model_validator
from typing import List, Optional, Dict, Any
from datetime import datetime
import pytz



class Entity(BaseModel):
    """Entity model for SEC filings"""
    cik: Optional[str] = None 
    companyName: Optional[str] = None    
    irsNo: Optional[str] = None
    stateOfIncorporation: Optional[str] = None
    fiscalYearEnd: Optional[str] = None
    sic: Optional[str] = None
    type: Optional[str] = None
    act: Optional[str] = None
    fileNo: Optional[str] = None
    filmNo: Optional[str] = None
    undefined: Optional[str] = None  # Typically has this info '01 Energy &amp; Transportation)' or '06 Technology)' etc


class UnifiedReport(BaseModel):
    """Unified report model for SEC filings"""
    
    # Required fields
    formType: str
    cik: str
    filedAt: str
    # primary_document_url: str
    primaryDocumentUrl: str
    accessionNo: str
    is_xml: bool

    # Identification
    id: Optional[str] = None
    description: Optional[str] = None
    
    # Company info
    ticker: Optional[str] = None
    companyName: Optional[str] = None
    entities: Optional[List[Entity]] = []
    # Timing
    periodOfReport: Optional[str] = None
    effectivenessDate: Optional[str] = None
    
    # Document links
    linkToTxt: Optional[str] = None
    linkToHtml: Optional[str] = None
    linkToFilingDetails: Optional[str] = None
    exhibits: Dict[str, str] = {}  # Only EX-10.* and EX-99.*
    items: Optional[List[str]] = None  # For 8-K items
    

    
    def print(self):
        """Print unified report format"""
        print("\n" + "="*80)
        print(f"Form Type: {self.formType}")
        print(f"CIK: {self.cik}")
        print(f"Filed At: {self.filedAt}")
        print(f"Company: {self.companyName}")
        print(f"Ticker: {self.ticker}")
        print(f"\nPrimary Document URL: {self.primaryDocumentUrl}")
        if self.exhibits:
            print("\nExhibits:")
            for ex_type, url in self.exhibits.items():
                print(f"  {ex_type}: {url}")
        print("="*80 + "\n")





class DocumentFile(BaseModel):
    """Document file model for SEC filings"""
    sequence: Optional[str] = None
    documentUrl: Optional[str] = None
    type: Optional[str] = None
    size: Optional[str] = None
    description: Optional[str] = None


class ClassContract(BaseModel):
    """Class/Contract information within a series"""
    classContract: Optional[str] = None
    name: Optional[str] = None
    ticker: Optional[str] = None

class SeriesInfo(BaseModel):
    """Series information with its contracts"""
    series: Optional[str] = None  # series_id
    name: Optional[str] = None    # series_name
    classesContracts: Optional[List[ClassContract]] = []



class SECFilingSchema(BaseModel):
    """Raw SEC WebSocket filing model"""
    ticker: Optional[str] = None

    id: str
    accessionNo: str
    cik: str
    formType: str
    filedAt: str
    
    companyName: Optional[str] = None
    companyNameLong: Optional[str] = None

    description: Optional[str] = None
    linkToTxt: Optional[str] = None
    linkToHtml: Optional[str] = None
    linkToXbrl: Optional[str] = None
    linkToFilingDetails: Optional[str] = None
    
    # Extract Entity information
    entities: Optional[List[Entity]] = []

    # Extract Documents  & dataFiles (both have same structure)
    documentFormatFiles: Optional[List[DocumentFile]] = []
    dataFiles: Optional[List[DocumentFile]] = []

    # Extract seriesAndClassesContractsInformation
    seriesAndClassesContractsInformation: Optional[List[SeriesInfo]] = []

    periodOfReport: Optional[str] = None
    effectivenessDate: Optional[str] = None

    # Add these fields
    items: Optional[List[str]] = None  # For 8-K items
    # groupMembers: Optional[List[str]] = None  # For SC 13G/D filings
    # registrationForm: Optional[str] = None
    # referenceAccessionNo: Optional[str] = None

    class Config:
        extra = 'ignore'

    # Convert all fields to strings
    # @field_validator('*')
    # def convert_to_string(cls, v: Any, info) -> Any:
    #     """Convert fields to strings, except for lists"""
    #     if isinstance(v, (list, dict)):  # Preserve lists and dicts
    #         return v
    #     return str(v) if v is not None else ''
    

    # @field_validator('formType')
    # def validate_form_type(cls, v):
    #     if v not in VALID_FORM_TYPES:
    #         raise ValueError(f"Form type must be one of {VALID_FORM_TYPES}")
    #     return v
    
    @field_validator('filedAt')
    def validate_filed_at(cls, v):
        """Validate filed_at timestamp
        Format: YYYY-MM-DD HH:mm:SS TZ
        Always in Eastern Time (ET)
        Summer (EDT): -04:00
        Winter (EST): -05:00
        """
        if not v:
            raise ValueError("Filedat timestamp cannot be empty")
        try:
            dt = datetime.fromisoformat(v)
            if dt.tzinfo is None:
                raise ValueError("Timestamp must include timezone")
            
            # Add future date check
            now = datetime.now(pytz.UTC)
            if dt > now:
                print(f"[Warning] Future filing date detected: {dt}")  # Log but don't reject
                
            return dt.astimezone(pytz.UTC).isoformat()
        except ValueError:
            raise ValueError(f"Invalid timestamp format: {v}")


    def _get_xml_url(self) -> str:
        if not self.dataFiles:  # Guard against empty dataFiles
            return None
        
        print(f"[Debug] dataFiles type: {type(self.dataFiles)}")
        print(f"[Debug] First dataFile type: {type(self.dataFiles[0])}")
        
        xml_url = next((f.documentUrl for f in self.dataFiles if f.type == 'XML' and f.documentUrl), None)
        return xml_url

    def _get_exhibits(self) -> Dict[str, str]:
        if not self.documentFormatFiles:
            return {}
        
        print(f"[Debug] documentFormatFiles type: {type(self.documentFormatFiles)}")
        print(f"[Debug] First documentFormatFile type: {type(self.documentFormatFiles[0])}")
        
        return { doc.type: doc.documentUrl
            for doc in self.documentFormatFiles
            if (doc.type and doc.documentUrl and doc.type.startswith(('EX-10.', 'EX-99.')))
        }

    def to_unified(self) -> UnifiedReport:
        """Convert to unified format with proper validation"""
        
        # Get XML URL (will be None if not found)
        xml_url = self._get_xml_url()
        
        # Rule 1: Forms requiring XML
        if self.formType in FORM_TYPES_REQUIRING_XML:
            if not xml_url:
                raise ValueError(f"No XML URL found for {self.formType}")
            primary_url = xml_url
            is_xml = True
            
            # Rule 2: Forms with optional XML (8-K types)
        else:
            primary_url = xml_url if xml_url else self.linkToTxt
            is_xml = xml_url is not None

        if not primary_url:  # ✅ Add this check
            raise ValueError(f"No document URL found for filing {self.accessionNo}")
        
        # Get exhibits (EX-10.x and EX-99.x)
        exhibits = self._get_exhibits()

        # entities associated with filing
        entities = self.entities if self.entities else None

        # This is already correct since "first entity in the entities array is always the primary filing issuer"
        self.cik = self.entities[0].cik if self.entities else self.cik

        return UnifiedReport(
            # Required fields
            formType=self.formType,
            cik=self.cik, # Primary filing issuer
            filedAt=self.filedAt,
            primaryDocumentUrl=primary_url,
            accessionNo=self.accessionNo,
            is_xml=is_xml,
            
            # Identification
            id=self.id,
            description=self.description,
            
            # Company info
            ticker=None, # ReportProcessor will set it
            companyName=self.companyName,
            entities=entities, 
            
            # Timing
            periodOfReport=self.periodOfReport,
            effectivenessDate=self.effectivenessDate,
            
            # Document links
            linkToTxt=self.linkToTxt,
            linkToHtml=self.linkToHtml,
            linkToFilingDetails=self.linkToFilingDetails,
            exhibits=exhibits,
            # 8-K items
            items=self.items,  # Add this line
        )
    


    def print(self):
        """Print raw filing format"""
        print("\n" + "="*80)
        print(f"ID: {self.id}")
        print(f"Accession No: {self.accessionNo}")
        print(f"CIK: {self.cik}")
        print(f"Company: {self.companyName}")
        print(f"Form Type: {self.formType}")
        print(f"Filed At: {self.filedAt}")
        print(f"Description: {self.description}")
        
        if self.entities:
            print("\nEntities:")
            for entity in self.entities:
                print(f"  - {entity.companyName} (CIK: {entity.cik})")
        
        if self.documentFormatFiles:
            print("\nDocument Files:")
            for doc in self.documentFormatFiles:
                print(f"  - Type: {doc.type}")
                print(f"    URL: {doc.documentUrl}")
        
        print("="*80 + "\n")    