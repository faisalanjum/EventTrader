from typing import List, Dict, Any
from typing_extensions import TypedDict
class AttributionState(TypedDict):
    company_ticker: str
    target_date: str
    events: List[Dict[str, Any]]
    result: Dict[str, Any]