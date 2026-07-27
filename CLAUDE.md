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
  context_processors.py   # exam_sets — feeds footer's published-exam-set list
  subject_maps.py         # subject label/code mappings
  templatetags/marks_extras.py
  management/commands/
    scrape_results.py       # pulls results from board portal
    transfer_to_postgres.py # legacy sqlite -> Postgres migration
    rank_students.py        # computes rank per exam_type/group
    publish_examset.py      # flips ExamSet.rankings_published (refuses if any rank IS NULL)
    verify_examset.py
    check_ranks.py
  templates/               # app-local templates (home, results, individual_result)
templates/
  base.html              # site shell: nav, footer, meta/JSON-LD, exam-set list (dynamic)
  methodology.html
db_legacy.sqlite3        # gitignored backup only — never the active DB, never commit
```

## Key Conventions

- `DATABASES['default']` uses Supabase's **transaction pooler (port 6543)**.
  `DISABLE_SERVER_SIDE_CURSORS = True` in settings.py is required for this —
  don't remove it, `QuerySet.iterator()` (scraper/transfer paths) breaks without it.
- `exam_type` is `{EXAM}_{YEAR}` (e.g. `SSC_2025`) — split on `_` for exam/year,
  never hardcode the mapping elsewhere.
- Footer's exam-set list is driven by `Rankings.context_processors.exam_sets`
  (`ExamSet.objects.filter(rankings_published=True)`) — don't hardcode exam sets
  in templates.
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
