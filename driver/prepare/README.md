# SEC extraction and OCR

Preserve original filing files and extract HTML/XML with links back to the source.
Optional OCR reads embedded images and PDF pages through self-hosted Chandra,
RapidOCR and OnnxTR. Other companion files are saved intact.

```text
filing -> original files -> HTML/XML extraction -> saved output
                          -> images/PDF -> OCR -> linked supplement
```

## Start here

1. Read [PrepareTools](../../.claude/plans/Drivers/DriversFinal/PrepareTools.md)
   for requirements and preserved planning history, not current release status.
2. Read the [operating guide](../../k8s/prepared-extraction/README.md)
   for the exact image, configuration, rollout and rollback.
3. Read the [qualification record](../../k8s/prepared-extraction/OCR_QUALIFICATION.txt)
   for completed checks, known OCR errors and remaining limits.
4. Use the [code reference](../../docs/prepare-reference.md)
   when changing extraction behavior or interpreting saved fields.

## Where the code and tests live

- `get/`: original files and verified package inventory.
- `job.py`, `document.py`: pinned jobs, bounded children and saved-output checks.
- `convert/`, `reconstruct.py`: source-linked readings and ordered reconstruction.
- `pictures/`: image/PDF preparation, native readers and unverified OCR supplements.
- `redisDB/prepared_filing.py`: filing attempts and durable receipt pointers;
  `redisDB/report_enricher.py`: delivery, publication and retained failed input.
- [Prepare tests](../../tests/driver/prepare/README.md): offline extraction and OCR checks.
- [Adapter and worker tests](../../tests/redisDB/README.md): delivery and retry checks.
- [Acquisition guide](get/README.md): download and original-file storage contracts.

## Keep these boundaries

- A completed OCR request does **not** prove accurate or complete reading.
  OCR output stays `fidelity: unverified`; preserve originals, errors and disagreements.
- Keep source identities, locations, context and uncertainty with every saved result.
- Machine failures remain failures through native parser wrappers. Bad content
  keeps its explicit incomplete/unread result. Valid receipts are read once at handoff.
- The caller's `filing_seconds` bounds acquisition, extraction, OCR and retries
  together. A timeout stops owned work and remains failed; it is not completion.
  A failed pointer retains input for explicit replay; it schedules no extra retry.
- A crashed browser invalidates its attempt. Fresh jobs retry technical failures;
  completed script checks are reused, while interrupted checks can run again.
- Building or pushing does not activate production. Activation remains an owner decision.
- Mac automation and downstream Driver/Neo4j changes are separate work.

Before changing code, reproduce the issue, check the pinned library's native support,
and make the smallest general fix with the relevant offline tests.
Keep tests and experiments outside runtime. The runtime manifest covers every file
under `driver/`, including this README; update its matching image and configuration
when any covered file changes.
