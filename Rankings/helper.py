from .models import StudentInfo, Marks

# Query all StudentInfo objects that do not have a related Marks object
students_without_marks = StudentInfo.objects.filter(marks__isnull=True)

# List the roll numbers of students without Marks
missing_marks_roll_numbers = students_without_marks.values_list('roll_no', flat=True)

# Print or return the roll numbers
print(list(missing_marks_roll_numbers))
