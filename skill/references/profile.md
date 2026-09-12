# The organisation profile

Everything an organisation may declare instead of having it coded. **Every key has a default
that works with no profile at all**, so the skill runs ready-to-use; a profile only narrows.
Written by `scripts/profile_tool.py`, never by hand, and validated on every write.

The transferable idea: an organisation's mapping is its own asset and does not belong in the
generic method. What is generic is that the mapping can be **declared** — so one codebase
serves organisations that keep their meaning in different places.

| Key | Default | What it does |
|---|---|---|
| `organisation` | empty | shown as a chip on the cover |
| `lang` | follow the schedule | `en` or `pt` forces the report language |
| `ev_method` | as the file declares | `physical` or `percent`; recorded as forced in the report |
| `baseline_slot` | elected by coverage | `0`–`10`; recorded as forced in the report |
| `threshold_days` | 30 | E and C, in working days of the activity's calendar |
| `tolerance_days` | 1 | G |
| `checks_optional` | none | `["B","F"]` promotes the standby checks to findings |
| `grouping` | `wbs` | a custom field by alias, name or id |
| `fields.*` | none | discipline, service, section, work_front, justification, quantity, unit, productivity_contracted, regulator_code — each a custom field by alias, name or id |
| `productivity.recent_days` | 30 | the recent-rate window |
| `productivity.thin_evidence_days` · `thin_evidence_share` | 10 · 0.02 | when a rate is flagged as thin evidence |
| `rain.reserve_days_per_month` | 4 | non-working exceptions that make a month a reserve month |
| `lookahead_weeks` | `[4, 8]` | the look-ahead windows |
| `theme.*` | shipped palette | accent, crit, warn, good, font_display, font_sans, font_mono, logo_text |
| `template` | shipped | a customised report template path |
| `sections_hidden` | none | section ids to drop, e.g. `["v6","v9"]` |

**A declared field the file does not have is reported at the top of the report, never
silently ignored.** `profile_tool.py show profile.json model.json` resolves every field against
the file and says which ones were found.

## The two flows

**Organisation profile.** `discover` first, so the person recognises fields instead of
recalling them; then one question at a time for what the file could not settle; then `set`
per answer and `show` to confirm. The questions, in order: which field is the discipline, the
section, the justification, the contracted productivity; whether the earned-value method the
file declares is the one practised; whether B and F count as findings; the threshold; the
baseline slot only if the elected one is wrong.

**Report.** Accent and severity colours, font stacks, a header label, the language if it should
not follow the schedule, and sections to hide. Deeper changes go in a copy of the template:
`templates/report.custom.html` takes precedence and survives updates.

`profile.example.json` at the skill root is a filled example to copy.
