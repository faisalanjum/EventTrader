---
name: test-v1105-long-desc
description: "V1105_LONGDESC_START_MARKER. This skill tests v2.1.105's skill-description cap raise from 250 to 1536 characters. If this description appears truncated in the skill listing system-reminder at around character 250, the cap was not raised; if it appears truncated at around 1536, the cap was raised correctly per changelog. The test sentinel markers are placed at specific character offsets: V1105_OFFSET_100 is at char 100 approximately, V1105_OFFSET_300 is at char 300 approximately (old cap would truncate this), V1105_OFFSET_700 is at char 700 approximately, V1105_OFFSET_1000 is at char 1000, V1105_OFFSET_1200 is at char 1200, V1105_OFFSET_1400 is at char 1400, and V1105_END_MARKER is the last visible sentinel. This description also contains deliberately redundant filler to reach the target length without substantive content since the purpose is only to verify truncation behavior rather than to provide meaningful guidance. filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler filler V1105_END_MARKER"
---

# Test: Skill description cap raise (v2.1.105)

## Hypothesis
v2.1.105 raised the skill-description listing cap from 250 chars to 1,536 chars.

## How to read the result
Inspect the skill listing in system-reminders. If `V1105_END_MARKER` appears, the full description was delivered (new cap held). If the listing stops before `V1105_OFFSET_300`, old 250-char cap still applies.

This skill body is intentionally empty — the only test signal is whether the frontmatter description gets truncated in the runtime skill listing.
