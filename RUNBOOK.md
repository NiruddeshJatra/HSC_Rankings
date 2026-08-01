# Result-day runbook — SSC 2026

Results publish **10 August 2026**. Everything below can be done from a phone
using the GitHub app. Follow the steps in order. Where a step says **STOP**, stop.

Nothing here is urgent enough to skip a check. A wrong parse published is far
worse than a day's delay.

---

## Before the day

1. Confirm the 2026 roll ranges for Science, Business Studies and Humanities,
   from the board or the institution. Write them down.
2. Confirm the `DATABASE_URL` secret exists: GitHub app → repo → Settings →
   Secrets → Actions. It must be the Supabase **session** pooler, **port 5432**
   (not 6543 — transaction pooling breaks this job's bulk reads).
3. Confirm the rehearsal passed. Two ways, either is fine:
   - **Without the board** (works any time of year): run "Scrape results" with
     `fixture_mode` ticked, `mode=sample`, `science_start=300001`,
     `science_end=300020`. Leave `base_url` blank. It reads 20 saved pages from
     `.github/fixtures` and issues no HTTP.
     **It must report exactly 3 warnings** — a blank result and a missing GPA on
     roll `300018`, an unknown subject code `999` on roll `300019`. Zero warnings
     means the check itself is broken, not that the data is clean.
   - **Against the board**: `exam=SSC`, `year=2025`, the 2025 base URL, a narrow
     roll range, `mode=sample`. It must print records and write nothing.
4. Confirm `SSC_2026` either has no `ExamSet` row yet, or has one with
   `rankings_published = False`.

---

## On the day

### 1. Find the result URL

Open the BISE-CTG site and find this year's individual-result page. The path
changes every year:

- 2024: `h1624`
- 2025: `h_x_y_ctg25`
- 2026: unknown — read it off the page

Copy the base path **without** the trailing script name, e.g.
`https://sscresult.bise-ctg.gov.bd/<this-year-path>/individual`

### 2. Sample run — one group

GitHub app → Actions → **Scrape results** → Run workflow.

- `exam` = `SSC`, `year` = `2026`
- `base_url` = the path from step 1
- Fill in **one** group's start/end. Leave the other two blank.
- `mode` = **sample**

**STOP and read the summary.** It prints one line per record. Check:

- names present and not garbled
- roll numbers match the range you asked for
- GPA between 0 and 5
- every subject code recognised (the digest flags unknown ones)
- marks plausible
- result status present (`PASS` / `FAIL`, not blank)

**If anything looks wrong, stop entirely. Do not run `full`.**

Nothing was written to the database, so there is nothing to undo.

### 3. Full run — all three groups

Actions → **Scrape results** → Run workflow.

- Same `exam`, `year`, `base_url`
- Fill in **all three** groups' start/end
- `mode` = **full**

This takes hours. It is safe to close the app and come back.

### 4. Read the job summary

Expected shape:

- roughly **100k–130k rows** total across the three groups
- failures are a **small fraction of a percent**
- **zero unknown subject codes**

A group that fails does not abort the others; failures are listed in the summary
and the run is marked failed at the end.

If an unknown subject code passes the abort threshold (50 occurrences) the
scrape aborts by itself and prints the offending codes plus the raw HTML of the
first record containing one. That means `Rankings/subject_maps.py` needs the 2026
codes added before continuing. **STOP** and fix the map first.

### 5. Read the verify output

Same summary page, "Verification" section. **STOP unless all of these are true:**

- zero rows with `rank IS NULL`
- zero duplicate roll numbers
- zero GPA outside 0.0–5.0
- zero blank or null `result`
- zero rows with `total_marks == 0` alongside non-zero subject marks

The workflow fails the job on any of these. A green Verification section means
all five passed.

### 6. Hand-check 5 rolls

Pick 5 rolls from the summary. Look each one up on the board's own portal, on the
phone, and compare name, GPA, result and subject marks.

This is the only check that catches a parse that is internally consistent but
systematically wrong. **STOP on any mismatch.**

### 7. Publish

Actions → **Publish rankings** → Run workflow → `exam_type` = `SSC_2026` → Run.

It re-runs verification first and stops there on any failure. It also refuses on
its own if any row still has a null rank.

### 8. Check the live site

- The SSC 2026 group pages show tables
- An individual result page shows correct marks, the `/1300` denominator, the
  percentile, and the share card

### 9. Request indexing

Google Search Console → URL Inspection → Request Indexing, for the three new
group URLs.

### 10. Share.

---

## If anything fails

- **Stopping is safe.** The exam set stays unpublished and the site keeps serving
  2024 and 2025 correctly. Nothing is broken by stopping.
- **Re-running is safe.** The full run uses `--resume`, so a re-run skips rolls
  already stored. Run it as many times as needed.
- **Ranking is safe to re-run.** `rank_students` recomputes every rank in a group
  from scratch; running it mid-scrape does not corrupt anything, it just ranks
  what is stored so far.
- **To roll back a publish:** Actions → **Publish rankings** → Run workflow →
  `exam_type` = `SSC_2026`, tick `unpublish` → Run.
  (Equivalent CLI: `python manage.py publish_examset --exam-type SSC_2026 --unpublish`.)
- **Missed rolls** are uploaded as workflow artifacts (`misses_ssc_2026_<group>.txt`),
  one file per group.

## Guards that are already in place

You do not need to remember these — they fire on their own.

- `scrape_results` refuses to write into an exam set whose rankings are already
  published, unless `--force` is passed. A mistyped year cannot overwrite a live
  set. (`--print-only` is exempt: it writes nothing.)
- The scrape aborts after 20 consecutive failures and prints the raw HTML of the
  first one — that is what a board page-format change looks like.
- The scrape aborts after 50 occurrences of an unmapped subject code.
- `verify_examset` exits non-zero on null ranks, duplicate rolls, out-of-range
  GPA, blank results, or zero totals with non-zero subject marks.
- `publish_examset --publish` refuses if any row has `rank IS NULL`.
- The scrape workflow never calls `publish_examset`. Going live is always a
  separate, deliberate run of the Publish workflow.
