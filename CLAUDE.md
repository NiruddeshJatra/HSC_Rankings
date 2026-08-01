# HSC_Rankings

Django 5.1 site scraping Chittagong board (BISE-CTG) SSC/HSC exam results and
publishing independently-computed merit rankings. Deployed on Vercel.

## File Structure

```
.github/
  workflows/scrape.yml  # workflow_dispatch-only remote scraper (sample|full modes);
                         #   never calls publish_examset - see RUNBOOK.md
  workflows/publish.yml # workflow_dispatch-only verify + publish/unpublish
  scripts/sample_digest.py  # condenses --print-only output into a phone-readable
                             #   one-line-per-record job summary
  fixtures/             # 20 synthetic SSC result pages (rolls 300001-300020) for
                         #   scrape_results --fixture-dir; 300018/300019 are
                         #   deliberately broken. See fixtures/README.md
RUNBOOK.md              # result-day procedure, written to be followed on a phone
HSC_Rankings/
  settings.py          # DB (Supabase Postgres via pooler), security, context processors
  urls.py               # root URLconf
Rankings/
  models.py             # StudentInfo, Marks, ExamSet
  views.py               # ranking/search/individual-result views
  urls.py                 # app routes (legacy + year-scoped exam/year/group)
  sitemaps.py             # sitemap.xml generation (excludes individual-result pages)
  context_processors.py   # exam_sets — single source of truth for ALL exam sets
                           #   (published + collecting), used by header nav, footer,
                           #   and home's "All rankings" index
  subject_maps.py         # subject label/code mappings
  subject_maxes.py         # per-subject max marks, keyed by exam level (HSC/SSC
                           #   prefix of exam_type) — single source of truth for
                           #   the individual-result denominator, not a flat dict
  templatetags/marks_extras.py  # stagger_class/subject_stagger_class/bar_class —
                                 # CSS-class helpers so templates need no style=""
  management/commands/
    scrape_results.py       # pulls results from board portal
    transfer_to_postgres.py # legacy sqlite -> Postgres migration
    rank_students.py        # computes rank per exam_type/group
    publish_examset.py      # flips ExamSet.rankings_published (refuses if any rank IS NULL)
    verify_examset.py       # sanity report; fails if any row has rank or result NULL/blank
    check_ranks.py
    audit_data.py           # read-only data-integrity report (result/gpa/marks
                             #   anomalies) per --exam-type; never writes
    repair_zero_totals.py   # --dry-run (default) / --apply: fixes total_marks=0
                             #   rows where subject fields hold real marks
  templates/               # app-local templates (home, results, individual_result,
                           #   roll_not_found — dedicated 404 for a valid exam/year
                           #   with no matching roll_no)
templates/
  base.html              # site shell: nav, footer, meta/JSON-LD, exam-set nav (dynamic)
  methodology.html
  404.html               # generic not-found (unmatched routes)
static/
  css/site.css           # THE stylesheet — see Key Conventions below
  js/site.js             # copy-link clipboard behavior (individual result share row)
  favicon/               # favicon.svg + png sizes + apple-touch-icon (Forest/Graph
                         #   Khata brand assets)
db_legacy.sqlite3        # gitignored backup only — never the active DB, never commit
```

## Key Conventions

- `DATABASES['default']` uses Supabase's **transaction pooler (port 6543)**.
  `DISABLE_SERVER_SIDE_CURSORS = True` in settings.py is required for this —
  don't remove it, `QuerySet.iterator()` (scraper/transfer paths) breaks without it.
- `exam_type` is `{EXAM}_{YEAR}` (e.g. `SSC_2025`) — split on `_` for exam/year,
  never hardcode the mapping elsewhere.
- `Rankings.context_processors.exam_sets` returns **all** `ExamSet` rows (published
  and collecting, each with a `published` flag) — the header nav, footer chip row,
  and home's "All rankings" index all render from this one structure. Don't
  hardcode exam sets or re-query `ExamSet` separately in a view/template; add a
  new exam set once in the DB and it appears everywhere.
- Single stylesheet: `static/css/site.css` (Forest / "Graph Khata" theme — Marcellus
  + Alegreya Sans + Kalam, dark forest-green palette, CSS custom properties at the
  top). No per-page stylesheets, no inline `<style>` blocks, no `style=""`
  attributes in any template. Dynamic per-row values (progress-bar width, fadeUp/
  drawIn stagger delay) are expressed as CSS classes (`bar-N`, `stagger-N`,
  `substagger-N`, 5%/45ms/60ms buckets) via the `marks_extras` template filters —
  add new buckets there and in `site.css` rather than reaching for `style=""`.
  All icons are inline SVG copied from the design reference; no icon fonts, no
  raster share-icon PNGs.
- Subject max-marks live in `Rankings/subject_maxes.py` (`subject_max(exam_type,
  field_name)`), keyed by exam **level** (HSC vs SSC prefix of `exam_type`), not
  a flat dict — HSC subjects outside bangla/english/ict are 200 (two-paper), SSC
  ones are 100. Public BD board syllabus constants, not derived from student
  data. Raises on an unrecognised level; don't reintroduce a single shared
  default, that's exactly the bug this replaced.
- Ranking-page URLs use a canonical `group_slug` (lowercase, spaces→underscores,
  e.g. `business_studies`), exposed by the `results` view and used everywhere a
  URL is built (`templates/base.html`, `results.html`). The view 301-redirects
  any non-canonical incoming group segment (wrong case, `%20`, etc.) to the
  canonical URL — don't build group URLs from the raw DB value again.
- `StudentInfo.exam_type` has no DB-level `choices` (removed — every new exam
  set was forcing a migration). Validation lives in `scrape_results` via
  `--exam {hsc,ssc}` + a 4-digit `--year` check.
- WhiteNoise serves static files from `staticfiles/`, not `static/`, and when
  `DEBUG=0` (true locally too, per `.env`) it caches at **process start** — a
  running `runserver` will keep serving pre-edit CSS/JS even after
  `collectstatic` regenerates `staticfiles/`. Restart the server after any
  static asset change, not just collectstatic.
- `publish_examset --publish` refuses if any row in that exam_type has
  `rank IS NULL` — this is an intentional data-integrity gate, not a bug.
- The GitHub Actions workflows use the Supabase **session** pooler (port 5432),
  not the transaction pooler the web app uses (6543): the scrape/rank/verify
  path does bulk reads that transaction pooling breaks. Both workflows print the
  connection host and assert `SELECT version()` says PostgreSQL before running.
- `scrape_results` refuses to write into an exam_type whose `ExamSet` is already
  published unless `--force` is passed (`--print-only` is exempt — it writes
  nothing, so it stays usable as a pre-flight check against a live set).
- `scrape_results --fixture-dir <dir>` reads `<roll>.html` off disk instead of
  issuing HTTP; everything downstream is the same code path. Fixtures in
  `.github/fixtures/` are **synthetic** — never commit a real student's result
  page, it carries the name/parents/reg_no the individual-result pages
  deliberately omit. `fixture_mode` in `scrape.yml` refuses to run with
  `mode=full`, since that would store invented students in the real exam set.
- Never hardcode `boardexamrankings.vercel.app` in templates/views — derive from
  `request`. Only allowed as the `ALLOWED_HOSTS` fallback default.
- Individual result pages: no father/mother name, no reg_no, no `Person` JSON-LD,
  and `noindex` — these are deliberate privacy exclusions, not oversights.
- `vercel.json` uses the legacy `builds` array with `@vercel/python` — this never
  runs `collectstatic` and makes Vercel ignore any Project Settings build command.
  **`staticfiles/` (the collectstatic output WhiteNoise serves from) must stay
  committed to git** — do not gitignore or untrack it, or every `/static/...`
  request 404s in production. Regenerate with `python manage.py collectstatic
  --noinput` after any static asset change and commit the result.

## Environment

Required at runtime: `DJANGO_DEBUG`, `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`,
`DJANGO_ENABLE_ADMIN`, `DATABASE_URL` (Supabase pooler, port 6543). Not auto-loaded
from `.env` — export manually for local shell/management commands.
