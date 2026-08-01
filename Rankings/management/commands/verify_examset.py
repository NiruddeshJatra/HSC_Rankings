from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count, IntegerField, Q

from Rankings.models import Marks, StudentInfo

# Integer columns on Marks that are NOT a subject's mark. Every other integer
# column is treated as one. Discovery is deliberate: a subject is added to Marks
# most years, and a hand-maintained list would silently go stale and quietly
# shrink this check. Anything added to Marks that is an integer but not a
# subject mark (a flag, a counter) must be listed here — SubjectFieldsTests
# fails if the derived list changes, so it cannot drift unnoticed.
NON_SUBJECT_INT_FIELDS = {'total_marks'}

SUBJECT_FIELDS = [
    f.name for f in Marks._meta.concrete_fields
    if isinstance(f, IntegerField)
    and not f.primary_key
    and f.name not in NON_SUBJECT_INT_FIELDS
]


def nonzero_subject_marks_q():
    """Matches a StudentInfo whose Marks row has any subject column above zero."""
    q = Q()
    for field_name in SUBJECT_FIELDS:
        q |= Q(**{f'marks__{field_name}__gt': 0})
    return q

GPA_BANDS = [
    (5.0, 5.0, '5.00'),
    (4.0, 4.99, '4.00-4.99'),
    (3.0, 3.99, '3.00-3.99'),
    (2.0, 2.99, '2.00-2.99'),
    (1.0, 1.99, '1.00-1.99'),
    (0.01, 0.99, '0.01-0.99'),
    (0.0, 0.0, '0.00'),
]


class Command(BaseCommand):
    help = 'Print a post-scrape sanity report for an exam_type, and fail (exit 1) if the data is not safe to publish.'

    def add_arguments(self, parser):
        parser.add_argument('--exam-type', required=True, help='e.g. SSC_2026')

    def handle(self, *args, **options):
        exam_type = options['exam_type']
        qs = StudentInfo.objects.filter(exam_type=exam_type)
        total = qs.count()

        if total == 0:
            raise CommandError(f"No rows found for exam_type {exam_type!r}")

        problems = []

        null_rank = qs.filter(rank__isnull=True).count()
        zero_marks = qs.filter(marks__total_marks=0).count()
        blank_result = qs.filter(Q(result__isnull=True) | Q(result='')).count()

        self.stdout.write(f"=== Sanity report: {exam_type} ===")
        self.stdout.write(f"Total student rows: {total}")
        self.stdout.write(f"Rows with rank IS NULL: {null_rank}")
        self.stdout.write(f"Rows with total_marks == 0: {zero_marks}")
        self.stdout.write(f"Rows with result IS NULL or blank: {blank_result}")

        # The HSC_2024 defect: total_marks left at 0 while the subject columns
        # actually hold marks. Such rows rank last and read as a zero score.
        broken_totals = qs.filter(marks__total_marks=0).filter(nonzero_subject_marks_q())
        broken_total_count = broken_totals.count()
        self.stdout.write(f"Rows with total_marks == 0 but non-zero subject marks: {broken_total_count}")

        if null_rank:
            problems.append(f"{null_rank} rows with rank IS NULL")
        if blank_result:
            problems.append(f"{blank_result} rows with result IS NULL or blank")
        if broken_total_count:
            problems.append(f"{broken_total_count} rows with total_marks == 0 but non-zero subject marks")
            for s in broken_totals.only('roll_no')[:10]:
                self.stdout.write(f"  roll {s.roll_no}")

        # GPA distribution
        self.stdout.write("\nGPA distribution:")
        gpas = []
        out_of_range = 0
        for row in qs.values_list('gpa', flat=True):
            try:
                gpa = float(row) if row not in (None, '') else None
            except ValueError:
                gpa = None
            if gpa is None:
                continue
            gpas.append(gpa)
            if not (0.0 <= gpa <= 5.0):
                out_of_range += 1

        for low, high, label in GPA_BANDS:
            count = sum(1 for g in gpas if low <= g <= high)
            self.stdout.write(f"  {label}: {count}")
        self.stdout.write(f"  Outside 0.0-5.0 (should be zero): {out_of_range}")
        if out_of_range:
            problems.append(f"{out_of_range} rows with GPA outside 0.0-5.0")

        # Institutes
        institute_counts = (
            qs.exclude(institute__isnull=True).exclude(institute='')
            .values('institute').annotate(c=Count('id')).order_by('-c')
        )
        distinct_institutes = institute_counts.count()
        self.stdout.write(f"\nDistinct institutes: {distinct_institutes}")
        self.stdout.write("Top 5 institutes by student count:")
        for row in institute_counts[:5]:
            self.stdout.write(f"  {row['institute']}: {row['c']}")

        # Duplicate roll numbers
        dupes = (
            qs.values('roll_no').annotate(c=Count('id')).filter(c__gt=1).order_by('-c')
        )
        dupe_count = dupes.count()
        self.stdout.write(f"\nDuplicate roll_no values: {dupe_count}")
        if dupe_count:
            problems.append(f"{dupe_count} duplicate roll_no values")
            for row in dupes[:10]:
                self.stdout.write(f"  {row['roll_no']}: {row['c']} rows")

        # Top 10 by total_marks
        self.stdout.write("\nTop 10 by total_marks:")
        top10 = qs.select_related('marks').order_by('-marks__total_marks')[:10]
        for s in top10:
            marks = getattr(s, 'marks', None)
            total_marks = marks.total_marks if marks else 'N/A'
            self.stdout.write(f"  Roll {s.roll_no}  {s.name}  {s.institute}  GPA {s.gpa}  Total {total_marks}")

        # Roll number coverage
        roll_ints = []
        for roll_no in qs.values_list('roll_no', flat=True).distinct():
            try:
                roll_ints.append(int(roll_no))
            except (TypeError, ValueError):
                continue
        if roll_ints:
            lowest, highest = min(roll_ints), max(roll_ints)
            expected = highest - lowest + 1
            seen = len(set(roll_ints))
            missing = expected - seen
            self.stdout.write(f"\nRoll number coverage: lowest={lowest} highest={highest}")
            self.stdout.write(f"Expected in range: {expected}, seen: {seen}, missing: {missing}")
        else:
            self.stdout.write("\nRoll number coverage: no numeric roll numbers found")

        self.stdout.write("")
        if problems:
            for p in problems:
                self.stdout.write(self.style.ERROR(f"FAIL: {p}"))
            raise CommandError(f"{exam_type} failed sanity checks - do not publish.")

        self.stdout.write(self.style.SUCCESS(f"{exam_type} passed all sanity checks."))
