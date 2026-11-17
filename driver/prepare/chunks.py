"""Split existing readback blocks; the complete readback remains their shared context."""
from bisect import bisect_left
from itertools import accumulate
import json


def split_blocks(blocks, num_chunks=1):
    """Return exactly N nonempty, ordered slices, roughly balanced by JSON characters.

    Pass readback's complete top-level blocks so tables, captions and nested lists
    stay together. Nothing is copied, interpreted or removed from a block.
    """
    if type(num_chunks) is not int or not 1 <= num_chunks <= len(blocks):
        raise ValueError("num_chunks must be an integer from 1 to the number of blocks")
    if num_chunks == 1:
        return [blocks[:]]
    sizes = (len(json.dumps(b, ensure_ascii=False, separators=(",", ":"))) for b in blocks)
    ends = list(accumulate(sizes, initial=0))
    chunks, start = [], 0
    for remaining in range(num_chunks, 1, -1):
        target = ends[start] + (ends[-1] - ends[start]) / remaining
        cut = max(start + 1, min(bisect_left(ends, target), len(blocks) - remaining + 1))
        cut = min((cut, max(start + 1, cut - 1)), key=lambda i: abs(ends[i] - target))
        chunks.append(blocks[start:cut])
        start = cut
    return chunks + [blocks[start:]]
