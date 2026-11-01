# QF-01 row-v3 development test

Goal: test only whether Qwen identifies the correct source-table row for a
known Driver.

```text
real HTML
  -> deterministic row menu
  -> Qwen chooses one row or null
  -> code applies the request's stated occurrence
  -> code copies the exact source evidence
```

The occurrence rule is not learned from these 93 cases. Their existing
contract defines occurrences as numeric cells ordered left-to-right. Code
applies that rule only when the parser proves the order and the selected row
has the declared number of cells; otherwise it abstains.

This is a development comparison because the 93 answers have already been
opened. It cannot authorize production even if it reaches 93/93. A fresh,
unseen set remains required.

Commands:

```bash
cd /home/faisal/EventMarketDB/.claude/plans/Drivers/FinalDesign/QwenTests/table_evidence/row_v3
/home/faisal/EventMarketDB/venv/bin/python row_v3.py verify
/home/faisal/EventMarketDB/venv/bin/python row_v3.py run
/home/faisal/EventMarketDB/venv/bin/python row_v3.py score
```

No model call is made by `prepare` or `verify`. Only `run` calls Qwen.
