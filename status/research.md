# R Research Log

## Research rules

- Prefer official documentation.
- Use local `man` pages when command syntax, system behavior, C/POSIX/libc details, or unavailable external docs make them useful.
- Record date, URL or `man <page>`, and concise finding.

## Findings

- 2026-11-21: The [Rust Reference on or-patterns](https://doc.rust-lang.org/reference/patterns.html#or-patterns) defines `A | B | C` as matching any alternative. Rustic adopts only signed integer literals in a `match` arm, retains its own numeric duplicate rule, and does not adopt general Rust pattern semantics.
- 2026-05-04: No product-specific external research yet; repository is initially empty and needs a concrete product scaffold.
- 2026-07-31: The cron shell's default `python3` resolves to the Hermes runtime venv without pytest; `/usr/bin/python3` provides pytest 9.0.3. Host verification used `PATH=/usr/bin:$PATH python3 ...` without changing project files or Docker verification behavior.
