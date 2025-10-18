from django.core.management.base import BaseCommand
from Rankings.models import StudentInfo

class Command(BaseCommand):
    help = 'Check if all students have ranks for specific exam type and group'

    def add_arguments(self, parser):
        parser.add_argument('--exam_type', type=str, required=True, help='Exam type (HSC_2025, HSC, SSC)')
        parser.add_argument('--group', type=str, required=True, help='Student group (SCIENCE, BUSINESS STUDIES, HUMANITIES)')

    def handle(self, *args, **kwargs):
        exam_type = kwargs['exam_type']
        group = kwargs['group']
        
        # Get all students for the specified exam type and group
        students = StudentInfo.objects.filter(exam_type=exam_type, group=group)
        
        total_students = students.count()
        students_with_rank = students.filter(rank__isnull=False).count()
        students_without_rank = students.filter(rank__isnull=True).count()
        
        self.stdout.write(f"=== Rank Check for {exam_type} {group} ===")
        self.stdout.write(f"Total students: {total_students}")
        self.stdout.write(f"Students with rank: {students_with_rank}")
        self.stdout.write(f"Students without rank: {students_without_rank}")
        
        if students_without_rank > 0:
            self.stdout.write(self.style.WARNING(f"❌ {students_without_rank} students are missing ranks!"))
            
            # Show details of students without ranks
            no_rank_students = students.filter(rank__isnull=True)
            self.stdout.write("\nStudents without ranks:")
            for student in no_rank_students:
                self.stdout.write(f"  - Roll: {student.roll_no}, Name: {student.name}")
        else:
            self.stdout.write(self.style.SUCCESS("✅ All students have ranks!"))
