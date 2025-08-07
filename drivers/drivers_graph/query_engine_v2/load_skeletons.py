#!/usr/bin/env python3
"""Load skeleton templates from CSV and convert to JSON for fast access."""

import csv
import json
import pathlib
from collections import namedtuple

Template = namedtuple("Template", "name params cypher comment")

def load_skeletons(path="skeletonTemplates.csv"):
    """Load skeleton templates from CSV file."""
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            # Split param list "ticker1, ticker2, qname" -> ["ticker1","ticker2","qname"]
            params = [p.strip() for p in row["Key Props"].split(",") if p.strip()]
            # Sanity-check placeholder tokens exist in the Cypher
            for p in params:
                assert f"${p}" in row["Cypher"], f"Param ${p} missing in {row['Name']}"
            yield Template(row["Name"], params, row["Cypher"].strip(), row["Comment"])

# Run it once:
if __name__ == "__main__":
    templates = list(load_skeletons())
    print(f"{len(templates)} templates imported OK")
    
    # Dump them to a single JSON file your router can read in <1 ms
    templates_dict = {
        t.name: {
            "params": t.params,
            "cypher": t.cypher,
            "comment": t.comment
        }
        for t in templates
    }
    
    pathlib.Path("templates").mkdir(exist_ok=True)
    pathlib.Path("templates/template_library.json").write_text(
        json.dumps(templates_dict, indent=2)
    )
    print("✅  template_library.json written")