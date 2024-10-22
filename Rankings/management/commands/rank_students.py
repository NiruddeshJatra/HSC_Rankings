from django.core.management.base import BaseCommand
from Rankings.models import StudentInfo

class Command(BaseCommand):
  help = 'Rank students based on total marks'

  def handle(self, *args, **kwargs):
    for group in ['HUMANITIES']:
      students = StudentInfo.objects.filter(group=group).order_by('-marks__total_marks')
      rank = 1
      for i, student in enumerate(students):
        try:
          if i > 0 and student.marks.total_marks == students[i-1].marks.total_marks:
            student.rank = students[i-1].rank  # Same rank if marks are the same
          else:
            student.rank = rank
          student.save()
          rank += 1
        except Exception:
          print(f'{students.roll_no} has no marks')
    self.stdout.write(self.style.SUCCESS('Successfully ranked students.'))
