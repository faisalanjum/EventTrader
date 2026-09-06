the freeze source that carried the automatic short-test cache (Codex SEQ 1745 item 1).
Its bound_identity() hashed only the test file, because deps_of() cannot fold a path built
with dirname(__file__), so a change to the tested freeze or handoff left the key identical.
Kept as the failing control; the cache is removed from the live owner.
