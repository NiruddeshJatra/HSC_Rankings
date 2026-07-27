# Changelog

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
