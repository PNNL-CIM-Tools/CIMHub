---
name: cimhub-style
description: CIMHub coding rules in priority order (KISS, DRY, readable, maintainable) with the agent self-check. Use when writing, reviewing or refactoring any Python in this repo.
---

# CIMHub coding style

Priority order: **KISS → DRY → Readable → Maintainable**. When two rules conflict, the earlier one wins.

## Rules

1. **KISS first.** Write the simplest code that meets the requirement. If you cannot explain a function in two or
   three sentences, it is too complex. No "manager of managers", nested factories or needless indirection.
2. **DRY, not dogmatic.** Put repeated logic in one well-named function. However, helper functions must contain at 
   least 3-5 lines of code and be called at least 3-5 times in order to justify their existence. No one-line wrappers
   of a def _get_something(): return get_attr(something, value)
3. **No over-abstraction.** Abstract only real, repeated, stable patterns. No meta-frameworks, super-generic base
   classes, deep inheritance trees or "just in case" layers. Prefer concrete, domain-named functions.
4. **No over-engineering (YAGNI).** Build what is asked for now. No speculative flags, extension points or options.
5. **Fail fast.** Raise a clear error rather than guess. At most one or two fallbacks, each deliberate and
   documented. "Try this, else that, else the other" is a design smell.
6. **No blanket try/except.** Catch only where you can handle the error: recover in a defined way, or add context
   and re-raise. Never swallow an exception. Let the rest bubble up to a clear boundary.
7. **Functional, side-effect-minimal.** Clear inputs and outputs, no hidden state. Keep helpers pure (no I/O, no
   globals). Name side-effecting functions for what they do (`write_documents`, `add_to_graph`).
8. **Readable over clever.** Explicit loops and conditionals over dense one-liners. Meaningful names, no cryptic
   abbreviations. If the clever version needs a long comment, write the obvious version.
9. **Small, cohesive modules.** One job per module or class. No god objects or catch-all utility modules. Don't
   create dependencies between unrelated parts of the code.
10. **Maintainable.** Add or update tests for any non-obvious logic. Validate inputs where it matters and fail with
    an actionable message. Log at meaningful boundaries, not on every line.

## Examples

```python
# BAD: fallback chain that hides which source was used
def base_kv(bus):
    try:
        return bus.kv
    except AttributeError:
        try:
            return bus.base_kv
        except AttributeError:
            return 12.47

# GOOD: one source, a clear error
def base_kv(bus):
    if bus.kv is None:
        raise ValueError(f"bus {bus.name}: kv is not set")
    return bus.kv
```

```python
# BAD: swallows every error, returns a value that looks valid
try:
    phases = parse_phases(text)
except Exception:
    phases = "ABC"

# GOOD: catch the one error you can explain, add context, re-raise
try:
    phases = parse_phases(text)
except KeyError as error:
    raise ValueError(f"{record_id}: unknown phase suffix {text!r}") from error
```

## Self-check before finishing any change

1. Is this the simplest solution that clearly solves the problem?
2. Am I repeating logic that should be shared?
3. Am I adding abstractions or fallbacks to feel "safe" rather than because they are needed?
4. Will a person reading this later quickly see what it does and why?

If any answer is "no" or "not really", rewrite until it is "yes".
