"""Do not ask numeric-forecast questions about verified speaker metadata.

Reuse the repository's native header recognizer and the source's own speaker
map. Preserve the entire text for model context and exact quotes. Unknown or
inconsistent headers keep every number; no speaker-name or finance word list.
The existing spoken_text helper joins/strips text and loses offsets, so this
adapter uses its compiled matcher solely to delimit candidate enumeration.
"""
import re
import sys

sys.path.insert(0, '/home/faisal/EventMarketDB')
from scripts.driver_seed.relocate_probe.phase2.m1_transcript_census import SPEAKER

TOKEN = re.compile(r'\S+')


def body_start(text, speakers, entry_speaker=None):
    if not isinstance(speakers, dict) or not speakers:
        return 0, 'missing_speaker_metadata'
    match = SPEAKER.match(text)
    if not match:
        return 0, 'no_native_header'
    name = match[0][:match[0].rfind('[')].rstrip()
    if name not in speakers:
        return 0, 'header_name_not_in_metadata'
    if entry_speaker is not None and entry_speaker != name:
        return 0, 'entry_speaker_mismatch'
    return match.end(), 'verified_header'


def digit_tokens(text, speakers, entry_speaker=None):
    start, _ = body_start(text, speakers, entry_speaker)
    return [{'start': match.start(), 'end': match.end(), 'text': match[0]}
            for match in TOKEN.finditer(text, start)
            if any(c.isdecimal() for c in match[0])]
