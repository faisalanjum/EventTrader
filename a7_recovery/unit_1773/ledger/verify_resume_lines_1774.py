# -*- coding: utf-8 -*-
"""Verify Codex SEQ 1774's resumption lines in the published transcript.

Prints how many of the four named physical lines hash exactly as Codex gave
them. Nothing is written; the transcript is read only.
"""
import hashlib, io

T = ("/home/faisal/EventMarketDB-driver-recovery/a3_recovery/regen_1541/"
     "evidence/transcript/accepted_prefix.jsonl")
WANT = {90941: "167f45e5534809daf1425c79eab9323c97a4f97d3bae960e28bf1b56979bded5",
        90983: "0239a6c3867184a0f74b7b3d54bcb8e016053d48960deb38d7c1f6782e4c25e4",
        90986: "c13a4d14a9ed025b31f6cc186ef776c543ce30a5e6cab3b3594938acd0a0a4eb",
        91022: "e528861b562f332728b397424f96b5c63f5b57fde8a0901746e230d24c0b3940"}

n = 0
with io.open(T, encoding="utf-8") as fh:
    for i, line in enumerate(fh, 1):
        if i in WANT and hashlib.sha256(line.encode("utf-8")).hexdigest() == WANT[i]:
            n += 1
print(n)
