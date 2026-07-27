from django.db import migrations


def normalize_forward(apps, schema_editor):
    StudentInfo = apps.get_model('Rankings', 'StudentInfo')
    updated = StudentInfo.objects.filter(
        exam_type='SSC_2025', result__in=[None, ''],
    ).exclude(gpa__in=[None, '']).update(result='PASS')
    print(f'\nnormalize_ssc_2025_result: set result=PASS on {updated} rows')


class Migration(migrations.Migration):

    dependencies = [
        ('Rankings', '0018_alter_studentinfo_exam_type'),
    ]

    operations = [
        # Irreversible: once applied, a 'PASS' row is indistinguishable from a
        # row that was always 'PASS' (e.g. from a later re-scrape). A reverse
        # that blindly clears every SSC_2025 'PASS' would wipe legitimate rows
        # that were never blank, so there is no safe RunPython reverse here.
        migrations.RunPython(normalize_forward, migrations.RunPython.noop),
    ]
