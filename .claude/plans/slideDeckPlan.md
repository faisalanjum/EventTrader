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
        slide_path = self._download_slide_deck(company_obj, event)
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
def _download_slide_deck(self, company_obj, event):
    """Download slide deck PDF, return file path or None."""
    os.makedirs(SLIDE_DECK_STORAGE_DIR, exist_ok=True)
    filename = f"{company_obj.company_info.symbol}_{event.year}_Q{event.quarter}_slides.pdf"
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
    image_dir = os.path.splitext(pdf_path)[0]  # e.g., slide_decks/AAPL_2024_Q3_slides/
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
       t.fiscal_year AS year, t.fiscal_quarter AS quarter
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

def download_slide_deck(company_obj, year, quarter):
    """Download PDF — reuses same logic as Step 5 _download_slide_deck()."""
    os.makedirs(SLIDE_DECK_STORAGE_DIR, exist_ok=True)
    symbol = company_obj.company_info.symbol
    filename = f"{symbol}_{year}_Q{quarter}_slides.pdf"
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
                slide_id = f"{transcript_id}_slides"

                # Phase 2a: Download
                try:
                    pdf_path = download_slide_deck(company_obj, year, quarter)
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
  AAPL_2024_Q3_slides.pdf                       ← downloaded PDF
  AAPL_2024_Q3_slides/                          ← per-deck image directory
    p1.png                                      ← page 1 image (200 DPI, ~200-500KB)
    p2.png
    ...p30.png
  MSFT_2024_Q4_slides.pdf
  MSFT_2024_Q4_slides/
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
