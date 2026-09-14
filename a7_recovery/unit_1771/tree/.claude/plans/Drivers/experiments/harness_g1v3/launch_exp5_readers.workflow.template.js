// EXP-5 reader arms workflow (persisted; DISABLED plan — separate approval).
// Launch via the Workflow tool with {scriptPath: <this file>} and args = the
// events array from launch_exp5_readers.manifest.json. MIRRORS the K-fields
// launcher's conventions deliberately: one COMPLETE preassembled prompt per
// event, replies as RAW TEXT, and no `schema:` anywhere — JavaScript's IEEE-754
// doubles collapse high-precision numbers before Python ever sees them, so the
// authoritative parse stays in raw_transport + the Step-2 checker.
//
// IT IS A SEPARATE FILE, NOT A FLAG ON THE DRAFT LAUNCHER: that one hardcodes
// 36 x (sonnet+opus) = 72 gold drafts and cannot express P1-P5. Neither plan
// may launch the other.
export const meta = {
  name: 'exp5-reader-arms',
  description: 'EXP-5 readers: P1-P4 over 36 events + P5 opus_ref over the h32 12 — 156 calls',
  phases: [
    { title: 'P1-sonnet_run1', detail: '36 events' },
    { title: 'P2-sonnet_run2', detail: '36 events' },
    { title: 'P3-haiku_run1', detail: '36 events' },
    { title: 'P4-haiku_run2', detail: '36 events' },
    { title: 'P5-opus_ref', detail: 'the h32-selected 12-event subsample' },
  ],
}
const prompt = (sid) => {
  const p = PROMPTS[sid]
  if (!p) throw new Error(`no preassembled prompt for ${sid}`)
  return p
}

// ARGS carry the EVENTS and the RUN INPUTS. A bare events array supplies no run
// inputs and therefore REFUSES — which is the point: the gates below are the
// start boundary, not prose in the manifest.
const RAW = typeof args === 'string' ? JSON.parse(args) : args
const EVENTS = Array.isArray(RAW) ? RAW : RAW.events
const RUNTIME = (Array.isArray(RAW) ? null : RAW.runtime) || null
__GUARD__

// ---- START GATE 1: the reviewed K-fields lock -------------------------------
// The manifest records the EXPECTED lock. While it is null the lock does not
// exist yet, so NOTHING may run: a plan whose lock has not been reviewed cannot
// be launched by supplying one at call time either.
if (KFIELDS_LOCK_SHA256 === null)
  throw new Error('REFUSED: the K-fields lock has not been reviewed yet — this plan cannot start')
if (!RUNTIME || !RUNTIME.kfields_lock_sha256)
  throw new Error('REFUSED: no K-fields lock supplied for this run')
if (RUNTIME.kfields_lock_sha256 !== KFIELDS_LOCK_SHA256)
  throw new Error('REFUSED: supplied K-fields lock does not match the approved plan')

// ---- START GATE 2: exact runtime model IDs ----------------------------------
// The WorkOrder resolves exact IDs immediately before an approved run. The plan
// pins ROLES only, so the ALIASES below ('sonnet'/'haiku'/'opus') must never
// reach `agent()`: every tier the schedule uses needs an exact ID supplied now.
const TIERS = [...new Set(ARMS.map(a => a.tier))].sort()
const IDS = (RUNTIME && RUNTIME.model_ids) || {}
for (const t of TIERS) {
  const id = IDS[t]
  if (!id) throw new Error(`REFUSED: no exact runtime model ID supplied for tier ${t}`)
  if (id === t) throw new Error(`REFUSED: tier ${t} was given its ALIAS, not an exact runtime ID`)
}
// P5 is RESTRICTED to the recorded h32 subsample. The restriction lives with
// the schedule, so a caller cannot widen it by passing more events.
const inP5 = (sid) => SUBSAMPLE.includes(sid)
const full = ARMS.flatMap(a =>
  EVENTS.filter(ev => a.scope === 'all_36' || inP5(ev.source_id))
        .map(ev => ({ arm: a.arm, role: a.role, tier: a.tier, effort: a.effort,
                      source_id: ev.source_id, ticker: ev.ticker })))
if (full.length !== PLANNED_CALLS)
  throw new Error(`schedule is ${full.length}, plan says ${PLANNED_CALLS}`)

// PHASE 2 — THE RETRY LAUNCH. `runtime.retry` is the list of scheduled pairs
// Python classified as invalid. It can only ever be a SUBSET of the approved
// schedule, so a retry can never reach an event or arm the plan did not
// schedule, and it reuses the SAME manifest-embedded prompt by construction:
// `prompt()` reads the pinned table, and nothing here can supply another.
const RETRY = (RUNTIME && RUNTIME.retry) || null
const scheduled = !RETRY ? full : full.filter(s =>
  RETRY.some(r => r.arm === s.arm && r.source_id === s.source_id))
if (RETRY && scheduled.length !== RETRY.length)
  throw new Error(`retry names ${RETRY.length} pairs, ${scheduled.length} are in the plan`)

const results = await pipeline(
  scheduled,
  s => agent(prompt(s.source_id), {
    label: `${s.arm}:${s.ticker}:${String(s.source_id).slice(-6)}`,
    phase: `${s.arm}-${s.role}`,
    model: IDS[s.tier], effort: s.effort, agentType: 'lean-probe',
  }).then(text => ({ arm: s.arm, source_id: s.source_id, text,
                     // TRUSTED PROMPT EVIDENCE: the hash of the exact pinned
                     // bytes THIS call used, emitted by the launcher itself.
                     // A caller cannot assert it and cannot substitute another
                     // prompt — `prompt()` reads the embedded table.
                     prompt_sha256: PROMPT_SHA[s.source_id],
                     attempt: RETRY ? 2 : 1 }))
)
const done = results.filter(Boolean)
log(`produced ${done.length}/${PLANNED_CALLS} planned calls`)
return { planned: PLANNED_CALLS, produced: done.length, results: done }
