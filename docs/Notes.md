
**Categories of Nodes:**
1. Macro or Common Nodes
    - Concept
    - Unit
    - Period
    - Dates
2. Company Specific Nodes
    - Entity
    - Dimension
    - Member
3. Instance or Report Specific Nodes
    - Report
    - Fact
    - Guidance
    - News
    - Footnote


**Unique Identifiers (u_id) By Node:**

1. **Period Node:** period_type_startdate_enddate (duration_2023-10-01_2024-10-01, instant_2015-01-28, forever?)
2. **Unit Node:** namespace_stringvalue (http://www.xbrl.org/2003/iso4217_iso4217:USD)
3. **Concept Node:** namespaceURI:conceptqname (http://xbrl.sec.gov/dei/2023:dei:EntityAddressStateOrProvince, http://fasb.org/us-gaap/2023:us-gaap:OperatingLeasePayments)
4. **Fact Node:** Documenturi_conceptqname_contextID_unitID_factID (https://www.sec.gov/Archives/edgar/data/3545/000000354524000128/alco-20240930_htm.xml_us-gaap:CommonStockParOrStatedValuePerShare_c-4_usdPerShare_f-90)




**Fact Validation Notes:**
    - The closed attribute is set once at the top-level has-hypercube relationship and all descendant concepts inherit this same value through domain-member relationships - they cannot have different values for the same hypercube


**Neo4j Notes:**
    - To set the displayLabel property for a node in Neo4j, use the following Cypher query:
      :style node { label: 'Date'; text-property: 'displayLabel';}



    