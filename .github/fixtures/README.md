# Scraper fixtures

20 SSC result pages, rolls `300001`–`300020`, for
`scrape_results --fixture-dir .github/fixtures`.

They exist so the scrape workflow can be rehearsed when the board's endpoint is
unavailable — which is most of the year, and possibly on the morning it matters.
Without them, "does the workflow work?" can only be answered by pointing it at a
live portal that may not be serving.

## These are synthetic

Every name, parent name, registration number and institute here is invented. No
real student's result page is committed to this repository.

That is deliberate, not a shortcut. A real page carries the student's name,
father's name, mother's name and registration number — the exact fields
`individual_result.html` refuses to publish. Saving 20 real pages into a public
repo would leak, in git history and forever, what the site itself declines to
show on a page it serves.

The DOM is copied from the real page: same `tftable` / `tftable2` classes, same
`<td>` ordering, same `NNN(GRADE)` mark format. The parser cannot tell the
difference — which is the whole point.

## What each page exercises

| Roll | Case |
|---|---|
| `300001`–`300017` | Ordinary passes across SCIENCE and BUSINESS STUDIES, GPA 3.84–5.00 |
| `300018` | **Broken:** board printed no result status and no GPA. The digest must flag a blank result. |
| `300019` | **Broken:** subject code `999`, absent from `Rankings/subject_maps.py`. The digest must flag an unknown code. |
| `300020` | A genuine FAIL, GPA 0.00. Valid data — it must **not** be flagged. |

A rehearsal that reports zero warnings has failed: `300018` and `300019` are
there to prove the warning path fires, and `300020` is there to prove it does
not fire on data that is merely bad news.

## Regenerating

Fixture content is deterministic (fixed RNG seed), so regenerating produces no
diff churn. `Rankings/tests.py::FixtureModeTests` asserts the counts and the two
broken cases, so an accidental edit here fails the suite.
