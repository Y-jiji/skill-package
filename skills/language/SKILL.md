---
name: language
description: Display docblock format and upgrade specs for a supported language. No args lists available languages; /language <ext> shows full spec; /language <ext> <section> shows one section (Downgrade, Format, or Upgrade).
---

Dispatch on `$ARGUMENTS`:

**No arguments** — output this fixed listing and stop:

    Available languages: cpp  js  java  python  rust  ts  tsx
    Usage: /language <ext>               — full spec
           /language <ext> <section>     — one section: Downgrade | Format | Upgrade

**One argument `<ext>`** — uppercase the token to form the filename, then `Read`
`skills/language/<EXT>.md` and display its full contents.

**Two arguments `<ext> <section>`** — uppercase `<ext>` to get the filename, `Read`
`skills/language/<EXT>.md`, find the `## <Section>` heading (case-insensitive match on the
section name), and output from that heading through the next `##` heading or EOF, whichever
comes first.
