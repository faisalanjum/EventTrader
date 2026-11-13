# Notion instruction 06 · keep one idea: label sections by matching stored text

Written by Fable for the Opus agent, 11 Nov 2026. The owner asked for this note so the idea is not forgotten. It is an idea only, not a decision.

Page: `1 · Prepare` (id `3eca0a3f310681ffb36de687666c09f0`).

## What to do

Add one closed toggle as the very last block of the page. Do not replace the page content, so the chart stays a diagram.

Toggle title: `💡 Idea to keep: label sections by matching stored text (not decided)`

Inside the toggle, put exactly this, in this order.

**Paragraph:**

Goal: find where each section of a filing (for example "Item 2.02") starts and ends in our extracted units, with no AI. This would fill the open part C · Label.

**Bulleted list:**

- Where the section text comes from: for old filings, the sections already stored in the database; for new filings, the same text our ingestion gets from the sec-api service before saving.
- Exhibits need no matching: one exhibit is one file.

**Heading (smallest size):** `Steps`

**Numbered list:**

1. Split our units into words, in reading order (a table's cells row by row), remembering which unit each word came from.
2. Split the stored section text into words.
3. Look for that run of words in ours.
4. Accept only when it is found word for word and exactly once. The first and last matched words give the section's first and last unit. Anything else is flagged, never guessed.

**Heading (smallest size):** `Tried once, 11 Nov 2026`

**Table with a header row:**

| Stored section (AMG 8-K, main page) | Our units |
|---|---|
| Item 2.02 Results of Operations | 32–33 |
| Item 8.01 Other Events | 34–35 |
| Item 9.01 Exhibits | 36–39 |

**Bulleted list:**

- 3 of 3 matched word for word, each found once, each starting and ending on whole units.
- Not proven: one 8-K only, the easy case. Long reports (10-Q, 10-K) are untested: their contents page repeats item titles, and the service may clean text its own way.

**Heading (smallest size):** `The code`

**Code block, language Python:**

```python
def words(unit):  # a unit's words in reading order; a table's cells row by row
    cells = sorted(unit['cells'], key=lambda c: (c['r'], c['c'])) if unit['kind'] == 'table' else [unit]
    return [w for c in cells for w in str(c.get('text') or '').split()]

def locate(units, section_text):  # (first unit, last unit) of the section, or None unless found exactly once
    stream = [(w, i) for i, u in enumerate(units) for w in words(u)]
    ours, theirs = [w for w, _ in stream], section_text.split()
    hits = [k for k in range(len(ours) - len(theirs) + 1) if ours[k:k + len(theirs)] == theirs]
    return (stream[hits[0]][1], stream[hits[0] + len(theirs) - 1][1]) if len(hits) == 1 else None
```

## Rules

- Leave the toggle closed.
- Change nothing else on the page.
- Add no words beyond what is written here. Keep the code exactly, including its two comments.
- If something cannot be done as written, do the nearest simple thing and say so.
- Reply with what you did, and anything you did differently.
