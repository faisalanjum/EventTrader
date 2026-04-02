---
description: "Test disableDeepLinkRegistration setting (v2.1.83)"
---

Check if the `disableDeepLinkRegistration` setting is recognized by the CLI.

1. Run: `claude config list 2>&1 | grep -i deep` via Bash to see if the setting appears
2. Check if any `.desktop` file related to claude-cli exists: `find /home/faisal/.local/share/applications -name '*claude*' 2>/dev/null; find /tmp -name '*claude*desktop*' 2>/dev/null`
3. Write results to `/tmp/test-v183-deep-link.txt`:
   - Line 1: `SETTING_RECOGNIZED=` YES if grep found it, NO otherwise
   - Line 2: `DESKTOP_FILES_FOUND=` list of any .desktop files found, or NONE
   - Line 3: `VERSION=v2.1.83`
4. Stop.
