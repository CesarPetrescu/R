# R Research Log

## Research rules

- Prefer official documentation.
- Use local `man` pages when command syntax, system behavior, C/POSIX/libc details, or unavailable external docs make them useful.
- Record date, URL or `man <page>`, and concise finding.

## Findings

- 2026-11-22: [The Rust Reference, wildcard pattern](https://doc.rust-lang.org/reference/patterns.html#wildcard-pattern) distinguishes the nonbinding `_` pattern from an identifier. Rustic adopts the discard meaning for `let _ = expr;` only; Rust's ownership rules and other pattern positions are outside this change.
- 2026-05-04: No product-specific external research yet; repository is initially empty and needs a concrete product scaffold.
- 2026-07-31: The cron shell's default `python3` resolves to the Hermes runtime venv without pytest; `/usr/bin/python3` provides pytest 9.0.3. Host verification used `PATH=/usr/bin:$PATH python3 ...` without changing project files or Docker verification behavior.
