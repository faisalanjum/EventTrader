# Driver workflow experiments

- **[Decider guidance study — November 15, 2026](2026-11-15_decider_guidance/readme.md):** all saved experiment material is inside this one folder. Start here for what worked, what failed, exact checked counts and limitations.
- [Folder map and every saved code file](2026-11-15_decider_guidance/code_guide.md)
- **Base + copies (Claude) — November 12–13, 2026** (`2026-11-12_base_and_copies_claude/`): load a filing once into a base Claude session, then run copies that reuse it. Results are written up in [DriverWorkflow.md](../DriverWorkflow.md#complete-independent-cache-experiment-record).
  - `context_cache_probe_2026-11-12/`: Codex's cache experiment (51 calls).
  - `context_reader_followup_2026-11-12/`: review of Fable's first run; also holds a copy of Fable's `mech_run1`.
  - `fable_reader_tests_2026-11-13_local/`: Fable's full raw tests, including the 10-K fact-finding runs (not in git).
- **Filing chunking research — November 11, 2026** (`2026-11-11_filing_chunking/`): how to cut a filing into pieces so AI reads it cheaply without missing facts. Main report + 4 source notes in `notes/`. Not the current plan (the current plan reads the whole filing via base + copies).

The study is stopped. No inference was rerun while organizing this archive.
