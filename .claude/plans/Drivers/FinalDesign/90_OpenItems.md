# 90 · Open items (what's not yet decided or not yet built)

**What this is:** every open thread in one place. Split into: **A** = design *decisions* still needing an owner call · **B** = design done, *code/wiring* not built · **C** = parked/deferred · **D** = design *sections* still to write · **E** = resolved (kept for the record).

---

## A. Open DESIGN decisions (need an owner call)
| ID | Question | Lean / note |
|---|---|---|
| **09 §8** | Approve the field-spec amendments in one yes/no: `level_bound`→shapes, fact `evhash16` retired, `qualitative`→`value_text` (DU-13/14/16/18) | recommended — see 95_Supersession #16-18 |
| ~~FS-14~~ | Slice-menu point-in-time | ✅ **RESOLVED 2026-07-02: PIT for DriverUpdate write-time** (3-context split) → §E |
| **FS-23** | Cross-company **value** comparison (does "International" at A = "International" at B?) — a separate, not-yet-built layer | deferred; conservative bar |
| **UNIT-12** | Add `percent_qoq` to the 9-unit enum? | lean **no** — keep stable unless production evidence forces it |
| **09 fields** | Owner was finalizing the per-fact_type field set — largely settled by 09; remaining = the §8 ack above | near-closed |
| 8-K taxonomy | Is the 24-tag 8-K event taxonomy useful here? | open (README "To Resolve") |
| Amendments | How to handle filing amendments? | open (README "To Resolve") |
| **Model policy** | Reader default = **Opus reads + Sonnet classifies** (supersedes Fable/2-pass) — but exact model, number of runs, and job-by-job process need a **larger audit/experiment** | leading default set; full policy open |

## B. Design done — BUILD/WIRING not done
| ID | What | Status |
|---|---|---|
| **UNIT-14** | The shared unit resolver is proven in scratch (117/117), **not wired** into the producer (old Steps 5-7) | build-pending |
| **PER-20** | DriverPeriod design locked; **not built** — extract `driver_period_resolver.py`, pass the 21 tests, prove YTD/TTM math, write-once hardening | build-pending |
| **XC-16** | Concept-linker: replace the hand 4-entry deny-set with the us-gaap **calculation-hierarchy** veto | recommended **before** the full-universe run |
| Concept-link full run | Validated on 274/795 companies (~35%); a **full-universe run** is pending | pending |
| Guidance field-map | `09 §5` delivers old-guidance-field → new-home; still verify against the **real guidance schema** (`guidance_ids.py`) + the member/company reconciliation | mostly done |

## C. Parked / deferred (out of scope for now)
- **Macro/news attribution** — **core shape LOCKED 2026-07-02**: `DailyCompanyMoveEvent {id=dcm:<cik>:<trade_date>, trade_date, created}` `-FOR_COMPANY->Company` `-ON_DATE->Date`; verdict via `EXPLAINED_BY`; realized return **read from `Date-HAS_PRICE-Company`** (never duplicated); News stays `FROM_SOURCE`. **Open details:** the significance threshold · the source for a *pure-macro* driver (e.g. `oil_price` with no company news) · `subject_company` / 0..N `FROM_SOURCE` if ever needed.
- **§10 dormant rider** — creating 10-K/10-Q metric facts by **XBRL-linking** instead of LLM re-extraction (`origin` field, `[XBRL]` quote, etc.). Activates only if the "Codex §4.8" write-path decision is approved.
- **Blanket-withdrawal fan-out** — a "guidance withdrawn" fact fans out per open guide (the one place the producer writes beyond the literal quote); owner sign-off noted (09 §7).

## D. Design SECTIONS still to write (the ~35% not done)
- **DriverCatalog build pipeline** (Track A) — leaf (pull→chunk→menu→converge) → reconcile (dedup ‖ G2 ‖ Refute ‖ D5 ‖ assemble ‖ validate) → fold (D1–D8) → repair; the G1/G2/Refute gates; chunking ladder; run layout + acceptance criteria; consumption contract; PIT safety; **model choice** (Opus reads + Sonnet classifies).
- **Guidance integration** (Track C) — regenerate-as-`fact_type=guidance` (decided), the reuse matrix, and the field-map (09 §5 is the core; add the class-level + member/company parts).
- **Incremental refresh** — re-run only on new events; old↔old frozen; the append-seam rules.
- **Overview finish** — the 3-tracks map, the authority/reading map, a status dashboard.
- **Cost / fold levers** (CostCutting ledger) — can fold into the pipeline section.

## E. RESOLVED (for the record)
- **Guidance node-label** (`:GuidanceUpdate` vs `:DriverUpdate` vs dual-label) → **regenerate as `fact_type=guidance` DriverUpdate facts; retire the original guidance extraction** (owner, 2026-07-01 — PER-19).
- **company_confirmed scope** → **guidance-only** (owner, 2026-07-01 — MF-11); type = **boolean** (09).
- **FactScope identity package (the old "Q1–Q4+E")** → resolved into `Naming_Slices_XBRL.md` (per memory); the `PENDING` file was deleted, don't reopen.
- **`_guidance`/`_surprise` suffix vs `fact_type` "redundant?"** → keep both (NAME-17 / MF-09).
- **FS-14 (slice-menu PIT)** → **PIT for DriverUpdate write-time** (owner, 2026-07-02); 3-context split (name-creation N/A · write=PIT · read/repair=all-history). Re-locked to `Naming_Slices §7` after a brief in-session reopen; slice-value immutability is orthogonal.
- **Macro/news core shape** → **LOCKED** (`DailyCompanyMoveEvent`, CIK-based id, returns from `HAS_PRICE`) — open *details* in §C.
