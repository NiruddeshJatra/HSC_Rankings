# Changelog

## 2026-08-01 — Offline rehearsal mode for the scrape workflow

- `scrape_results --fixture-dir <dir>` reads each roll from `<dir>/<roll>.html`
  instead of issuing HTTP requests. Parsing, the roll assertion, the GPA range
  check, unknown-subject-code detection and the digest all run unchanged — the
  post-fetch pipeline moved into a `handle_html()` both paths call, so there is
  no second code path to drift. `--base-url` is now required only when
  `--fixture-dir` is absent.
- New `.github/fixtures/`: 20 SSC result pages, rolls 300001–300020, so the
  workflow can be rehearsed when the board's endpoint is unavailable — which is
  most of the year, and possibly on the morning it matters. Roll 300018 has no
  result status or GPA and roll 300019 carries an unmapped subject code, so a
  rehearsal proves the warning path fires; roll 300020 is a genuine FAIL that
  must *not* be flagged.
- Fixtures are **synthetic**. A real result page carries the student's name,
  father's name, mother's name and registration number — the exact fields
  individual result pages refuse to publish — so committing 20 real pages would
  leak in git history what the site declines to serve. The DOM is copied from
  the real page; the parser cannot tell the difference.
- New `fixture_mode` input on `scrape.yml`. It passes `--fixture-dir`, drops the
  `base_url` requirement, and **refuses to run with `mode=full`**: storing
  invented students in the real exam set is precisely what it must never do.

## 2026-08-01 — Remote result-day scraping via GitHub Actions, pre-flight hardening

- New `.github/workflows/scrape.yml` (`workflow_dispatch` only): runs the
  scrape from a phone on result day. `mode=sample` parses 20 rolls per group
  with `--print-only` and writes nothing; `mode=full` scrapes with `--resume`,
  then ranks and verifies. Per-group failures don't abort the other groups.
  Uses the Supabase **session** pooler (port 5432) — transaction pooling breaks
  the bulk reads `--resume` and `rank_students` perform — and asserts
  `SELECT version()` says PostgreSQL before touching anything.
- `publish_examset` is deliberately unreachable from that workflow. Going live
  is a separate `.github/workflows/publish.yml` run (with an `unpublish`
  toggle for rollback), taken after a human reads the verification output.
- New `.github/scripts/sample_digest.py` condenses `--print-only` output from
  ~12 lines per record to one, and flags blank names, blank result statuses,
  out-of-range GPAs and unknown subject codes — the job summary is the whole
  interface on the day, and it has to be readable on a phone.
- New `RUNBOOK.md`: numbered result-day procedure with explicit stop
  conditions, written to be followed on a phone.
- `scrape_results` now refuses to write into an exam set whose rankings are
  already published unless `--force` is passed, so a mistyped `--year` can't
  overwrite a live set. `--print-only` is exempt — it writes nothing, so the
  sample pre-flight still works against a published set.
- The unknown-subject-code abort (50 occurrences) now prints the raw HTML of
  the first record containing each offending code, not just the code and a
  sample label — matching what the consecutive-failure abort already did.
- `verify_examset` now fails on rows where `total_marks` is 0 while subject
  columns hold marks (the HSC_2024 defect class). All three published exam
  sets pass the new check; their remaining `total_marks == 0` rows are genuine
  zero-mark candidates.

## 2026-07-28 — Data integrity fixes, group-URL bug, percentile, share card

- Fixed live bug: ranking-page URLs built from the raw DB group value (e.g.
  `BUSINESS STUDIES`) produced `%20`-encoded links; `results` view now exposes
  a canonical `group_slug` and 301-redirects any non-canonical incoming group
  segment.
- `SUBJECT_MAX_MARKS` replaced with a level-aware table in new
  `Rankings/subject_maxes.py` — HSC's two-paper subjects (physics, chemistry,
  civics, etc.) were wrongly defaulting to 100 instead of 200, understating the
  individual-result denominator (e.g. HSC Science showed `/850` instead of
  `/1300`). Verified zero subject marks now exceed their assigned max across
  all three published exam sets.
- Normalized 90,714 SSC_2025 rows where the board portal's bare `GPA=X.XX` (no
  explicit status) was stored as a blank `result` instead of `PASS`
  (migration `0019`); fixed `scrape_results` so SSC 2026 stores this correctly
  at capture time; `verify_examset` now fails on any blank/null `result`.
- Repaired 84 HSC_2024 rows where `total_marks` didn't match the sum of
  subject fields — 80 were stuck at 0 (new `repair_zero_totals` command,
  dry-run by default), 4 had a partial total that only counted
  bangla+english+ict (migration `0021`, hand-verified against the raw subject
  data before fixing). HSC_2024 re-ranked after both fixes; leaderboard top 10
  unchanged (all affected rows were bottom-of-table).
- Removed `choices` from `StudentInfo.exam_type` (migration `0020`) — it isn't
  DB-enforced and forced a migration for every new exam set; validation lives
  in `scrape_results`'s `--exam`/`--year` args.
- Added group percentile and institution rank to the individual result page
  (two `count()` queries against existing indexes); added a shareable result
  card (`#share-card` in `individual_result.html`) sized for a phone
  screenshot, with a Web Share API button (clipboard-copy fallback) and an
  explanatory line above it so the card's purpose is obvious.
- Desktop/mobile visual parity fix in `site.css`: student names, roll numbers,
  institution, and marks were rendering at full/green contrast on desktop's
  `<table>` but muted/bold on mobile's card view; desktop now matches mobile's
  color choices (green reserved for rank numerals and GPA). Desktop body/table
  type size bumped via `@media (min-width: 800px)`.
- New read-only `audit_data.py` management command for future data-integrity
  spot checks (result/gpa/marks anomalies per `--exam-type`; never writes).

## 2026-07-27 — Forest / "Graph Khata" visual redesign, brand assets

- New site-wide dark theme (Marcellus + Alegreya Sans + Kalam fonts, forest-green
  palette with mauve/amber/copper accents), consolidated into a single
  `static/css/site.css` — deleted the old per-page `global.css`/`home.css`/
  `individual_result.css`.
- Added favicon set, logo, and OG share image (`static/favicon/`,
  `static/images/logo-*`, `static/images/og-base-1200x630.png`) from the design
  project; base.html now links real favicons instead of a missing `logo.ico`.
- `Rankings.context_processors.exam_sets` now returns every exam set (published
  and collecting) instead of published-only, so header nav, footer, and the home
  "All rankings" index share one data source — home's collecting-state pill and
  the footer's pulsing "collecting" indicator both come from this.
- Ranking table now ships real duplicate markup for desktop (table) and mobile
  (card-grid), toggled by CSS breakpoint rather than squeezing one table — top-3
  rows highlighted by `student.rank <= 3`, not page position.
- Individual result page: subject marks now show progress bars against public
  BD board syllabus max-marks (`SUBJECT_MAX_MARKS` in `views.py`); share row
  replaced raster Twitter/Instagram/Telegram icons with inline SVG
  WhatsApp/Facebook + a copy-link button (`static/js/site.js`).
- New `roll_not_found.html` — a valid exam/year with no matching roll number now
  gets a dedicated "no result for roll X" page (still 404 status) instead of the
  generic not-found page.
- Zero `style=""` attributes anywhere: per-row animation delay and progress-bar
  width are expressed as CSS classes (`stagger-N`, `substagger-N`, `bar-N`) via
  new filters in `Rankings/templatetags/marks_extras.py`.
- Repo hygiene: untracked all `__pycache__/*.pyc` (already gitignored but
  previously committed), removed stray design-source files accidentally left in
  the repo root.

## 2026-07-27 — Restore committed staticfiles (broke prod static serving)

- Previous entry's "untrack staticfiles/ build artifacts" was wrong: `vercel.json`
  uses the legacy `builds` array with `@vercel/python`, which never runs
  `collectstatic` and makes Vercel ignore any build command. WhiteNoise serves
  `/static/...` from `STATIC_ROOT` (`staticfiles/`), so untracking it would have
  shipped an empty directory and 404'd every static asset in production.
- Removed `staticfiles/` from `.gitignore`, re-ran `collectstatic`, re-committed
  the output. Documented the constraint in `CLAUDE.md` to prevent repeat.

## 2026-07-27 — Settings correctness fix, footer privacy cleanup, repo hygiene

- Added `DISABLE_SERVER_SIDE_CURSORS = True` to settings.py — required for
  Supabase's transaction pooler (port 6543); without it `QuerySet.iterator()`
  fails at runtime with an opaque pooler error.
- Fixed `LEGACY_SQLITE` DB entry to point at `db_legacy.sqlite3` (previously
  pointed at a `db.sqlite3` that no longer exists, which silently created an
  empty file instead of erroring).
- Footer: removed phone number and GitHub repo link, replaced contact email,
  added attribution line. Exam-set list is now dynamic via new
  `Rankings/context_processors.py` (`exam_sets`) instead of hardcoded HTML —
  new exam sets (e.g. SSC 2026) now appear automatically once published.
- Deduplicated `WebSite` JSON-LD block in `templates/base.html`; made
  og/twitter titles year-agnostic.
- Repaired one junk `StudentInfo` row (SSC_2025, all fields blank) that was
  blocking `publish_examset`; re-ranked and published SSC_2025.
- Repo hygiene: untracked `.pyc` files, `exam_result_backup.sql` (24MB MySQL
  dump with PII), and `staticfiles/` build artifacts that were tracked despite
  being gitignored; extended `.gitignore` accordingly.
