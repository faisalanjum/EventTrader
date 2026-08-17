#!/usr/bin/env python3
"""Turn a copy of the dense choice_v2.py into the COMPACT-encoding variant:
  - no two-space indent on choice lines (2 tokens/line = 10% of the prompt)
  - the `cols:` legend once in the instructions instead of once per ROW (7.6%)
Everything else (occurrence labels, ordering, priming, freeze) is unchanged.
Usage: python3 patch_choice_v2_compact.py <path/to/choice_v2_compact/choice_v2.py>"""
import sys, py_compile
path = sys.argv[1]
src = open(path, encoding="utf-8").read()
if "COMPACT ENCODING" in src:
    print("already patched"); sys.exit(0)

old_id = 'TEST_ID = "QF-01-CHOICE-V2-DEV"'
assert old_id in src
src = src.replace(old_id, 'TEST_ID = "QF-01-CHOICE-V2-COMPACT-DEV"', 1)

old_legend = ('        "Source-derived choices "\n'
              '        "(each row lists: choice|occurrence|value|headers):",\n'
              '    ]\n')
assert old_legend in src
new_legend = ('        "Source-derived choices. Every choice line is "\n'
              '        "choice|occurrence|value|headers:",\n'
              '    ]\n')
src = src.replace(old_legend, new_legend, 1)

old_hdr = ('            lines.extend(["", header,\n'
           '                          "  cols: choice|occurrence|value|headers"])\n')
assert old_hdr in src
new_hdr = ('            # COMPACT ENCODING (2026-08-16): the per-row `cols:` legend cost\n'
           '            # 12 tokens x 41 rows (7.6% of the prompt); it is stated once in\n'
           '            # the instructions instead.\n'
           '            lines.extend(["", header])\n')
src = src.replace(old_hdr, new_hdr, 1)

old_line = ('        lines.append(\n'
            '            f"  {item[\'choice\']}|{occurrence_in_row}|{item[\'value\']}|{heads}"\n'
            '        )\n')
assert old_line in src, "choice line emit not found"
new_line = ('        # COMPACT ENCODING (2026-08-16): the two-space indent tokenised as\n'
            '        # two separate tokens on every line (10% of the whole prompt).\n'
            '        lines.append(\n'
            '            f"{item[\'choice\']}|{occurrence_in_row}|{item[\'value\']}|{heads}"\n'
            '        )\n')
src = src.replace(old_line, new_line, 1)

open(path, "w", encoding="utf-8").write(src)
py_compile.compile(path, doraise=True)
print("patched + compiled OK:", path)
