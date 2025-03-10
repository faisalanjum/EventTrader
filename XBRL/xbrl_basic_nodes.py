"""
This module contains basic node implementations for the XBRL module.
These have been extracted from XBRLClasses.py to improve maintainability.
"""

# Import common dependencies
from .common_imports import *

# Import from core module
from .xbrl_core import Neo4jNode, NodeType, RelationType, GroupingType

from arelle.ModelInstanceObject import ModelFact, ModelContext


@dataclass
class Context(Neo4jNode):
    context_id: str
    cik: str  # This should match CompanyNode's cik
    period_u_id: str
    dimension_u_ids: List[str] = field(default_factory=list)
    member_u_ids: List[str] = field(default_factory=list)
    u_id: str = field(init=False)

    def __post_init__(self):
        self.generate_id()

    def __hash__(self):
        return hash(self.u_id)

    def __eq__(self, other):
        if isinstance(other, Context):
            return self.u_id == other.u_id
        return False


    def generate_id(self):
        """Generate a unique ID for the context based on company, period, and dimensional qualifiers"""
        # Clean and prepare components that define context's semantic identity
        components = [
            # str(self.context_id).strip(),             # Removed ID as it's report-specific but we are making context company-specific
            str(self.cik).strip(),                    # Company identifier
            str(self.period_u_id).strip(),            # Period identifier
            "_".join(sorted(self.dimension_u_ids)) if self.dimension_u_ids else "no_dims",  # Dimensional qualifiers
            "_".join(sorted(self.member_u_ids)) if self.member_u_ids else "no_mems"        # Member values
        ]
        
        # Join components and create hash
        unique_key = "_".join(filter(None, components))
        self.u_id = str(abs(hash(unique_key)))  # Using abs() to avoid negative numbers
        
        # Debug print
        # print(f"\nContext ID Components:")
        # print(f"1. CIK: {self.cik}")
        # print(f"2. Period ID: {self.period_u_id}")
        # print(f"3. Dimensions: {self.dimension_u_ids or 'no_dims'}")
        # print(f"4. Members: {self.member_u_ids or 'no_mems'}")
        # print(f"Final u_id: {self.u_id}")


    # Neo4j Node Properties
    @property
    def node_type(self) -> NodeType:
        return NodeType.CONTEXT

    @property
    def id(self) -> str:
        return self.u_id

    @property
    def properties(self) -> Dict[str, Any]:
        return {
            "u_id": self.id,
            "context_id": self.context_id,
            "cik": self.cik,
            "period_u_id": self.period_u_id,
            "dimension_u_ids": self.dimension_u_ids,
            "member_u_ids": self.member_u_ids
        }




@dataclass
class Period(Neo4jNode):
    period_type: str  # Required field, no default
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    # context_ids: List[str] = field(default_factory=list)
    context_ids: Optional[List[str]] = field(default_factory=list)  # Optional, defaults to an empty list
    u_id: str = field(init=False)

    def __post_init__(self):
        if self.period_type == "duration" and not (self.start_date and self.end_date):
            raise ValueError("Duration periods must have both start and end dates")
        if self.period_type == "instant" and not self.start_date:
            raise ValueError("Instant periods must have a start date")
        self.generate_id()

    def __hash__(self):
        return hash(self.u_id)

    def __eq__(self, other):
        if isinstance(other, Period):
            return self.u_id == other.u_id
        return False

    @property
    def is_duration(self) -> bool:
        return self.start_date is not None and self.end_date is not None

    @property
    def is_instant(self) -> bool:
        return self.start_date is not None and self.end_date is None

    def generate_id(self):
        """Generate a unique ID for the period."""
        id_parts = [self.period_type]
        if self.start_date:
            id_parts.append(self.start_date)
        if self.end_date:
            id_parts.append(self.end_date)
        self.u_id = "_".join(id_parts)

    # Neo4j Node Properties
    @property
    def node_type(self) -> NodeType:
        return NodeType.PERIOD
        
    @property
    def id(self) -> str:
        return self.u_id
        
    @property
    def properties(self) -> Dict[str, Any]:
        return {
            "u_id": self.id,# This returns u_id
            "period_type": self.period_type,
            "start_date": self.start_date,
            "end_date": self.end_date
            # "context_ids": self.context_ids # TODO: Add this back in relation to Facts but after adding report_metadata
        }

    def merge_context(self, context_id: str) -> None:
        """Add a context ID if it's not already present"""
        if context_id not in self.context_ids:
            self.context_ids.append(context_id)



@dataclass
class Unit(Neo4jNode):
    """ Units are uniquely identified by their string_value (e.g. 'iso4217:USD', 'shares').
    Non-numeric facts have no unit information and as such excluded from Unit nodes."""
        
    model_fact: Optional[ModelFact] = None
    u_id: Optional[str] = None
    
    # All these will be set in post_init
    string_value: Optional[str] = None
    is_divide: Optional[bool] = None
    unit_reference: Optional[str] = None
    registry_id: Optional[str] = None
    is_simple_unit: Optional[bool] = None
    item_type: Optional[str] = None
    namespace: Optional[str] = None
    status: Optional[str] = None

    def __post_init__(self):
        """Process the model_fact to initialize all unit attributes"""
        if self.model_fact is None:  # Skip if loading from Neo4j
            return
        
        unit = getattr(self.model_fact, 'unit', None)
        self.is_divide = getattr(unit, "isDivide", None)
        self.string_value = getattr(unit, "stringValue", None)
        self.unit_reference = self._normalize_unit_id(self.model_fact.unitID)
        
        # Process UTR entries
        utr_entry = next(iter(self.model_fact.utrEntries), None) if self.model_fact.utrEntries else None
        self.registry_id = getattr(utr_entry, "id", None)
        self.is_simple_unit = getattr(utr_entry, "isSimple", None)
        self.item_type = getattr(utr_entry, "itemType", None)
        self.namespace = getattr(utr_entry, "nsUnit", None)
        self.status = getattr(utr_entry, "status", None)
        
        self.u_id = self.generate_uid() # UTR ID + String Value

    def generate_uid(self):
        # Defensive cleaning - handle any possible input
        clean_ns = str(self.namespace).strip() if self.namespace is not None else ""
        clean_val = str(self.string_value).strip() if self.string_value is not None else ""
        
        # If we have both, combine them
        if clean_ns and clean_val:
            return f"{clean_ns}_{clean_val}"
        # If we only have value, return it
        elif clean_val:
            return clean_val
        # If neither, return None
        return None
            

    def __hash__(self):
        """Enable using Unit objects in sets and as dict keys"""
        return hash(self.u_id)

    def __eq__(self, other):
        """Enable comparison between Unit objects"""
        if isinstance(other, Unit):
            return self.u_id == other.u_id
        return False

    @staticmethod
    def _normalize_unit_id(unit_id: Any) -> Optional[str]:
        if not unit_id:
            return None
        if isinstance(unit_id, str) and unit_id.startswith("u-"):
            return unit_id
        if hasattr(unit_id, "id"):
            return f"u-{unit_id.id}"
        return f"u-{abs(hash(str(unit_id))) % 10000}"

    @property
    def is_simple(self) -> bool:
        """Check if the unit is a simple unit based on registry data"""
        return bool(self.is_simple_unit)
    
    @property
    def is_registered(self) -> bool:
        """Check if the unit is registered in UTR"""
        return self.registry_id is not None
    
    @property
    def is_active(self) -> bool:
        """Check if the unit is active based on status"""
        return self.status == "active" if self.status else False

    # Neo4j Node Properties
    @property
    def node_type(self) -> NodeType:
        """Define the Neo4j node type"""
        return NodeType.UNIT
        
    @property
    def id(self) -> str:
        """u_id for Neo4j"""
        return self.u_id
        
    @property
    def properties(self) -> Dict[str, Any]:
        """Actual node properties in Neo4j"""
        return {
            "id": self.id,
            "name": self.string_value,  # Using string_value as name
            "is_divide": self.is_divide,
            "is_simple_unit": self.is_simple_unit,
            "item_type": self.item_type,
            "namespace": self.namespace,
            "registry_id": self.registry_id,
            "status": self.status,
            # "string_value": self.string_value,
            "u_id": self.u_id,
            "unit_reference": self.unit_reference
        }

 
    def __repr__(self) -> str:
        """String representation of the Unit"""
        return f"Unit(id={self.id}, type={self.item_type or 'unknown'})"  # Changed self._id to self.id
    




@dataclass
class AdminReportNode(Neo4jNode):
    code: str          # e.g., "10-K_FYE-1231", "10-Q_Q1", "8-K"
    label: str         # e.g., "Annual Report (December)", "Q1 Report"
    category: str      # e.g., "10-K", "10-Q", "8-K"
    
    @property
    def node_type(self) -> NodeType:
        return NodeType.ADMIN_REPORT
        
    @property
    def id(self) -> str:
        return self.code
        
    @property
    def properties(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "label": self.label,
            "category": self.category,
            "displayLabel": self.label
        }



@dataclass
class CompanyNode(Neo4jNode):
    cik: str
    name: Optional[str] = None  # Check if it matters to make it Optional
    ticker: Optional[str] = None
    exchange: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    fiscal_year_end: Optional[str] = None

    # Add fields that may not be in the class definition but are accessed in properties method
    cusip: Optional[str] = None
    figi: Optional[str] = None
    class_figi: Optional[str] = None
    sic: Optional[str] = None
    sic_name: Optional[str] = None
    sector_etf: Optional[str] = None
    industry_etf: Optional[str] = None
    mkt_cap: Optional[float] = None
    employees: Optional[int] = None
    shares_out: Optional[float] = None
    ipo_date: Optional[str] = None


    def __post_init__(self):
        # Ensure CIK is properly formatted (10 digits with leading zeros)
        self.cik = self.cik.zfill(10)
        
    def display(self):
        """Returns display name for the entity"""
        if self.ticker:
            return f"{self.name} ({self.ticker})"
        return self.name

    @property
    def node_type(self) -> NodeType:
        return NodeType.COMPANY

    @property
    def id(self) -> str:
        """Use CIK as unique identifier"""
        return self.cik

    @property
    def properties(self) -> Dict[str, Any]:
        """
        Returns properties for Neo4j node
        Filters out None values to keep the node clean
        """
        props = {
            'id': self.id,
            'cik': self.cik,
            'name': self.name,
            'displayLabel': self.display()
        }
        
        # Add optional properties if they exist
        optional_props = {
            'ticker': self.ticker,
            'exchange': self.exchange,
            'sector': self.sector,
            'industry': self.industry,
            'cusip': self.cusip,
            'figi': self.figi,
            'class_figi': self.class_figi,
            'sic': self.sic,
            'sic_name': self.sic_name,
            'sector_etf': self.sector_etf,
            'industry_etf': self.industry_etf,
            'mkt_cap': self.mkt_cap,
            'employees': self.employees,
            'shares_out': self.shares_out,
            'ipo_date': self.ipo_date,
            'fiscal_year_end': self.fiscal_year_end
        }
        
        # Only include non-None optional properties
        props.update({k: v for k, v in optional_props.items() if v is not None})
        
        return props
        
    @classmethod
    def from_neo4j(cls, props: Dict[str, Any]) -> 'CompanyNode':
        """Create CompanyNode from Neo4j properties"""
        # Required field
        if 'cik' not in props:
            raise ValueError("Missing required field 'cik' for CompanyNode")
        
        # Initialize with required fields
        company = cls(cik=props['cik'])
        
        # Map neo4j properties to attributes
        field_mappings = {
            'name': 'name',
            'ticker': 'ticker',
            'exchange': 'exchange',
            'sector': 'sector',
            'industry': 'industry',
            'fiscal_year_end': 'fiscal_year_end',
            'cusip': 'cusip',
            'figi': 'figi',
            'class_figi': 'class_figi',
            'sic': 'sic',
            'sic_name': 'sic_name',
            'sector_etf': 'sector_etf',
            'industry_etf': 'industry_etf',
            'ipo_date': 'ipo_date'
        }
        
        # Set string and simple fields
        for neo4j_field, attr_name in field_mappings.items():
            if neo4j_field in props and props[neo4j_field] not in (None, "", "null"):
                setattr(company, attr_name, props[neo4j_field])
        
        # Handle numeric fields with special parsing
        if 'mkt_cap' in props and props['mkt_cap'] not in (None, "", "null"):
            try:
                mkt_cap_value = props['mkt_cap']
                if isinstance(mkt_cap_value, (int, float)):
                    company.mkt_cap = float(mkt_cap_value)
                else:
                    # Try to clean the string if it contains commas, etc.
                    clean_val = str(mkt_cap_value).replace(',', '').replace('$', '').strip()
                    company.mkt_cap = float(clean_val)
            except (ValueError, TypeError):
                pass
        
        if 'employees' in props and props['employees'] not in (None, "", "null"):
            try:
                employees_value = props['employees']
                if isinstance(employees_value, (int, float)):
                    company.employees = int(employees_value)
                else:
                    # Try to clean the string if it contains commas, etc.
                    clean_val = str(employees_value).replace(',', '').strip()
                    company.employees = int(float(clean_val))
            except (ValueError, TypeError):
                pass
        
        if 'shares_out' in props and props['shares_out'] not in (None, "", "null"):
            try:
                shares_value = props['shares_out']
                if isinstance(shares_value, (int, float)):
                    company.shares_out = float(shares_value)
                else:
                    # Try to clean the string if it contains commas, etc.
                    clean_val = str(shares_value).replace(',', '').strip()
                    company.shares_out = float(clean_val)
            except (ValueError, TypeError):
                pass
        
        return company




@dataclass
class DateNode(Neo4jNode):
    year: int
    month: int
    day: int

    def __post_init__(self):
        self.date = datetime(self.year, self.month, self.day)

    def display(self):
        return self.date.strftime("%Y-%m-%d")
        
    @property
    def node_type(self) -> NodeType:
        return NodeType.DATE
        
    @property
    def id(self) -> str:
        return self.display()
        
    @property
    def properties(self) -> Dict[str, Any]:
        return {
            'id': self.display(),
            'year': self.year,
            'month': self.month,
            'day': self.day,
            'quarter': f"Q{(self.month-1)//3 + 1}",
            'displayLabel': self.display() 
        }



@dataclass
class ReportNode(Neo4jNode):
    # source: https://sec-api.io/docs/query-api
    formType: str
    periodEnd: str          # event date for 8-K, period end for 10-K/Q
    isAmendment: bool
    instanceFile: str       # instance file name - sec_api - maybe able to get it from dataFiles field in sec_api 
    cik: str                                             # Change this to Ticker when moving to sec_api
    
    # TODO: Will be supplied by sec-api 
    filedAt: Optional[str] = "2024-12-02T16:06:24-04:00"

    # TODO: Will be supplied by sec-api 
    accessionNo: Optional[str] = None
    periodOfReport: Optional[str] = None     # official filing period date

    # for admin purposes
    insertedAt: Optional[str] = field(default_factory=lambda: datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    status: Optional[bool] = False           # Once a report has been uploaded, make this True

    def __post_init__(self):
        self.cik = self.cik.zfill(10)
        self.period_date = datetime.strptime(self.periodEnd, '%Y-%m-%d')
    
    def get_fiscal_period(self) -> str:
        """Get fiscal period (Q1-Q4 or FYE MM/DD)"""
        month = self.period_date.month
        if self.formType == "10-K":
            return f"FYE {month:02d}/31"
        return f"Q{(month-1)//3 + 1}"
    
    def find_matching_sub_report(self, parent: AdminReportNode) -> AdminReportNode:
        """Find matching sub-report based on period end date"""
        sub_reports = [n for n in self.admin_reports 
                      if n.category == parent.code]
        return min(sub_reports, 
                  key=lambda x: abs(x.get_date() - self.period_date))

        
    def display(self) -> str:
        """Returns display name for the report"""
        date = datetime.strptime(self.periodEnd, '%Y-%m-%d')
        amendment = "A" if self.isAmendment else ""
        period = ("8K" if self.formType == "8-K" else
                 f"Q{(date.month - 1) // 3 + 1}" if self.formType == "10-Q" 
                 else f"FY{date.year}")
        # return f"{self.cik}_{date.year}_{period}{amendment}" # Later use Ticker when we have sec-api
        return f"{date.year}_{period}{amendment}" # Later use Ticker when we have sec-api
        
        
    @property
    def node_type(self) -> NodeType:
        """Returns node type for Neo4j"""
        return NodeType.REPORT
        
    @property
    def id(self) -> str:
        """Use instanceFile as unique identifier"""
        return self.instanceFile
        
    @property
    def properties(self) -> Dict[str, Any]:
        """Returns properties for Neo4j node"""
        props = {
            'id': self.id,
            'formType': self.formType,
            'periodEnd': self.periodEnd,
            'isAmendment': self.isAmendment,
            'instanceFile': self.instanceFile,
            'filedAt': self.filedAt,
            'cik': self.cik,
            'displayLabel': self.display(),
            'insertedAt': self.insertedAt,
            'status': self.status
        }
        
        # Add optional properties if they exist
        optional_props = {
            'accessionNo': self.accessionNo,
            'periodOfReport': self.periodOfReport
        }
        
        # Only include non-None optional properties
        props.update({k: v for k, v in optional_props.items() if v is not None})
        
        return props    
