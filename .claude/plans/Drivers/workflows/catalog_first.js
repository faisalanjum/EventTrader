// ============================================================================
// ⚠️  RAISE TO USER BEFORE USING OR WIRING THIS FILE — design is still changing.
//
//  NOT USED IN STEP 1 (building the Driver catalog menu). Step 1 =
//    menu_build.js (blind per-company naming) + reconcile.js (dedup ‖ G2 →
//    Refute → writer → validate). This G1 module is for PRODUCTION live-reuse
//    and the honesty gate — both come later.
//
//  REBUILD PENDING: the docs (DriverExperiment.md "Primary priorities" North
//    Star · Drivers.md §2 · DriverOntology R1) now specify PROPOSE-FIRST reuse
//    — the producer coins its own exact name BLIND, THEN is shown the retrieved
//    related drivers and reuses only on EXACT meaning. The code BELOW still
//    implements the OLD catalog-first flow (catalog shown up front). The user is
//    still deciding HOW related drivers are shown/sorted for reuse, so DO NOT
//    rebuild or wire this yet — confirm the final reuse-display rules first.
// ============================================================================
export const meta = {
  name: 'driver-catalog-first-g1',
  description: 'G1 — CATALOG-FIRST reuse (reusable). For each new event, show the producer the nearest visible catalog names and REUSE if EXACT same meaning, else CREATE a new candidate (which then goes through the G2 gate) or SKIP. This is the PRODUCTION mechanism and the core of the honesty gate. Pass events + the already-retrieved visible catalog names via args.',
  phases: [ { title: 'CatalogFirst' } ],
}

const ONT = '/home/faisal/EventMarketDB/.claude/plans/Drivers/DriverOntology.md'
// args = { events: [ { ticker, date, text } ], catalog: [ ..nearest existing driver_names visible at/before the event.. ] }
const events  = (args && args.events)  || []
const catalog = (args && args.catalog) || []

const SCHEMA = { type:'object', additionalProperties:false, required:['ticker','date','decisions'], properties:{
  ticker:{type:'string'}, date:{type:'string'},
  decisions:{type:'array', items:{type:'object', additionalProperties:false, required:['candidate_cause','action','reason'], properties:{
    candidate_cause:{type:'string', description:'the real driver the evidence attributes the move to'},
    action:{type:'string', description:'reuse | create | skip'},
    reuse_name:{type:'string', description:'existing catalog name reused, if action=reuse, else ""'},
    new_name:{type:'string', description:'proposed new driver_name, if action=create, else "" (it then goes to the G2 gate)'},
    reason:{type:'string'} }}} } }

if (!events.length) {
  log('catalog_first (G1): no events passed via args.events — nothing to do. Pass { events:[{ticker,date,text}], catalog:[names] }.')
  return { note: 'no events supplied', catalog_size: catalog.length }
}

phase('CatalogFirst')
const out = (await parallel(events.map(ev => () => agent(`Read ${ONT} (the rules). You are a producer applying CATALOG-FIRST reuse (G1) — reuse before you create.
EVENT  (${ev.ticker} ${ev.date}):
${ev.text}
VISIBLE CATALOG NAMES (already retrieved for this event; reuse before creating; only names visible on or before this event date): ${JSON.stringify(catalog)}
For each real causal driver the evidence attributes the move to:
- if an EXACT same-meaning name already exists in the catalog → action=reuse (put it in reuse_name). A brand/segment metric is NOT the same as its company-wide form.
- else propose a specific new name per DriverOntology → action=create (new_name); it will then pass through the G2 gate.
- if the text is vague or a one-off with no reusable driver → action=skip.
Return the SCHEMA object for this event.`, {schema:SCHEMA, label:`g1:${ev.ticker}:${ev.date}`, phase:'CatalogFirst'}))) ).filter(Boolean)
return out
