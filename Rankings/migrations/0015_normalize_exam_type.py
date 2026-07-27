from django.db import migrations

RENAMES = {
    'HSC': 'HSC_2024',
    'SSC': 'SSC_2025',
}


def rename_forward(apps, schema_editor):
    StudentInfo = apps.get_model('Rankings', 'StudentInfo')
    for old, new in RENAMES.items():
        StudentInfo.objects.filter(exam_type=old).update(exam_type=new)


def rename_backward(apps, schema_editor):
    StudentInfo = apps.get_model('Rankings', 'StudentInfo')
    for old, new in RENAMES.items():
        StudentInfo.objects.filter(exam_type=new).update(exam_type=old)


class Migration(migrations.Migration):

    dependencies = [
        ('Rankings', '0014_alter_studentinfo_exam_type_and_more'),
    ]

    operations = [
        migrations.RunPython(rename_forward, rename_backward),
    ]
