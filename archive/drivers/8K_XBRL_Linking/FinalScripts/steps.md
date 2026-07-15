1. LangXtract
    - Need to understand how to pass XBRL schema (for a specific Company - create XBRL )
    - Idea is each fact reported in a report needs to be fetched out along with its corresponding XBRL terminology
        1 concept
        2 period
        3 context
        4 member
        5 dimension
        6 domain
        7 unit
        8 gaap_item/ qname of concept?

2. **PROMPT for LangXtract**
  Extract financial facts from SEC filings for {ticker}.

  CRITICAL MATCHING RULES:
  1. Extract EXACT text spans (do not paraphrase)
  2. Match each extraction to a qname from the XBRL CONCEPTS list in the context
  3. Use ONLY qnames that appear in the list - NEVER invent or modify qnames
  4. If no concept matches, use: matched_qname: "UNMATCHED"
  5. Use the historical values in the list to validate your extraction:
     - If your extracted value is wildly different from recent values, lower confidence
     - If your extracted value follows reasonable growth/decline patterns, higher confidence

  REQUIRED ATTRIBUTES FOR EACH EXTRACTION:
  - matched_qname: Exact qname string from the list (or "UNMATCHED")
  - value: Raw numeric value (e.g., 24400000000, not "$24.4 billion")
  - period: Reporting period as stated in text
  - confidence: Float 0.0-1.0 based on match quality AND value reasonableness
  - reasoning: Brief explanation of confidence score
  """

3.       # =========================================================================
      # MAIN EXTRACTION
      # =========================================================================

      def extract(self, text: str, ticker: str) -> list[dict]:
          """
          Single-pass extraction with XBRL schema matching.
          """
          # Get XBRL context from Neo4j
          xbrl_context, valid_qnames = self.get_xbrl_context(ticker)

          if not valid_qnames:
              raise ValueError(f"No XBRL data found for {ticker}")

          # Run LangExtract with schema context
          result = lx.extract(
              text_or_documents=text,
              prompt_description=self.get_prompt(ticker),
              examples=self.get_examples(),
              additional_context=xbrl_context,  # ← Schema injection
              model_id="gemini-2.5-flash",
              extraction_passes=2,              # Multiple passes for recall
              max_workers=10,
              max_char_buffer=2000,
              temperature=0.1                   # Low temp = less hallucination
          )

          # Process results with validation
          extractions = []
          for ext in result.extractions:
              attrs = ext.attributes or {}
              matched_qname = attrs.get("matched_qname", "UNMATCHED")

              # Validate qname exists in our list
              qname_valid = matched_qname in valid_qnames or matched_qname == "UNMATCHED"

              extractions.append({
                  "extraction_text": ext.extraction_text,
                  "char_start": ext.char_interval.start_pos if ext.char_interval else None,
                  "char_end": ext.char_interval.end_pos if ext.char_interval else None,
                  "matched_qname": matched_qname,
                  "qname_valid": qname_valid,  # ← Post-validation flag
                  "value": attrs.get("value"),
                  "period": attrs.get("period"),
                  "confidence": attrs.get("confidence"),
                  "reasoning": attrs.get("reasoning")
              })

          return extractions, valid_qnames  # Return valid_qnames for downstream use


4. How to test 

how to test the full pipeline:

  cd /home/faisal/EventMarketDB/drivers/8K_XBRL_Linking/FinalScripts

  # 1. UNIT TESTS (no dependencies needed)
  python3 test_pipeline.py --unit

  # 2. POSTPROCESSOR TEST (no dependencies needed)  
  python3 test_pipeline.py --postprocess

  # 3. CATALOG TEST (requires: pip install python-dotenv neo4j)
  python3 test_pipeline.py --catalog DELL

  # 4. FULL PIPELINE (requires: pip install langextract python-dotenv neo4j)
  python3 test_pipeline.py --extract DELL

  # Or with a custom 8-K file:
  python3 test_pipeline.py --extract DELL --file /path/to/8k.txt

  Dependencies needed:
  pip install python-dotenv neo4j langextract

  Files in FinalScripts:
  | File                 | Purpose               |
  |----------------------|-----------------------|
  | extraction_schema.py | Data classes          |
  | extraction_config.py | Prompt + examples     |
  | postprocessor.py     | Validation + parsing  |
  | extractor.py         | Orchestration wrapper |
  | xbrl_catalog.py      | Neo4j catalog fetch   |
  | test_pipeline.py     | Test script  


5.

A few easy options to view the HTML on your Mac:

  Option 1: SCP the file to your Mac (simplest)
  # Run this on your Mac terminal (not SSH session)
  scp faisal@192.168.40.73:/home/faisal/EventMarketDB/drivers/8K_XBRL_Linking/output/DELL_8K_20251226_122044.html ~/Desktop/

  # Then open it
  open ~/Desktop/DELL_8K_20251226_122044.html


