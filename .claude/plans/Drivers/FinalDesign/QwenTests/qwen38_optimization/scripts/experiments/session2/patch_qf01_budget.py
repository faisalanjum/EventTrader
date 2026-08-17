import sys, py_compile
p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='''    maximum = max(byte_counts)
    if maximum >= budget:
        raise ValueError(
            f"input budget unsafe: largest prompt is {maximum} UTF-8 bytes "
            f"against a {budget}-token budget")
    return {
        "largest_case_utf8_bytes": maximum,
        "conservative_input_token_budget": budget,
    }
'''
new='''    maximum = max(byte_counts)
    # The original compared raw UTF-8 BYTES against a TOKEN budget (~3-4x too
    # strict; measured 2026-08-16 with the Qwen tokenizer: the largest aligned
    # prompt is 12,276 bytes = 3,920 tokens). Convert at 3 bytes/token, which is
    # still conservative for these rendered tables (3.13 chars/token measured).
    max_tokens_estimate = (maximum + 2) // 3
    if max_tokens_estimate >= budget:
        raise ValueError(
            f"input budget unsafe: largest prompt is {maximum} UTF-8 bytes "
            f"(~{max_tokens_estimate} tokens) against a {budget}-token budget")
    return {
        "largest_case_utf8_bytes": maximum,
        "largest_case_token_estimate": max_tokens_estimate,
        "conservative_input_token_budget": budget,
    }
'''
assert old in s; s=s.replace(old,new,1); open(p,"w",encoding="utf-8").write(s); py_compile.compile(p,doraise=True); print("budget patched", p)
