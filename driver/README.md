# Driver

New home for the document-to-Driver pipeline. Build the design and code together,
one agreed step at a time. Both existing and newly ingested documents use this flow.

Step 1 is implemented: preserve a compressed SEC package and read its files on demand. Broader
filing validation and later preparation stages remain separate checkpoints.

- [Prepare: usage and limits](prepare/README.md)
- [Tests: layout, fixtures and command](../tests/driver/README.md)
- [Current design](../.claude/plans/Drivers/DriversFinal/PrepareStep.md)
- [Fact-type findings (archived)](../.claude/plans/Drivers/DriversFinal/Archive/fact_types_2026-10-02.md)
- [Previous implementation](../driver_reference/README.md): reference material; review before reusing.

Keep reusable code in `driver/<stage>/` and tests in `tests/driver/<stage>/`.
Use module CLIs directly; keep generated data and one-off experiments outside the
source tree. Keep this package independent of `driver_reference`.
