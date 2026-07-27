from django.db import migrations


def normalize_forward(apps, schema_editor):
    StudentInfo = apps.get_model('Rankings', 'StudentInfo')
    updated = StudentInfo.objects.filter(
        exam_type='SSC_2025', result__in=[None, ''],
    ).exclude(gpa__in=[None, '']).update(result='PASS')
    print(f'\nnormalize_ssc_2025_result: set result=PASS on {updated} rows')


def normalize_backward(apps, schema_editor):
    StudentInfo = apps.get_model('Rankings', 'StudentInfo')
    reverted = StudentInfo.objects.filter(exam_type='SSC_2025', result='PASS').update(result='')
    print(f'\nnormalize_ssc_2025_result (reverse): cleared result on {reverted} rows')


class Migration(migrations.Migration):

    dependencies = [
        ('Rankings', '0018_alter_studentinfo_exam_type'),
    ]

    operations = [
        migrations.RunPython(normalize_forward, normalize_backward),
    ]
