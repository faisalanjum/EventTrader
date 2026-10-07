"""Picture reading for preparation (owner, Oct 6): Chandra reads every picture and the two free OCR tools give evidence and flags; the
packet is what the final AI reader receives about the picture (Chandra's blocks, free OCR evidence, regions). Sonnet, a second reader,
is kept behind one setting, off by default: on, a flagged picture is read again and compared (the reviewed v6 route). Readers: readers.py."""
from .packets import packet
from .routing import route

FORMAT = 'picture packet 2: extraction status line'                       # 1 = the packet alone; 2 adds the status line (Codex r12 C1)

def status(flags, enable_sonnet, asked, second_text, generated_tokens, limit):
    """The one short extraction-status line, from the existing flags only: missing, incomplete/uncertain ('cut off' says truncation
    only when the token count proves it), possible skipped text ('missed') and unconfirmed text ('no support'), then single reader /
    unverified or two readers compared. 'table' and 'chart text' stay in the record: the packet already shows them."""
    says = ['MISSING: Chandra wrote no usable reading; look at the picture'] if 'no reading' in flags else []
    if 'cut off' in flags:
        says.append('INCOMPLETE: Chandra stopped at its output limit' if limit and (generated_tokens or 0) >= limit
                    else 'INCOMPLETE OR UNCERTAIN: Chandra marked text unreadable or uncertain')
    if 'missed' in flags: says.append("possible skipped text: both free OCR tools read text outside Chandra's blocks")
    if 'no support' in flags: says.append('unconfirmed text: a Chandra block that no free OCR tool reads at its place')
    says.append('single reader (Sonnet; Chandra missing), unverified' if second_text and 'no reading' in flags
                else 'two readers (Chandra + Sonnet), compared per block' if second_text
                else ('no reader text (Sonnet ' if 'no reading' in flags else 'single reader (Chandra; Sonnet ')
                + ('off' if not enable_sonnet else 'on, no usable second reading' if asked else 'on, not asked') + ')' + ('' if 'no reading' in flags else ', unverified'))
    return '[EXTRACTION STATUS: ' + '; '.join(says) + ']'


def read_picture(name, picture, chandra_html, generated_tokens, free, limit, enable_sonnet=False, second=None):
    """One picture: (read by Sonnet?, flags, packet text, packet record). chandra_html None = no reading; free = the free OCR's record;
    limit = Chandra's output limit. Flags are the existing checks on Chandra's reading and the free OCR alone: 'no reading' and
    'cut off' mark a failed or partial reading; 'table', 'chart text', 'missed' and 'no support' mark risk. Off (default): second is
    never called and no comparison runs. On: second(picture) -> (text or None, source pointer) is called for a flagged picture.
    The text is the packet with the extraction-status line after its first line; the record carries the mode, flags and line."""
    if enable_sonnet and second is None: raise ValueError('enable_sonnet needs a second reader')
    flagged, flags = route(chandra_html, generated_tokens, free, limit)
    asked = enable_sonnet and flagged
    text, src = second(picture) if asked else (None, None)
    t, rec = packet(name, picture, chandra_html or '', text, src, free=free)
    line = status(flags, enable_sonnet, asked, text, generated_tokens, limit)
    first, rest = t.split('\n', 1)
    rec.update(sonnet='on' if enable_sonnet else 'off', flags=flags, extraction_status=line, format=FORMAT)   # results never mix
    return asked, flags, first + '\n' + line + '\n' + rest, rec
