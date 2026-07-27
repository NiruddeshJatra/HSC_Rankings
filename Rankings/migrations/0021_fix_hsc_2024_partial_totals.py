from django.db import migrations

# roll_no -> (original stored total_marks, correct sum of all subject fields).
# These 4 HSC_2024 BUSINESS STUDIES rows had total_marks == bangla+english+ict
# only - the other subject marks (accounting/economics/management/production)
# were already stored on Marks but never folded into total_marks.
FIXES = {
    '502748': (192, 615),
    '502791': (181, 629),
    '502806': (126, 499),
    '502808': (198, 690),
}


def fix_forward(apps, schema_editor):
    StudentInfo = apps.get_model('Rankings', 'StudentInfo')
    Marks = apps.get_model('Rankings', 'Marks')
    updated = 0
    for roll_no, (_, correct_sum) in FIXES.items():
        student = StudentInfo.objects.filter(roll_no=roll_no, exam_type='HSC_2024').first()
        if not student:
            continue
        updated += Marks.objects.filter(student=student).update(total_marks=correct_sum)
    print(f'\nfix_hsc_2024_partial_totals: corrected total_marks on {updated} rows')


def fix_backward(apps, schema_editor):
    StudentInfo = apps.get_model('Rankings', 'StudentInfo')
    Marks = apps.get_model('Rankings', 'Marks')
    reverted = 0
    for roll_no, (original, _) in FIXES.items():
        student = StudentInfo.objects.filter(roll_no=roll_no, exam_type='HSC_2024').first()
        if not student:
            continue
        reverted += Marks.objects.filter(student=student).update(total_marks=original)
    print(f'\nfix_hsc_2024_partial_totals (reverse): restored {reverted} rows')


class Migration(migrations.Migration):

    dependencies = [
        ('Rankings', '0020_alter_studentinfo_exam_type'),
    ]

    operations = [
        migrations.RunPython(fix_forward, fix_backward),
    ]
