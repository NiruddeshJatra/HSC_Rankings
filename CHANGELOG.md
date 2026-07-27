# Changelog

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
