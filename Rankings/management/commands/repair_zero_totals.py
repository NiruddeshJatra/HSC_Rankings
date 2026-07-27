from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from Rankings.models import Marks

SUBJECT_FIELDS = [
    f.name for f in Marks._meta.get_fields()
    if f.name not in ('id', 'student', 'total_marks')
    and hasattr(f, 'get_internal_type')
    and f.get_internal_type() in ('IntegerField', 'PositiveIntegerField')
]


class Command(BaseCommand):
    help = (
        'Repair rows where total_marks=0 but subject fields sum to a real value. '
        'Dry-run by default; pass --apply to write.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--exam-type', required=True, help='e.g. HSC_2024')
        parser.add_argument('--dry-run', action='store_true', help='List affected rows without writing (default)')
        parser.add_argument('--apply', action='store_true', help='Write the repaired total_marks')

    def handle(self, *args, **options):
        exam_type = options['exam_type']
        apply_changes = options['apply']

        qs = Marks.objects.filter(student__exam_type=exam_type, total_marks=0).select_related('student')
        if not qs.exists() and not Marks.objects.filter(student__exam_type=exam_type).exists():
            raise CommandError(f'No rows found for exam_type {exam_type!r}')

        affected = []
        for m in qs:
            recomputed = sum(getattr(m, f) or 0 for f in SUBJECT_FIELDS)
            if recomputed == 0:
                continue  # refuses to touch rows that are genuinely zero
            affected.append((m, recomputed))

        mode = 'APPLY' if apply_changes else 'DRY RUN'
        self.stdout.write(f'=== repair_zero_totals ({mode}): {exam_type} ===')
        self.stdout.write(f'{len(affected)} rows affected')
        for m, recomputed in affected:
            self.stdout.write(
                f'  roll={m.student.roll_no} name={m.student.name} group={m.student.group} '
                f'current_total_marks={m.total_marks} recomputed_sum={recomputed}'
            )

        if not apply_changes:
            self.stdout.write(self.style.WARNING('Dry run - no changes written. Pass --apply to write.'))
            return

        with transaction.atomic():
            for m, recomputed in affected:
                m.total_marks = recomputed
                m.save(update_fields=['total_marks'])

        self.stdout.write(self.style.SUCCESS(f'Updated total_marks on {len(affected)} rows for {exam_type}.'))
