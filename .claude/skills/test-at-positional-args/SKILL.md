---
name: test-at-positional-args
description: "Test positional argument substitution ($ARGUMENTS[N] and $N shorthand)"
context: fork
---

# Positional Argument Test

You received these arguments:
- Full arguments string: "$ARGUMENTS"
- Argument 0 (via $ARGUMENTS[0]): "$ARGUMENTS[0]"
- Argument 1 (via $ARGUMENTS[1]): "$ARGUMENTS[1]"
- Argument 2 (via $ARGUMENTS[2]): "$ARGUMENTS[2]"
- Shorthand $0: "$0"
- Shorthand $1: "$1"
- Shorthand $2: "$2"

Write ALL of the above exactly as you see them (after substitution) to:
`earnings-analysis/test-outputs/test-at-positional-args.txt`

Format as:
```
FULL_ARGS: <value>
ARG0_LONG: <value>
ARG1_LONG: <value>
ARG2_LONG: <value>
ARG0_SHORT: <value>
ARG1_SHORT: <value>
ARG2_SHORT: <value>
TIMESTAMP: <current ISO timestamp>
```

Then return "POSITIONAL_ARGS_TEST_COMPLETE".
