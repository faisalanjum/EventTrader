

**Flow**


**Categories of Nodes:**
1. Macro or Common Nodes
    - Concept
    - Abstract
    - PureAbstract
    - Unit
    - Period
    - Date
    - AdminReport
    
2. Company Specific Nodes
    - Context 
    - Company
    - Dimension
    - Member
    
3. Instance or Report Specific Nodes
    - Report
    - Fact
    - Guidance (ToDo)
    - News (ToDo)
    - Footnote (ToDo)



# Node Unique Identifiers (u_id)

## 1. Common/Macro Nodes
| Node Type    | Generic Format                  | Example                                                     |
|-------------|--------------------------------|---------------------------------------------------------------|
| Concept     | `namespaceURI:qname`           | `http://fasb.org/us-gaap/2023:us-gaap:OperatingLeasePayments` |
| Abstract    | `namespaceURI:qname`           | `http://fasb.org/us-gaap/2023:us-gaap:DisclosureAbstract`     |
| Unit        | `namespace_stringvalue`        | `http://www.xbrl.org/2003/iso4217_iso4217:USD`                |
| Period      | `period_type_startdate_enddate`| `duration_2023-10-01_2024-10-01` or `instant_2024-01-28` or forever    
| Date        | `YYYY-MM-DD`                   | `2024-01-28`                                                  |
| AdminReport | `report_code`                  | `10-K` or `10-Q`                                              |

## 2. Company-Specific Nodes
| Node Type  | Generic Format                                   | Example                                                             |
|------------|--------------------------------------------------|---------------------------------------------------------------------|
| Company    | `cik` (10 digits)                                | `0000003545`                                                        |
| Context    | `hash(cik_perioduid_dim1uid_dim2uid_mem1uid)`    | `558673591988726742`                                                |
| Dimension  | `company_id:namespaceURI:qname`                  | `3545:http://fasb.org/us-gaap/2023:us-gaap:SubsequentEventTypeAxis` |
| Member     | `company_id:namespaceURI:qname`                  | `3545:http://fasb.org/us-gaap/2023:us-gaap:OperatingSegmentsMember` |
| Domain     | `company_id:namespaceURI:qname`                  | `3545:http://fasb.org/us-gaap/2023:us-gaap:SubsequentEventTypeDomain` |

## 3. Instance/Report-Specific Nodes
| Node Type  | Generic Format                                | Example                                                    |
|------------|----------------------------------------------|-------------------------------------------------------------|
| Report     | `cik_doctype_date`      (??InstanceFile??)   | `0000003545_10-K_2024-01-28`                                |
| Fact       | `documenturi_conceptqname_contextID_unitID_factID` | `alco-20240930.htm_us-gaap:CommonStock_c-4_usd_f-90`  |

## Notes:
1. All namespace URIs are consistent within a taxonomy version
2. Company-specific nodes include CIK in their identifiers
3. Context IDs are hashed combinations of multiple components
4. Report-specific nodes include document information


# Relationship Uniqueness Constraints:
- **The uniqueness is enforced in the MERGE clause** 

1. **Calculation Edge:** 
    - cik,                # Company identity
    - report_id,          # Specific filing
    - network_name,       # Network context
    - parent_id,          # Parent concept
    - child_id,           # Child concept
    - context_id          # Full context including dimensions

2. **Presentation Edge:** A presentation/calculation relationship is considered unique if it has the same:
    - cik,                # Company identity
    - report_id,          # Specific filing
    - network_name,       # Network context
    - parent_id,          # Parent concept
    - child_id,           # Child concept
    - parent_level,       # Position in hierarchy
    - child_level         # Position in hierarchy



**Fact Validation Notes:**
    - The closed attribute is set once at the top-level has-hypercube relationship and all descendant concepts inherit this same value through domain-member relationships - they cannot have different values for the same hypercube


**Neo4j Notes:**
    - To set the displayLabel property for a node in Neo4j, use the following Cypher query:
      :style node { label: 'Date'; text-property: 'displayLabel';}


**Presentation Networks:**
    - Note when displaying Presentation Networks, first groupby Period_id and then inside that groupby Context_id and show the facts by Period_id (inside each context_id)


**Relationships Edges in Neo4j**
1. "HAS_CONCEPT"
2. "HAS_UNIT"
3. "HAS_PERIOD"
4. "HAS_MEMBER"
5. "HAS_DOMAIN"
6. "PARENT_OF"
7. "NEXT"
8. "HAS_PRICE"
9. "HAS_SUB_REPORT"
10. "BELONGS_TO"
11.  "REPORTED_ON"
12. "HAS_DIMENSION"
13. "FACT_MEMBER"
14. "PRESENTATION_EDGE"
15. "IN_CONTEXT"
16. "CALCULATION_EDGE"


**KNOWN ISSUES:**
1. Invalid Calculation Edges (only few 15 out of 327) 
   - One reason is that we are grouping validated facts (from Presentation network) using context_id (which works most of the time) but sometimes for example in Balance sheet, summation is also done using 2 contexts (so grouping by period is required)

2. Some Facts are missing Contexts - check using Cypher Query (6 out of 3672)
4. Some Members are isolated in Neo4j - Not sure why?

**Handled:**
- 'Other' NodeType is created in create_indexes - Which is Fine as it's used as default fallback (_initial_classify)
- 'HyperCube' NodeType is created in create_indexes - Which is Fine as it's used for table structures determination in presentation hierarchy

**TODO:**
- Automatic creation of FOREVER PeriodNode (not sure why there is none created)
- 