# 01 · Overview — Driver Final Design

> **Mental model — a driver is an index card.** Like a Zettelkasten slip-box (one idea per card): each driver is one atomic cause on its own card — specific enough to track and update over time, uniquely named so the same cause always lands on the same card, kept as few as possible, and linked to related cards. **One card = one meaning.**

## Purpose — what this is and why it exists

1. The Driver Catalog is one shared master list of "drivers" — the real-world causes that move a stock (for example: same-store sales, the oil price, interest rates).
2. A driver is a reusable cause that can recur. A driver-update is one real occurrence of that cause in a specific event (one earnings call, one news item, etc.). In short: the driver is the blueprint; a driver-update is one stamped copy. *(In coding terms: a driver is a class, and a driver-update is an instance of that class.)*
3. Every driver is backed by a real quote from a filing, transcript, or news item — nothing is invented.
4. The core promise: the same cause always gets the same name everywhere.
5. When two drivers turn out to mean exactly the same thing, we join them with a reversible "same-as" link — both survive, and nothing is ever deleted or merged away. *(How and when this runs is covered in the build section.)*
6. Because the same cause always shares one name, scattered mentions line up into one clean history per cause — both across many companies and over time for the same company.
7. This clean history is what we act on: when a cause meaningfully changes, the system can automatically flag a buy or sell. Ultimately it feeds one loop: learn from the past → predict the next move → trade.
8. Every automated tool (the earnings bot, the news bot) reuses this one shared list, so they all speak the same language.
9. Keep the list as small as possible — but never at the cost of correctness. Small never beats correct.
10. One name = one meaning. A single name must never cover two different causes.
11. We never invent a broad name. Breadth appears on its own, only when the same exact name gets reused across many companies.
12. A name holds only the cause. Everything else — what happened, direction, size, date, company, time period, units — lives in other fields, never in the name.
13. Our edge over products like RavenPack and Bigdata: they only list that an event happened; we go further and grade each cause against what the stock actually did. That grading is how a signal gets checked. Don't drift toward their "just list events" model.

## The one law
Blending two different causes into one name = **permanent damage** (a bad trade you can't undo). Splitting one cause into two names = a **cheap one-line fix**. So when unsure, **keep them separate.**

## Why so strict (history)
Two earlier versions died: version 1 used a fixed word-list and rejected 82% of even-correct names; version 2 merged too eagerly and collapsed three different demand stories into one generic name, then failed a fresh exam. This version: **the AI judges meaning, code only checks structure, and we always lean specific.**

<!-- WORK IN PROGRESS: this Overview file still needs its later slices — the 3 tracks (DriverCatalog / DriverUpdate / Guidance), the authority + reading map, and a status dashboard. Added one approved piece at a time. -->
