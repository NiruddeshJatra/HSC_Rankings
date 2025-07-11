from django.core.management.base import BaseCommand
from Rankings.models import StudentInfo

class Command(BaseCommand):
    help = 'Rank SSC Science students based on total marks'

    def handle(self, *args, **kwargs):
        group = 'SCIENCE'
        exam_type = 'SSC'
        students = StudentInfo.objects.filter(group=group, exam_type=exam_type).order_by('-marks__total_marks')
        rank = 1
        for i, student in enumerate(students):
            try:
                if i > 0 and student.marks.total_marks == students[i-1].marks.total_marks:
                    student.rank = students[i-1].rank  # Same rank if marks are the same
                else:
                    student.rank = rank
                student.save()
                rank += 1
                print(f'Ranked {student.roll_no} as rank {student.rank}')
            except Exception as e:
                print(f'{student.roll_no} has no marks: {e}')
        self.stdout.write(self.style.SUCCESS(f'Successfully ranked {rank-1} SSC {group} students.'))