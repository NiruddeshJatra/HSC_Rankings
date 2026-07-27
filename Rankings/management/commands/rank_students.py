from django.core.management.base import BaseCommand, CommandError
from Rankings.models import StudentInfo

BATCH_SIZE = 1000


def normalize_group(group):
    return group.strip().upper().replace('_', ' ')


class Command(BaseCommand):
    help = 'Rank students within an exam_type/group by total marks (standard competition ranking). Safe to re-run.'

    def add_arguments(self, parser):
        parser.add_argument('--exam-type', required=True, help='e.g. SSC_2026')
        parser.add_argument('--group', required=True, help="Group name (e.g. SCIENCE), or 'all' for every group present for this exam_type")

    def handle(self, *args, **options):
        exam_type = options['exam_type']
        group_arg = options['group']

        if group_arg.lower() == 'all':
            groups = list(
                StudentInfo.objects.filter(exam_type=exam_type)
                .exclude(group__isnull=True).exclude(group='')
                .values_list('group', flat=True).distinct()
            )
            if not groups:
                raise CommandError(f'No students found for exam_type {exam_type!r}')
        else:
            groups = [normalize_group(group_arg)]

        for group in groups:
            self._rank_group(exam_type, group)

        self.stdout.write(f'\nNull-rank check for {exam_type}:')
        total_null = 0
        for group in groups:
            null_count = StudentInfo.objects.filter(exam_type=exam_type, group=group, rank__isnull=True).count()
            total_null += null_count
            self.stdout.write(f'  {group}: {null_count} rows with rank IS NULL')

        if total_null:
            raise CommandError(f'{total_null} rows still have rank IS NULL for {exam_type} after ranking.')
        self.stdout.write(self.style.SUCCESS(f'All ranked rows for {exam_type} have a non-null rank.'))

    def _rank_group(self, exam_type, group):
        students = list(
            StudentInfo.objects.filter(exam_type=exam_type, group=group, marks__isnull=False)
            .select_related('marks')
            .order_by('-marks__total_marks')
        )
        if not students:
            self.stdout.write(f'No students with marks for {exam_type} {group}')
            return

        ranks = compute_competition_ranks([s.marks.total_marks for s in students])
        for student, rank in zip(students, ranks):
            student.rank = rank

        for i in range(0, len(students), BATCH_SIZE):
            StudentInfo.objects.bulk_update(students[i:i + BATCH_SIZE], ['rank'], batch_size=BATCH_SIZE)

        self.stdout.write(self.style.SUCCESS(f'Ranked {len(students)} {exam_type} {group} students.'))


def compute_competition_ranks(scores_desc):
    """Standard competition ranking ("1224"): rank = count of strictly-higher scores + 1.
    `scores_desc` must already be sorted highest-first."""
    ranks = []
    prev_score = None
    prev_rank = 0
    for i, score in enumerate(scores_desc):
        rank = prev_rank if score == prev_score else i + 1
        ranks.append(rank)
        prev_score = score
        prev_rank = rank
    return ranks
