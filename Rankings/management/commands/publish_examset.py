from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from Rankings.models import ExamSet, StudentInfo


class Command(BaseCommand):
    help = 'Flip the rankings_published flag for an exam set, with a safety interlock against publishing unranked data.'

    def add_arguments(self, parser):
        parser.add_argument('--exam-type', required=True, help='e.g. SSC_2026')
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument('--publish', action='store_true')
        group.add_argument('--unpublish', action='store_true')

    def handle(self, *args, **options):
        exam_type = options['exam_type']

        if options['publish']:
            total = StudentInfo.objects.filter(exam_type=exam_type).count()
            if total == 0:
                raise CommandError(f"Refusing to publish {exam_type}: no student rows found. Nothing has been scraped yet.")

            unranked = StudentInfo.objects.filter(exam_type=exam_type, rank__isnull=True).count()
            if unranked:
                raise CommandError(
                    f"Refusing to publish {exam_type}: {unranked} of {total} student row(s) have rank IS NULL. "
                    f"Run rank_students for this exam_type first."
                )

            exam_set, _ = ExamSet.objects.get_or_create(
                exam_type=exam_type,
                defaults={'label': exam_type.replace('_', ' ')},
            )
            exam_set.rankings_published = True
            exam_set.last_ranked_at = timezone.now()
            exam_set.save()
            self.stdout.write(self.style.SUCCESS(f"Published rankings for {exam_type}."))
        else:
            exam_set, _ = ExamSet.objects.get_or_create(
                exam_type=exam_type,
                defaults={'label': exam_type.replace('_', ' ')},
            )
            exam_set.rankings_published = False
            exam_set.save()
            self.stdout.write(self.style.SUCCESS(f"Unpublished rankings for {exam_type}."))
