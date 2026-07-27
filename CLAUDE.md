# HSC_Rankings

Django 5.1 site scraping Chittagong board (BISE-CTG) SSC/HSC exam results and
publishing independently-computed merit rankings. Deployed on Vercel.

## File Structure

```
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
  templatetags/marks_extras.py  # stagger_class/subject_stagger_class/bar_class —
                                 # CSS-class helpers so templates need no style=""
  management/commands/
    scrape_results.py       # pulls results from board portal
    transfer_to_postgres.py # legacy sqlite -> Postgres migration
    rank_students.py        # computes rank per exam_type/group
    publish_examset.py      # flips ExamSet.rankings_published (refuses if any rank IS NULL)
    verify_examset.py
    check_ranks.py
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
- Subject max-marks (`SUBJECT_MAX_MARKS` in `views.py`) are public BD board
  syllabus constants (e.g. Bangla/English=200, ICT=50, else 100) used only to
  size the subject-marks progress bars — not derived from any student's data.
- `publish_examset --publish` refuses if any row in that exam_type has
  `rank IS NULL` — this is an intentional data-integrity gate, not a bug.
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
