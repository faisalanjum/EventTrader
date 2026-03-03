# Slide Deck Ingestion from earningscall.biz

## Context

Earnings call slide decks (investor presentations) contain structured financial data, charts, and guidance that complements transcripts. The earningscall.biz API already supports `download_slide_deck()` (GET `/slides`) which downloads PDFs. The existing transcript pipeline (API → Redis → Neo4j) will be extended to also fetch, parse, and store slide decks alongside transcripts.

**User decisions:**
- PDF extraction: **Docling** (IBM open-source — layout analysis, table recognition, OCR)
- Pipeline: **Extend existing transcript pipeline** (not a separate pipeline)
- Embeddings: **Yes** (OpenAI text-embedding-3-large vectors for semantic search)
- API access: **Will purchase Slide Deck tier** (add feature flag + graceful 403 handling)

---

## DECIDED: PDF Chunking Strategy — Option B (Page-by-page)

**Status: Decided** — page-by-page chunking.

Each PDF page becomes a `SlidePageNode` linked to a parent `SlideDeckNode` via `HAS_SLIDE_PAGE`. The parent node also stores the full concatenated text for full-text queries.

**Why page-by-page:**
- Slide decks are designed as one topic per page — page boundaries ARE semantic boundaries
- Predictable chunk sizes (a few hundred to ~2000 chars per slide), always within embedding limits
- Enables fine-grained retrieval: "which slide mentioned services revenue guidance?"
- Mirrors the existing `QAExchangeNode` pattern exactly (child nodes with individual embeddings under a parent)
- Zero new heuristics — no minimum/maximum chunk size logic needed

**What Docling handles at ingestion:**
- Text, tables, bullet points, footnotes — full extraction per page
- OCR on text labels embedded in charts/images
- Does NOT interpret visual chart content (trends, comparisons) — that's done downstream by LLM at query time

**Implementation impact:** Adds `SlidePageNode` class + `HAS_SLIDE_PAGE` relationship type + a loop in processing to create per-page nodes. ~20 additional lines over the single-node approach.

---

## Step 1: Add dependencies

- `pip install docling` — PDF text/table extraction (requires Python 3.10+, project uses 3.11 ✓)
- `pip install pdf2image` — PDF page → PNG conversion (uses poppler, likely already installed on system)

**File:** `requirements.txt`

---

## Step 2: Feature flag for slide deck processing

Add to `config/feature_flags.py`:
```python
ENABLE_SLIDE_DECK_DOWNLOAD = False   # Toggle slide deck downloading (requires API plan)
ENABLE_SLIDE_DECK_EMBEDDINGS = False  # Generate embeddings on slide page text (deferred — enable after validating content quality)
SLIDE_DECK_STORAGE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "slide_decks")
SLIDE_DECK_IMAGE_DPI = 200           # PNG resolution (200 = readable, ~200-500KB per page)
SLIDE_DECK_EMBEDDING_BATCH_SIZE = 50  # Match NEWS/QAEXCHANGE batch sizes
SLIDEDECK_VECTOR_INDEX_NAME = "slidedeck_vector_idx"
```

**File:** `config/feature_flags.py`

---

## Step 3: Add NodeType and RelationType for slide decks

Add to the existing enums in `XBRL/xbrl_core.py`:
```python
# In NodeType enum:
SLIDE_DECK = "SlideDeck"
SLIDE_PAGE = "SlidePage"

# In RelationType enum:
HAS_SLIDE_DECK = "HAS_SLIDE_DECK"    # Transcript -> SlideDeck
HAS_SLIDE_PAGE = "HAS_SLIDE_PAGE"    # SlideDeck -> SlidePage
```

**File:** `XBRL/xbrl_core.py`

---

## Step 4: Add SlideDeckNode to EventTraderNodes.py

**Two node classes** — parent `SlideDeckNode` (full deck metadata + concatenated text) and child `SlidePageNode` (per-page content + embedding). Mirrors `TranscriptNode` → `QAExchangeNode` pattern.

```python
class SlideDeckNode(Neo4jNode):
    """Parent node for slide deck — holds full concatenated text and PDF metadata"""

    def __init__(self, id: str, content: Optional[str] = None,
                 file_path: Optional[str] = None, page_count: Optional[int] = None):
        self._id = id
        self.content = content          # Full Docling-extracted markdown (all pages)
        self.file_path = file_path      # Local PDF path for re-extraction
        self.page_count = page_count    # Number of pages in PDF

    # node_type -> NodeType.SLIDE_DECK
    # properties, from_neo4j — follow PreparedRemarkNode pattern exactly

class SlidePageNode(Neo4jNode):
    """Child node for a single slide page — holds per-page content, image path, + embedding"""

    def __init__(self, id: str, content: Optional[str] = None,
                 page_number: Optional[int] = None,
                 image_path: Optional[str] = None,
                 embedding: Optional[List[float]] = None):
        self._id = id
        self.content = content          # Docling-extracted markdown for this page
        self.page_number = page_number  # 1-indexed page number
        self.image_path = image_path    # Path to PNG on disk (for LLM vision at query time)
        self.embedding = embedding      # Vector embedding for this page

    # node_type -> NodeType.SLIDE_PAGE
    # properties, from_neo4j — follow QAExchangeNode pattern
```

Embeddings live on `SlidePageNode` (per-page), NOT on `SlideDeckNode` (full deck would exceed embedding limits).

**File:** `neograph/EventTraderNodes.py`

---

## Step 5: Extend EarningsCallProcessor to download slide decks

Modify `transcripts/EarningsCallTranscripts.py`:

**5a. Add imports** (alongside existing `from config.feature_flags import SPEAKER_CLASSIFICATION_MODEL` at line 21):
```python
from config.feature_flags import (SPEAKER_CLASSIFICATION_MODEL,
    ENABLE_SLIDE_DECK_DOWNLOAD, SLIDE_DECK_STORAGE_DIR, SLIDE_DECK_IMAGE_DPI)
from earningscall.errors import InsufficientApiAccessError
```

**5b. Add to `get_single_event()`** — after the transcript fetch block (around line 414, before `results.append(result)`):

```python
# After successful transcript fetch, attempt slide deck download
if feature_flags.ENABLE_SLIDE_DECK_DOWNLOAD:
    try:
        slide_path = self._download_slide_deck(company_obj, event, event_date)
        if slide_path:
            result["slide_deck_path"] = slide_path
            full_text, pages, image_paths = self._extract_slide_deck(slide_path)
            result["slide_deck_text"] = full_text
            result["slide_deck_pages"] = pages          # List of per-page markdown strings
            result["slide_deck_image_paths"] = image_paths  # List of per-page PNG paths
    except InsufficientApiAccessError:
        self.logger.warning("Slide Deck API access not available")
    except Exception as e:
        self.logger.error(f"Slide deck download failed: {e}")
```

Add three helper methods (~35 lines total):
```python
def _download_slide_deck(self, company_obj, event, event_date):
    """Download slide deck PDF, return file path or None.
    Uses conference date (not fiscal year/quarter) in filename to avoid collisions
    for the 13 fiscal-tag collision groups (e.g., EW FY2025 Q2 maps to both
    Feb 2025 and Jul 2025 calls). See Issue #35 analysis."""
    os.makedirs(SLIDE_DECK_STORAGE_DIR, exist_ok=True)
    date_str = str(event_date).split('T')[0].split(' ')[0]  # YYYY-MM-DD
    filename = f"{company_obj.company_info.symbol}_{date_str}_slides.pdf"
    filepath = os.path.join(SLIDE_DECK_STORAGE_DIR, filename)
    if os.path.exists(filepath):
        return filepath  # Already downloaded
    result = company_obj.download_slide_deck(event=event, file_name=filepath)
    return result  # Returns filepath or None (404 = no slide deck)

def _extract_slide_deck(self, pdf_path):
    """Extract text + images from slide deck PDF. Returns (full_text, pages_list, image_paths)."""
    from docling.document_converter import DocumentConverter
    from pdf2image import convert_from_path

    # Text extraction via Docling
    converter = DocumentConverter()
    doc = converter.convert(pdf_path)
    full_text = doc.document.export_to_markdown()
    pages = []
    for page_no in range(1, doc.document.num_pages() + 1):
        pages.append(doc.document.export_to_markdown(page_no=page_no))

    # Image conversion via pdf2image
    image_dir = os.path.splitext(pdf_path)[0]  # e.g., slide_decks/AAPL_2024-07-31_slides/
    os.makedirs(image_dir, exist_ok=True)
    image_paths = []
    pil_images = convert_from_path(pdf_path, dpi=SLIDE_DECK_IMAGE_DPI)
    for i, img in enumerate(pil_images, start=1):
        img_path = os.path.join(image_dir, f"p{i}.png")
        img.save(img_path, "PNG")
        image_paths.append(img_path)

    return full_text, pages, image_paths
```

**Files:**
- `transcripts/EarningsCallTranscripts.py` — add download + extraction methods
- `transcripts/transcript_schemas.py` — add 4 optional fields to `UnifiedTranscript`:
  ```python
  slide_deck_path: Optional[str] = None
  slide_deck_text: Optional[str] = None
  slide_deck_pages: Optional[List[str]] = None        # Per-page markdown strings
  slide_deck_image_paths: Optional[List[str]] = None   # Per-page PNG file paths
  ```

---

## Step 6: Extend TranscriptMixin for Neo4j slide deck nodes

Add to `_process_transcript_content()` in `neograph/mixins/transcript.py`. This method already uses `nodes_to_create` list and `add_rel()` helper — just append to those (same pattern as QAExchange):

```python
# After existing PR/QA/FullText processing, handle slide deck
if transcript_data.get("slide_deck_text"):
    pages = transcript_data.get("slide_deck_pages", [])
    image_paths = transcript_data.get("slide_deck_image_paths", [])
    slide_id = f"{transcript_id}_slides"

    # Parent: SlideDeckNode (full text, no embedding)
    slide_node = SlideDeckNode(
        id=slide_id,
        content=transcript_data["slide_deck_text"],
        file_path=transcript_data.get("slide_deck_path"),
        page_count=len(pages),
    )
    nodes_to_create.append(slide_node)
    add_rel("Transcript", transcript_id, "SlideDeck", slide_id, "HAS_SLIDE_DECK")

    # Children: SlidePageNode per page (text + image path)
    for i, page_text in enumerate(pages, start=1):
        page_id = f"{slide_id}_p{i}"
        page_node = SlidePageNode(
            id=page_id,
            content=page_text,
            page_number=i,
            image_path=image_paths[i-1] if i <= len(image_paths) else None,
        )
        nodes_to_create.append(page_node)
        add_rel("SlideDeck", slide_id, "SlidePage", page_id, "HAS_SLIDE_PAGE")
```

Update the import block at `neograph/mixins/transcript.py:9-12`:
```python
from ..EventTraderNodes import (
    PreparedRemarkNode, QuestionAnswerNode,
    FullTranscriptTextNode, QAExchangeNode, TranscriptNode,
    SlideDeckNode, SlidePageNode  # NEW
)
```

**File:** `neograph/mixins/transcript.py`

---

## Step 7: Extend EmbeddingMixin for slide deck embeddings (DEFERRED)

**Status: Deferred** — `ENABLE_SLIDE_DECK_EMBEDDINGS` defaults to `False`. Slide page text is often sparse (bullet points, table fragments) compared to QAExchange text (rich analyst Q&A). The same content is already covered verbally in transcript PR/QA nodes which DO have embeddings. Enable later if semantic search over slide-specific content proves necessary.

The code is still written (ready to flip the flag):

**7a.** Add 3-line vector index wrapper (identical pattern to `_create_qaexchange_vector_index()`):
```python
def _create_slidepage_vector_index(self):
    return self.create_vector_index(
        label="SlidePage", property_name="embedding",
        index_name=SLIDEDECK_VECTOR_INDEX_NAME, dimensions=OPENAI_EMBEDDING_DIMENSIONS
    )
```

**7b.** Add `batch_process_slidepage_embeddings()` — near-copy of `batch_process_qaexchange_embeddings()` with Cypher changed to:
```cypher
MATCH (sp:SlidePage) WHERE sp.embedding IS NULL AND sp.content IS NOT NULL
RETURN sp.id AS id, sp.content AS content
```
Reuses existing `process_embeddings_in_parallel()` and `_store_cached_embeddings_in_neo4j()`.

**File:** `neograph/mixins/embedding.py`

---

## Step 8: Flesh out query script

Replace the placeholder `scripts/earnings/get_presentations_range.py` (currently returns hardcoded "No presentations found"):

```python
QUERY = """
MATCH (t:Transcript)-[:INFLUENCES]->(c:Company {ticker: $ticker})
WHERE datetime(t.conference_datetime) >= datetime($start)
  AND datetime(t.conference_datetime) < datetime($end)
  AND EXISTS { (t)-[:HAS_SLIDE_DECK]->(:SlideDeck) }
MATCH (t)-[:HAS_SLIDE_DECK]->(sd:SlideDeck)
RETURN t.id AS transcript_id,
       left(t.conference_datetime, 10) AS date,
       sd.id AS slide_deck_id
ORDER BY t.conference_datetime
"""
```

Follows the exact same pattern as `get_transcript_range.py`, `get_transcript_pr_range.py`, `get_transcript_qa_range.py` — reuses `neo4j_session()`, `error()`, `ok()`, `parse_exception()` from `scripts/earnings/utils.py`.

**File:** `scripts/earnings/get_presentations_range.py`

---

## Step 9: Backfill script for existing transcripts

Steps 5–6 handle **new** transcripts automatically (both LIVE and HISTORICAL paths converge on `get_single_event()`). But transcripts already in Neo4j were ingested before slide deck support — they need a one-time backfill.

### Why not re-run the full pipeline?

Re-running `get_transcripts_by_date_range()` for every ticker would re-fetch transcripts, re-classify speakers via OpenAI, re-process Q&A pairs — all redundant since those nodes already exist. The backfill script **bypasses Redis entirely** and writes SlideDeck/SlidePage nodes directly into Neo4j alongside existing Transcript nodes.

### Design: group by ticker, reuse Company objects

The key optimization: `get_company(ticker)` creates a Company object that caches the events list. We group all missing transcripts by ticker so we call `get_company()` once per ticker (not once per transcript). This mirrors how `EarningsCallProcessor.load_companies()` works at line 52.

```python
#!/usr/bin/env python3
"""One-time backfill: download slide decks for existing transcripts that don't have one.

Usage: python scripts/earnings/backfill_slide_decks.py [--dry-run] [--ticker AAPL]

Reuses existing infrastructure:
- earningscall.get_company() + company.download_slide_deck() for API access
- Docling DocumentConverter for PDF extraction
- neo4j_session() from scripts/earnings/utils.py for Neo4j writes
- SLIDE_DECK_STORAGE_DIR from feature_flags for PDF storage
- Exponential backoff retry already configured on earningscall library
"""
import sys, os, logging, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.earnings.utils import load_env, neo4j_session, ok, get_neo4j_config
from neo4j import GraphDatabase
from config.feature_flags import SLIDE_DECK_STORAGE_DIR, SLIDE_DECK_IMAGE_DPI
from eventtrader.keys import EARNINGS_CALL_API_KEY
import earningscall
from earningscall import get_company
from earningscall.event import EarningsEvent
from docling.document_converter import DocumentConverter

load_env()
earningscall.api_key = EARNINGS_CALL_API_KEY
earningscall.retry_strategy = {"strategy": "exponential", "base_delay": 2, "max_attempts": 10}
logger = logging.getLogger(__name__)

# ── Phase 1: Query Neo4j for transcripts missing slide decks ──────────────
FIND_MISSING = """
MATCH (t:Transcript)-[:INFLUENCES]->(c:Company)
WHERE NOT EXISTS { (t)-[:HAS_SLIDE_DECK]->(:SlideDeck) }
RETURN t.id AS transcript_id, c.ticker AS ticker,
       t.fiscal_year AS year, t.fiscal_quarter AS quarter,
       left(t.conference_datetime, 10) AS conference_date
ORDER BY c.ticker, t.conference_datetime
"""

# ── Phase 3: Write to Neo4j (MERGE = idempotent, safe to re-run) ─────────
MERGE_SLIDE_DECK = """
MATCH (t:Transcript {id: $transcript_id})
MERGE (sd:SlideDeck {id: $slide_id})
SET sd.content = $content, sd.file_path = $file_path, sd.page_count = $page_count
MERGE (t)-[:HAS_SLIDE_DECK]->(sd)
"""
MERGE_SLIDE_PAGE = """
MATCH (sd:SlideDeck {id: $slide_id})
MERGE (sp:SlidePage {id: $page_id})
SET sp.content = $content, sp.page_number = $page_number, sp.image_path = $image_path
MERGE (sd)-[:HAS_SLIDE_PAGE]->(sp)
"""

def download_slide_deck(company_obj, year, quarter, conference_date):
    """Download PDF — reuses same logic as Step 5 _download_slide_deck().
    Uses conference_date (not fiscal year/quarter) in filename to avoid collisions
    for the 13 fiscal-tag collision groups. See Issue #35 analysis."""
    os.makedirs(SLIDE_DECK_STORAGE_DIR, exist_ok=True)
    symbol = company_obj.company_info.symbol
    filename = f"{symbol}_{conference_date}_slides.pdf"
    filepath = os.path.join(SLIDE_DECK_STORAGE_DIR, filename)
    if os.path.exists(filepath):
        return filepath  # Already on disk from prior run
    event = EarningsEvent(year=year, quarter=quarter, conference_date=None)
    try:
        result = company_obj.download_slide_deck(event=event, file_name=filepath)
        return result  # filepath or None (404)
    except Exception as e:
        if "403" in str(e) or "InsufficientApiAccess" in type(e).__name__:
            logger.error(f"API plan doesn't include slide decks — aborting backfill")
            sys.exit(1)
        raise

def extract_pages(pdf_path, converter=None):
    """Extract per-page markdown + images — reuses same logic as Step 5 _extract_slide_deck()."""
    if converter is None:
        converter = DocumentConverter()
    doc = converter.convert(pdf_path)
    full_text = doc.document.export_to_markdown()
    pages = []
    for page_no in range(1, doc.document.num_pages() + 1):
        pages.append(doc.document.export_to_markdown(page_no=page_no))

    # Convert pages to PNG images
    from pdf2image import convert_from_path
    image_dir = os.path.splitext(pdf_path)[0]
    os.makedirs(image_dir, exist_ok=True)
    image_paths = []
    for i, img in enumerate(convert_from_path(pdf_path, dpi=SLIDE_DECK_IMAGE_DPI), start=1):
        img_path = os.path.join(image_dir, f"p{i}.png")
        img.save(img_path, "PNG")
        image_paths.append(img_path)

    return full_text, pages, image_paths

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Query + download only, skip Neo4j writes")
    parser.add_argument("--ticker", type=str, help="Backfill single ticker only")
    args = parser.parse_args()

    # Phase 1: Get missing transcripts from Neo4j
    with neo4j_session() as (session, err):
        if err: print(err); sys.exit(1)
        rows = list(session.run(FIND_MISSING))

    if not rows:
        print(ok("NO_MISSING", "All transcripts already have slide decks")); sys.exit(0)

    # Group by ticker for efficient Company object reuse
    from collections import defaultdict
    by_ticker = defaultdict(list)
    for r in rows:
        ticker = r["ticker"]
        if args.ticker and ticker.upper() != args.ticker.upper():
            continue
        by_ticker[ticker].append(r)

    print(f"Found {sum(len(v) for v in by_ticker.values())} transcripts across {len(by_ticker)} tickers missing slide decks")

    # Phase 2 + 3: Download, extract, write — one ticker at a time
    # Single Neo4j driver for entire backfill (avoid creating hundreds of TCP connections)
    uri, user, password = get_neo4j_config()
    driver = GraphDatabase.driver(uri, auth=(user, password))
    converter = DocumentConverter()  # Reuse single Docling converter instance
    stats = {"downloaded": 0, "no_deck": 0, "written": 0, "errors": 0}

    try:
        for ticker, transcript_rows in by_ticker.items():
            try:
                company_obj = get_company(ticker)  # One API call per ticker
            except Exception as e:
                logger.error(f"Failed to get company object for {ticker}: {e}")
                stats["errors"] += len(transcript_rows)
                continue

            for r in transcript_rows:
                transcript_id = r["transcript_id"]
                year, quarter = r["year"], r["quarter"]
                conference_date = r["conference_date"]
                slide_id = f"{transcript_id}_slides"

                # Phase 2a: Download
                try:
                    pdf_path = download_slide_deck(company_obj, year, quarter, conference_date)
                except Exception as e:
                    logger.error(f"Download failed for {ticker} Q{quarter} {year}: {e}")
                    stats["errors"] += 1
                    continue

                if not pdf_path:
                    logger.info(f"No slide deck available for {ticker} Q{quarter} {year} (404)")
                    stats["no_deck"] += 1
                    continue

                # Phase 2b: Extract text + images (reuses shared converter)
                try:
                    full_text, pages, image_paths = extract_pages(pdf_path, converter)
                except Exception as e:
                    logger.error(f"Extraction failed for {pdf_path}: {e}")
                    stats["errors"] += 1
                    continue

                stats["downloaded"] += 1

                if args.dry_run:
                    print(f"  [DRY RUN] {ticker} Q{quarter} {year}: {len(pages)} pages, {len(full_text)} chars, {len(image_paths)} images")
                    continue

                # Phase 3: Write to Neo4j (reuses shared driver)
                try:
                    with driver.session() as session:
                        # Parent SlideDeckNode
                        session.run(MERGE_SLIDE_DECK, transcript_id=transcript_id,
                                    slide_id=slide_id, content=full_text,
                                    file_path=pdf_path, page_count=len(pages))
                        # Child SlidePageNodes (text + image path)
                        for i, page_text in enumerate(pages, start=1):
                            session.run(MERGE_SLIDE_PAGE, slide_id=slide_id,
                                        page_id=f"{slide_id}_p{i}",
                                        content=page_text, page_number=i,
                                        image_path=image_paths[i-1] if i <= len(image_paths) else None)
                    stats["written"] += 1
                except Exception as e:
                    logger.error(f"Neo4j write failed for {ticker} Q{quarter} {year}: {e}")
                    stats["errors"] += 1

            # Brief pause between tickers to avoid API rate limits
            time.sleep(0.5)
    finally:
        driver.close()

    print(f"\nBackfill complete: {stats}")
```

### Key design decisions:

| Decision | Rationale |
|----------|-----------|
| **Bypass Redis, write directly to Neo4j** | Parent Transcript nodes already exist. No enrichment (returns, metadata) needed for SlideDeck/SlidePage. Going through Redis would be redundant round-trip. |
| **Group by ticker** | `get_company(ticker)` makes one API call. Reuse the same Company object for all quarters of that ticker. |
| **MERGE (not CREATE)** | Idempotent — safe to re-run if interrupted. Won't duplicate nodes. |
| **`--dry-run` flag** | Download + extract without writing to Neo4j. Useful for testing Docling quality and collecting page count stats before committing. |
| **`--ticker` flag** | Test on a single ticker first before running full backfill. |
| **Check PDF on disk first** | `os.path.exists(filepath)` skips re-downloading. If script is interrupted and re-run, only missing PDFs are fetched. |
| **0.5s pause between tickers** | earningscall library has exponential backoff for 429s, but a small pause between tickers reduces the chance of hitting rate limits in the first place. |
| **Abort on 403** | If the API plan doesn't include slide decks, fail fast instead of burning through all tickers getting 403s. |
| **Single Neo4j driver + single Docling converter** | Reuse one driver (connection pool) and one DocumentConverter across all transcripts. Avoids creating hundreds of TCP connections. |

### Execution plan:

1. **Test single ticker**: `python scripts/earnings/backfill_slide_decks.py --ticker AAPL --dry-run`
2. **Verify Docling output**: Check `slide_decks/AAPL_*.pdf` files and extracted text quality
3. **Write single ticker**: `python scripts/earnings/backfill_slide_decks.py --ticker AAPL`
4. **Verify in Neo4j**:
   ```cypher
   MATCH (t:Transcript)-[:HAS_SLIDE_DECK]->(sd:SlideDeck)-[:HAS_SLIDE_PAGE]->(sp:SlidePage)
   WHERE t.symbol = 'AAPL'
   RETURN t.fiscal_year, t.fiscal_quarter, sd.page_count, count(sp) AS pages
   ```
5. **Full backfill**: `python scripts/earnings/backfill_slide_decks.py`
6. **Final stats**: Check how many transcripts got slide decks vs 404s (many companies don't publish slide decks)

**File:** `scripts/earnings/backfill_slide_decks.py`

---

## Step 10: Update schema documentation

Update the transcript-queries skill and neo4j-schema skill to include:
- `SlideDeck` node label and properties (id, content, file_path, page_count)
- `SlidePage` node label and properties (id, content, page_number, image_path, embedding)
- `HAS_SLIDE_DECK` relationship (Transcript → SlideDeck)
- `HAS_SLIDE_PAGE` relationship (SlideDeck → SlidePage)
- Vector index on `SlidePage` for per-page semantic search

**Files:**
- `.claude/skills/transcript-queries/SKILL.md`
- `.claude/skills/neo4j-schema/SKILL.md`

---

## Critical files to modify (ordered)

| # | File | Change | New code |
|---|------|--------|----------|
| 1 | `requirements.txt` | Add `docling` + `pdf2image` | 2 lines |
| 2 | `config/feature_flags.py` | Add slide deck flags | ~5 lines |
| 3 | `XBRL/xbrl_core.py` | Add `SLIDE_DECK`, `SLIDE_PAGE` NodeTypes + `HAS_SLIDE_DECK`, `HAS_SLIDE_PAGE` RelationTypes | 4 lines |
| 4 | `neograph/EventTraderNodes.py` | Add `SlideDeckNode` + `SlidePageNode` classes | ~50 lines |
| 5 | `transcripts/transcript_schemas.py` | Add 4 optional fields to `UnifiedTranscript` | 4 lines |
| 6 | `transcripts/EarningsCallTranscripts.py` | Add download + Docling extraction + pdf2image in `get_single_event()` | ~40 lines |
| 7 | `neograph/mixins/transcript.py` | Create parent SlideDeck + per-page SlidePage children in `_process_transcript_content()` | ~18 lines |
| 8 | `neograph/mixins/embedding.py` | 3-line index wrapper on `SlidePage` + batch embedding method (DEFERRED, flag off) | ~20 lines |
| 9 | `scripts/earnings/get_presentations_range.py` | Replace stub with real Cypher query | ~15 lines |
| 10 | `scripts/earnings/backfill_slide_decks.py` | One-time backfill: group-by-ticker, download, extract text + images, direct Neo4j MERGE | ~100 lines |
| 11 | Skill docs | Document new schema (2 nodes, 2 relationships, image_path convention, 1 vector index) | ~15 lines each |

**Total new code: ~260 lines** across 11 files. Two new classes (`SlideDeckNode`, `SlidePageNode`). Zero new patterns — everything follows existing `Transcript` → `QAExchange` infrastructure. Embeddings deferred (flag off by default).

## Disk storage structure

```
slide_decks/                                    ← SLIDE_DECK_STORAGE_DIR
  AAPL_2024-07-31_slides.pdf                    ← downloaded PDF (date-based, collision-safe)
  AAPL_2024-07-31_slides/                       ← per-deck image directory
    p1.png                                      ← page 1 image (200 DPI, ~200-500KB)
    p2.png
    ...p30.png
  MSFT_2024-10-22_slides.pdf
  MSFT_2024-10-22_slides/
    p1.png
    ...
```

**Estimated storage**: ~200-500KB per page PNG at 200 DPI. 30-page deck ≈ 6-15MB images + ~2MB PDF. 500 decks ≈ 4-8GB total. Manageable for local disk.

## Ingestion coverage

| Scenario | Covered by | Automatic? |
|----------|-----------|------------|
| **New transcripts — LIVE** (scheduling thread) | Step 5 (`get_single_event()`) | Yes — both paths converge on `get_single_event()` |
| **New transcripts — HISTORICAL** (date range) | Step 5 (`get_single_event()`) | Yes — same common entry point |
| **Existing transcripts already in Neo4j** | Step 9 (backfill script) | No — run once manually after deployment |

## Reusable existing infrastructure

| What we reuse | Where it lives | How |
|---|---|---|
| `download_slide_deck()` API method | `earningscall` library (already installed v1.2.1) | Call directly — identical pattern to `get_transcript()` |
| `get_single_event()` pipeline | `transcripts/EarningsCallTranscripts.py:208` | Add slide deck block after transcript fetch |
| Redis → Neo4j flow | `TranscriptMixin._process_transcript_content()` at `:382` | Append to existing `nodes_to_create` + `add_rel()` |
| `create_vector_index()` generic method | `neograph/mixins/embedding.py:45` | 3-line wrapper call |
| `batch_process_qaexchange_embeddings()` | `neograph/mixins/embedding.py:573` | Near-copy with different Cypher |
| `process_embeddings_in_parallel()` | `openai_local/openai_parallel_embeddings.py` | Called from batch method |
| `PreparedRemarkNode` class structure | `neograph/EventTraderNodes.py:1626` | Template for `SlideDeckNode` |
| `QAExchangeNode` class structure | `neograph/EventTraderNodes.py:1782` | Template for `SlidePageNode` (child with embedding) |
| Query script pattern | `scripts/earnings/get_transcript_range.py` | Same utils, same output format |
| `UnifiedTranscript` Pydantic schema | `transcripts/transcript_schemas.py` | Add 4 optional fields |
| Feature flag pattern | `config/feature_flags.py` | Add flags, same style |

## Verification

1. **Unit test Docling extraction**: Download a sample slide deck PDF manually, run Docling extraction, verify markdown output quality. **Important**: compare per-page `export_to_markdown(page_no=N)` output against full `export_to_markdown()` — [Docling has a known issue](https://github.com/docling-project/docling/discussions/1575) where per-page export can omit text items or reorder content vs full export. If quality is poor, fall back to splitting full markdown by page break placeholders (`page_break_placeholder` param)
2. **Feature flag off**: Verify existing transcript pipeline works unchanged with `ENABLE_SLIDE_DECK_DOWNLOAD = False`
3. **Feature flag on**: Enable flag, run `get_single_event()` for a company known to have slide decks, verify:
   - PDF downloaded to `slide_decks/` directory
   - Text extracted via Docling
   - Redis payload includes `slide_deck_text`, `slide_deck_path`, `slide_deck_pages`, and `slide_deck_image_paths`
   - `SlideDeck` parent node created in Neo4j with `HAS_SLIDE_DECK` relationship to Transcript
   - `SlidePage` child nodes created with `HAS_SLIDE_PAGE` relationships to SlideDeck
   - Each `SlidePage` has correct `page_number`, per-page `content`, and `image_path` pointing to a valid PNG on disk
4. **Graceful 403**: With flag on but no API plan, verify `InsufficientApiAccessError` is caught and logged (not thrown)
5. **Graceful 404**: For companies without slide decks, verify None returned and no node created
6. **Embeddings**: Verify vector index created on `SlidePage`, embeddings generated on per-page nodes (NOT on parent SlideDeck)
7. **Query script**: Run `get_presentations_range.py AAPL 2024-01-01 2025-01-01` and verify output
8. **Neo4j schema check**:
   ```cypher
   MATCH (t:Transcript)-[:HAS_SLIDE_DECK]->(sd:SlideDeck)
   RETURN t.symbol, t.fiscal_year, t.fiscal_quarter, sd.id, size(sd.content) AS text_length
   LIMIT 5
   ```
9. **Backfill**: Run `backfill_slide_decks.py`, verify it skips transcripts where no slide deck exists (404) and creates `SlideDeckNode` + `HAS_SLIDE_DECK` for those that do
10. **Chunking data collection** (post-launch): After ~50 decks ingested, run:
   ```cypher
   MATCH (sd:SlideDeck)
   RETURN sd.page_count, size(sd.content) AS chars, sd.id
   ORDER BY size(sd.content) DESC
   ```
   Use this to decide chunking strategy (see Open Decision above).

---

## Independent Verification Analysis (2026-03-02)

Full empirical audit of every claim, code reference, API, Neo4j schema, and assumption.
Conducted by reading every line of referenced source code, querying the live Neo4j database,
inspecting the installed earningscall library, and verifying the Docling API via documentation.

### BUGS / ISSUES FOUND

#### BUG 1 — CRITICAL: fiscal_year stored as comma-formatted string in Neo4j

**Affects:** Step 9 backfill script (`backfill_slide_decks.py`)

All 4,397 Transcript nodes store `fiscal_year` as comma-formatted strings: `"2,023"`, `"2,024"`,
`"2,025"`, etc. — NOT integers. Empirically verified:

```
Neo4j query:
  MATCH (t:Transcript) RETURN t.fiscal_year, apoc.meta.cypher.type(t.fiscal_year) AS type LIMIT 1
  → fiscal_year: "2,023", type: "STRING"

  toInteger(t.fiscal_year) → NULL  (comma breaks conversion)
  All 4,397 transcripts have comma-formatted fiscal_year (CONTAINS ',' = 4,397)
  fiscal_quarter is also STRING type but without commas (e.g., "1", "2")
```

The backfill script's `FIND_MISSING` query returns `t.fiscal_year AS year` → `"2,023"` (string).
This is then passed to `EarningsEvent(year=year, quarter=quarter, conference_date=None)`.
The earningscall library's `download_slide_deck()` at `company.py:192` does:
```python
if quarter < 1 or quarter > 4:  # TypeError: '<' not supported between 'str' and 'int'
```
This will crash the entire backfill script.

**Fix required in backfill script:**
```python
year = int(str(r["year"]).replace(',', ''))
quarter = int(str(r["quarter"]))
```
Or fix the Cypher query:
```cypher
RETURN toInteger(replace(t.fiscal_year, ',', '')) AS year,
       toInteger(t.fiscal_quarter) AS quarter
```

Note: This is a pre-existing data quality issue in the Transcript ingestion pipeline —
`TranscriptNode` uses `safe_int()` to convert to int at `transcript.py:558`, but somehow
the values are stored as comma-formatted strings in Neo4j. A separate investigation is
warranted to find the root cause and fix it upstream.

---

#### BUG 2 — MODERATE: feature_flags prefix inconsistency in Step 5b

Step 5a imports the constant directly:
```python
from config.feature_flags import (SPEAKER_CLASSIFICATION_MODEL,
    ENABLE_SLIDE_DECK_DOWNLOAD, SLIDE_DECK_STORAGE_DIR, SLIDE_DECK_IMAGE_DPI)
```
But Step 5b code uses module-prefix style:
```python
if feature_flags.ENABLE_SLIDE_DECK_DOWNLOAD:
```
These are inconsistent. Since the import is `from config.feature_flags import ...`, the
code should use just `ENABLE_SLIDE_DECK_DOWNLOAD` (no prefix). Or change the import to
`from config import feature_flags` and use `feature_flags.ENABLE_SLIDE_DECK_DOWNLOAD`.

---

#### BUG 3 — MODERATE: Docling per-page export known quality issue

The plan correctly references GitHub discussion #1575 at line 618 (Verification step 1),
noting that per-page `export_to_markdown(page_no=N)` can omit text items or reorder content
vs the full `export_to_markdown()` call.

Empirical verification via GitHub (2026-03-02): Discussion #1575 confirms this issue is
**REAL and UNSOLVED** as of Docling v2.31.0. The reporter notes "some TextItems are randomly
skipped" when using page_no, and tables appear in wrong locations in the output.

The plan mentions a fallback strategy ("split full markdown by page break placeholders")
but this fallback is NOT coded anywhere in Steps 5 or 9 — it's only mentioned as a
verification step. The implementation should include this fallback from the start, or at
minimum, validate that per-page output matches full output for the first few decks before
proceeding with batch processing.

**Recommendation:** Implement a validation check in `_extract_slide_deck()`:
```python
# Verify per-page export quality
concatenated = "\n".join(pages)
if len(concatenated) < 0.8 * len(full_text):  # >20% content loss
    logger.warning(f"Per-page export lost {100 - len(concatenated)*100//len(full_text)}% content, falling back to page-break split")
    pages = full_text.split(page_break_placeholder)  # fallback
```

---

#### ISSUE 4 — MODERATE: Docling `num_pages` — property vs method uncertainty

The plan calls `doc.document.num_pages()` with parentheses. Docling's official API reference
lists `num_pages` but its exact nature (property vs method) is ambiguous from documentation.
Multiple community examples show both patterns. If `num_pages` is a `@property`, then
calling it with `()` would first evaluate to an `int`, then attempt to call the int,
raising `TypeError: 'int' object is not callable`.

**Recommendation:** Verify at implementation time. Use `doc.document.num_pages` (no parens)
to be safe, or check with `callable(doc.document.num_pages)` first.

---

#### ISSUE 5 — MINOR: Insertion point line numbers slightly off

Plan says: "around line 414, before `results.append(result)`"
Actual code at that location:
- Line 411: `result['conference_datetime'] = result['conference_datetime'].isoformat()`
- Line 414: `result = self._validate_transcript(result)`
- Line 415: `results.append(result)`

The slide deck download block should go between lines 411 and 414 (after datetime
serialization, before validation). Line 414 is `_validate_transcript`, not `results.append`.
Minor but worth noting for implementation accuracy.

Note: `_validate_transcript()` catches all exceptions and logs warnings only (lines 459-473),
so extra `slide_deck_*` fields would not cause validation failures even without updating
`UnifiedTranscript`. But updating the schema (as the plan specifies) is still correct practice.

---

#### ISSUE 6 — MINOR: Redis file paths non-portable

The slide deck fields `slide_deck_path` and `slide_deck_image_paths` store absolute local
filesystem paths (e.g., `/path/to/slide_decks/AAPL_2024-07-31_slides.pdf`). These are
serialized into Redis via `json.dumps()`. If the Redis consumer runs on a different machine
(e.g., K8s worker pod), the paths won't resolve. Currently not a problem since transcript
processing is single-machine, but worth noting for future K8s scaling.

---

### EVERYTHING VERIFIED CORRECT

#### Earningscall Library (v1.2.1) — ALL CLAIMS VERIFIED

| Claim | Evidence | Status |
|-------|----------|--------|
| `download_slide_deck()` exists | `company.py:168-214`, signature: `(self, year, quarter, event, file_name)` | ✅ |
| Returns filename (str) or None | Line 202: `return resp`, Line 204-205: `return None` on 404 | ✅ |
| `InsufficientApiAccessError` exists | `errors.py:23-24`, inherits from `ClientError` | ✅ |
| 403 raises `InsufficientApiAccessError` | `company.py:206-213`, reads `X-Plan-Name` header | ✅ |
| 404 returns None gracefully | `company.py:204-205` | ✅ |
| `get_company(ticker)` exists | `exports.py:15-27`, returns `Company` object | ✅ |
| `EarningsEvent(year, quarter, conference_date)` | `event.py:25-39`, dataclass with those exact fields | ✅ |
| Exponential backoff retry | `api.py:163-173`, configurable `DEFAULT_RETRY_STRATEGY` | ✅ |
| `EARNINGS_CALL_API_KEY` in keys.py | `eventtrader/keys.py:30` | ✅ |
| earningscall v1.2.1 in requirements | `requirements.txt` confirmed | ✅ |

#### Neo4j Database Schema — EMPIRICALLY VERIFIED

| Claim | Evidence | Status |
|-------|----------|--------|
| No SlideDeck/SlidePage nodes exist | Query: `count(sd:SlideDeck) = 0, count(sp:SlidePage) = 0` | ✅ |
| No HAS_SLIDE_DECK/HAS_SLIDE_PAGE rels | Query: `MATCH ()-[r:HAS_SLIDE_DECK]->() → count = 0` | ✅ |
| 4,397 Transcript nodes | `MATCH (t:Transcript) RETURN count(t) = 4397` | ✅ |
| INFLUENCES: Transcript→Company | `MATCH (t:Transcript)-[:INFLUENCES]->(c:Company) → 4,397` | ✅ |
| HAS_TRANSCRIPT: Company→Transcript | `MATCH (c:Company)-[:HAS_TRANSCRIPT]->(t:Transcript) → 4,397` | ✅ |
| Transcript has `symbol` property | Keys include: id, symbol, company_name, conference_datetime, fiscal_year, fiscal_quarter, etc. | ✅ |
| Transcript ID format | `{SYMBOL}_{conference_datetime_iso}` e.g., `HPE_2025-09-03T17.00.00-04.00` | ✅ |
| QAExchange ID format | `{transcript_id}_qa__{sequence}` e.g., `SMPL_2023-01-05T08.30.00-05.00_qa__0` | ✅ |
| PreparedRemark ID format | `{transcript_id}_pr` | ✅ |
| Vector indexes: 3072 dim, cosine | `news_vector_index` and `qaexchange_vector_idx`, both 3072 dim, COSINE | ✅ |
| 79,781 QAExchange nodes | Label count verified | ✅ |
| 4,263 PreparedRemark nodes | Label count verified | ✅ |

#### Codebase — ALL LINE NUMBERS AND PATTERNS VERIFIED

| Claim | Actual Location | Status |
|-------|----------------|--------|
| `get_single_event()` at ~line 208 | Line 208 exactly | ✅ |
| `load_companies()` at ~line 52 | Line 52 exactly | ✅ |
| `SPEAKER_CLASSIFICATION_MODEL` import at line 21 | Line 21 exactly | ✅ |
| `_process_transcript_content()` at ~line 382 | Line 382 exactly | ✅ |
| `nodes_to_create` list + `add_rel()` helper | Lines 385-398 exactly as described | ✅ |
| `PreparedRemarkNode` at ~line 1626 | Line 1626 exactly | ✅ |
| `QAExchangeNode` at ~line 1782 | Line 1782 exactly (data class at 1770) | ✅ |
| `create_vector_index()` at ~line 45 | Line 45 exactly | ✅ |
| `_create_qaexchange_vector_index()` at ~line 123 | Lines 123-131 exactly | ✅ |
| `batch_process_qaexchange_embeddings()` at ~line 573 | Line 573 exactly | ✅ |
| `get_presentations_range.py` is a stub | Returns hardcoded "No presentations found" | ✅ |
| Python 3.11 runtime | `venv/pyvenv.cfg: executable = /usr/local/bin/python3.11` | ✅ |
| Neither docling nor pdf2image in requirements.txt | Grep confirmed — absent | ✅ |
| No slide deck feature flags in feature_flags.py | Full file read confirmed — absent | ✅ |

#### Pipeline Architecture — VERIFIED

| Claim | Evidence | Status |
|-------|----------|--------|
| API → Redis → Neo4j flow | `get_single_event()` → `store_transcript_in_redis()` → `_process_transcript_content()` | ✅ |
| LIVE and HISTORICAL paths converge on `get_single_event()` | Both `get_transcripts_for_single_date()` and `get_transcripts_by_date_range()` call it | ✅ |
| `result` dict populated before `results.append()` | Lines 228-415 build dict, 415 appends | ✅ |
| Redis serialization: `json.dumps(transcript, default=str)` | `store_transcript_in_redis()` line 765 | ✅ |
| LPUSH to raw queue | Line 769: `pipe.lpush(client.RAW_QUEUE, raw_key)` | ✅ |
| Atomic Redis pipeline | Lines 762-779: transaction=True pipeline | ✅ |
| `manager.merge_nodes()` for batch writes | Line 539: `self.manager.merge_nodes(nodes_to_create)` | ✅ |
| `create_relationships()` for rels | Lines 541-549: individual rel creation | ✅ |

#### Query Script Pattern — VERIFIED

| Claim | Evidence | Status |
|-------|----------|--------|
| `get_transcript_range.py` pattern matches | Uses INFLUENCES direction, datetime() casting, EXISTS filter, `neo4j_session()`, `error()`/`ok()` | ✅ |
| `utils.py` functions exist | `neo4j_session()`, `error()`, `ok()`, `parse_exception()`, `load_env()`, `get_neo4j_config()` — all verified | ✅ |
| Same CLI arg pattern (ticker, start, end) | `sys.argv[1:4]` in all scripts | ✅ |

#### Embedding Pipeline — VERIFIED

| Claim | Evidence | Status |
|-------|----------|--------|
| `OPENAI_EMBEDDING_DIMENSIONS = 3072` | `feature_flags.py:113` | ✅ |
| `OPENAI_EMBEDDING_MODEL = "text-embedding-3-large"` | `feature_flags.py:112` | ✅ |
| `QAEXCHANGE_VECTOR_INDEX_NAME = "qaexchange_vector_idx"` | `feature_flags.py:126` | ✅ |
| 3-line vector index wrapper pattern | `_create_qaexchange_vector_index()` at lines 123-131 — exactly 3 substantive lines | ✅ |
| `batch_process_qaexchange_embeddings()` uses temp content, cleanup | Lines 573-693: sets `_temp_content`, calls `batch_embeddings_for_nodes()`, cleans up | ✅ |
| `process_embeddings_in_parallel()` reusable | `openai_local/openai_parallel_embeddings.py` — 71 lines, async, rate-limited | ✅ |

#### Design Decisions — SOUND

| Decision | Assessment |
|----------|------------|
| Page-by-page chunking | Correct — slide decks ARE designed as one-topic-per-page. Mirrors QAExchange pattern. |
| Parent SlideDeckNode + child SlidePageNode | Correct — follows existing Transcript → QAExchange hierarchy exactly. |
| Embeddings on SlidePageNode (not parent) | Correct — full deck text would exceed embedding token limits. Per-page is within range. |
| Conference date in filenames (not fiscal year/quarter) | Correct — avoids collision for companies with overlapping fiscal periods. |
| MERGE (not CREATE) in backfill | Correct — idempotent, safe to re-run. |
| Group by ticker in backfill | Correct — reuses Company object (one API call per ticker). |
| Feature flags defaulting to False | Correct — safe rollout strategy. |
| Bypass Redis in backfill | Correct — parent Transcript nodes already exist, no enrichment needed. |
| Deferred embeddings | Reasonable — slide page text may be sparse; transcript PR/QA already covers same content verbally. |

### SUMMARY

**Plan quality: HIGH.** The architecture, design decisions, code patterns, and integration
points are all sound and well-researched. The plan correctly mirrors existing infrastructure
(Transcript → QAExchange pattern) and reuses established code paths.

**3 bugs to fix before implementation:**
1. **CRITICAL:** Backfill script type conversion for comma-formatted fiscal_year strings
2. **MODERATE:** `feature_flags.` prefix inconsistency (pick one import style)
3. **MODERATE:** Implement Docling per-page fallback from the start (not just in verification)

**2 items to verify at implementation time:**
1. Docling `num_pages` — property vs method (use without parens to be safe)
2. Docling `export_to_markdown(page_no=N)` quality — test on first few PDFs before batch

**Total estimated new code: ~260 lines across 11 files** — confirmed reasonable.

---

### ADDENDUM: Cross-referencing with Pipeline & Gap Analysis (2026-03-02)

After reading `transcriptIngestionPipeline.md` (full 8-stage pipeline deep dive) and
`transcript-fix-gaps-validation.md` (17-gap analysis with 5-bot validation), the following
updates and new findings apply:

#### NOTE: Transcript ID format migration is a non-issue for slide decks

The gap analysis reveals a planned transcript ID migration (3,722 LONG + 675 SHORT → DATE
format). Since zero SlideDeck/SlidePage nodes exist today, there is nothing to orphan or
re-link. The natural deployment sequence (code fix → ID migration → then slide deck feature)
means slide decks will only ever be created against already-migrated DATE-format IDs.
No coordination needed — just don't run the backfill before the ID migration, which would
be nonsensical anyway (the API tier hasn't been purchased yet).

---

#### REFINEMENT to BUG 1 — fiscal_year type: Root cause identified

The pipeline doc (Notable Nuance #7) reveals transcript IDs differ between stages:
- Raw Redis key: SYMBOL_datetime (LONG)
- `_standardize_fields()`: creates `id = "{symbol}_{fiscal_year}_{fiscal_quarter}"` (SHORT)

The `fiscal_year` and `fiscal_quarter` in the result dict are Python integers from the
earningscall API. But in Neo4j they are stored as comma-formatted strings ("2,023").

Root cause is likely in the Neo4j merge process — `TranscriptNode.properties` returns
`fiscal_year` as an `int`, but somewhere in `manager.merge_nodes()` or the Cypher
serialization, Python's locale-aware string formatting or a JSON round-trip introduces
the comma. This is a pre-existing data quality bug unrelated to slide decks, but the
backfill script MUST handle it.

The backfill script's `FIND_MISSING` query should use Cypher conversion:
```cypher
RETURN t.id AS transcript_id, c.ticker AS ticker,
       toInteger(replace(t.fiscal_year, ',', '')) AS year,
       toInteger(t.fiscal_quarter) AS quarter,
       left(t.conference_datetime, 10) AS conference_date
```

---

#### CONFIRMATION: Pipeline data flow is compatible

The pipeline doc confirms data flows through 8 stages:
```
API (get_single_event) → Redis raw → BaseProcessor → Redis processed
→ ReturnsProcessor → Redis withreturns → Neo4j → Embeddings
```

The slide deck fields (`slide_deck_path`, `slide_deck_text`, `slide_deck_pages`,
`slide_deck_image_paths`) added to the result dict in `get_single_event()` will survive
all intermediate stages because:
- `_standardize_fields()` only ADDS id/created/updated/symbols/formType — does not strip fields
- `_clean_content()` only converts timestamps — does not strip fields
- `_add_metadata()` only ADDS returns schedule — does not strip fields
- ReturnsProcessor only ADDS return data — does not strip fields
- `_process_transcript_content()` reads specific fields with `.get()` — ignores unknown fields

**Verified: the full pipeline is compatible with the slide deck plan's data flow.**

---

#### CONFIRMATION: Both Neo4j write paths handle slide decks

The pipeline doc confirms two independent paths to Neo4j:
1. **PubSub (real-time)**: `_process_pubsub_item()` → `_process_deduplicated_transcript()`
2. **Batch**: `process_transcripts_to_neo4j()` → `_process_deduplicated_transcript()`

Both converge on `_process_deduplicated_transcript()` → `_process_transcript_content()`.
The slide deck code in Step 6 is added to `_process_transcript_content()`, so both paths
handle slide decks correctly. **No additional code needed for PubSub vs batch distinction.**

---

#### NOTE: Redis memory impact of slide deck text

The pipeline involves TWO Redis storage stages per transcript:
1. Raw: `transcripts:{live|hist}:raw:{id}` → full JSON
2. Processed: `transcripts:{live|hist}:processed:{id}` → full JSON (enriched)

Adding slide deck text (~50-100KB per deck for a 30-page presentation) doubles the per-
transcript Redis memory for the slide deck portion. For batch processing of ~500 transcripts
with decks, this is ~50-100MB additional Redis memory. Not blocking, but worth monitoring.

The withreturns/withoutreturns stage is a THIRD copy, making it ~150-300MB total temporarily.
Redis keys have TTL (2 days), so this is transient.

---

#### NO CHANGE to original findings

All 3 bugs (fiscal_year types, feature_flags prefix, Docling per-page fallback) and
2 verification items (num_pages, export_to_markdown quality) remain valid. The pipeline
and gap analysis documents reinforce the original findings without contradicting any of them.
