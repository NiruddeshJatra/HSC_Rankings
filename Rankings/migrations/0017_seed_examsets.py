from django.db import migrations


def label_for(exam_type):
    exam, _, year = exam_type.partition('_')
    return f"{exam} {year}" if year else exam_type


def seed_forward(apps, schema_editor):
    StudentInfo = apps.get_model('Rankings', 'StudentInfo')
    ExamSet = apps.get_model('Rankings', 'ExamSet')
    exam_types = StudentInfo.objects.values_list('exam_type', flat=True).distinct()
    for exam_type in exam_types:
        ExamSet.objects.get_or_create(
            exam_type=exam_type,
            defaults={
                'label': label_for(exam_type),
                'rankings_published': True,
                'scrape_complete': True,
            },
        )


def seed_backward(apps, schema_editor):
    ExamSet = apps.get_model('Rankings', 'ExamSet')
    StudentInfo = apps.get_model('Rankings', 'StudentInfo')
    exam_types = list(StudentInfo.objects.values_list('exam_type', flat=True).distinct())
    ExamSet.objects.filter(exam_type__in=exam_types).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('Rankings', '0016_examset'),
    ]

    operations = [
        migrations.RunPython(seed_forward, seed_backward),
    ]
