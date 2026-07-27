import random
from collections import Counter

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Avg, Max, Min

from Rankings.models import Marks, StudentInfo

SUBJECT_FIELDS = [
  'bangla', 'english', 'math', 'physics', 'chemistry', 'biology',
  'higher_math', 'ict', 'islam_moral', 'hindu_moral', 'buddha_moral',
  'christian_moral', 'bangladesh_world', 'agriculture', 'home_science',
  'finance_banking', 'accounting', 'business_ent', 'general_science',
  'music', 'geography', 'civics', 'economics', 'history_bd', 'statistics',
  'management', 'finance', 'production', 'logic', 'history',
  'islamic_history', 'social_work', 'sociology', 'physical_education',
  'career_education',
]


class Command(BaseCommand):
  help = 'Audit data integrity for a given exam_type (report only, no writes)'

  def add_arguments(self, parser):
    parser.add_argument('--exam-type', type=str, required=True)

  def handle(self, *args, **options):
    exam_type = options['exam_type']
    students = StudentInfo.objects.filter(exam_type=exam_type)
    if not students.exists():
      raise CommandError(f'No StudentInfo rows found for exam_type={exam_type}')

    self.stdout.write(self.style.MIGRATE_HEADING(f'=== AUDIT: {exam_type} ==='))
    self.section_result_field(students)
    self.section_total_marks(students)
    self.section_internal_consistency(students)
    self.section_cross_check(students, exam_type)

  # 1. RESULT FIELD
  def section_result_field(self, students):
    self.stdout.write('\n--- 1. RESULT FIELD ---')

    total = students.count()
    null_or_blank = 0
    result_values = Counter()
    for result in students.values_list('result', flat=True):
      if result is None or result.strip() == '':
        null_or_blank += 1
      result_values[result] += 1
    self.stdout.write(f'Total rows: {total}')
    self.stdout.write(f'result null/empty/whitespace: {null_or_blank}')
    self.stdout.write('Distinct result values:')
    for value, count in result_values.most_common():
      self.stdout.write(f'  {value!r}: {count}')

    gpa_null = 0
    gpa_out_of_range = []
    for pk, gpa in students.values_list('pk', 'gpa'):
      if gpa is None or gpa.strip() == '':
        gpa_null += 1
        continue
      try:
        gpa_val = float(gpa)
      except ValueError:
        gpa_out_of_range.append((pk, gpa))
        continue
      if gpa_val < 0.0 or gpa_val > 5.0:
        gpa_out_of_range.append((pk, gpa))
    self.stdout.write(f'gpa null/empty: {gpa_null}')
    self.stdout.write(f'gpa outside 0.0-5.0 (or non-numeric): {len(gpa_out_of_range)}')
    for pk, gpa in gpa_out_of_range[:20]:
      self.stdout.write(f'  student_id={pk} gpa={gpa!r}')

  # 2. TOTAL MARKS
  def section_total_marks(self, students):
    self.stdout.write('\n--- 2. TOTAL MARKS ---')
    marks_qs = Marks.objects.filter(student__in=students)

    agg = marks_qs.aggregate(min_tm=Min('total_marks'), max_tm=Max('total_marks'), avg_tm=Avg('total_marks'))
    self.stdout.write(f"min total_marks: {agg['min_tm']}")
    self.stdout.write(f"max total_marks: {agg['max_tm']}")
    self.stdout.write(f"avg total_marks: {agg['avg_tm']}")

    top10 = marks_qs.select_related('student').order_by('-total_marks')[:10]
    self.stdout.write('Top 10 total_marks:')
    for m in top10:
      self.stdout.write(
        f'  roll={m.student.roll_no} name={m.student.name} group={m.student.group} total_marks={m.total_marks}'
      )

    top20 = marks_qs.order_by('-total_marks')[:20]
    top20_totals = Counter(m.total_marks for m in top20)
    self.stdout.write('Row count per distinct total_marks value (top 20 totals):')
    for value, count in sorted(top20_totals.items(), key=lambda x: -x[0]):
      self.stdout.write(f'  total_marks={value}: {count} rows')

    self.stdout.write('Per-group populated-subject-field census:')
    groups = students.values_list('group', flat=True).distinct()
    for group in groups:
      group_marks = marks_qs.filter(student__group=group)
      group_count = group_marks.count()
      self.stdout.write(f'  group={group!r} (n={group_count}):')
      for field in SUBJECT_FIELDS:
        populated = group_marks.filter(**{f'{field}__isnull': False}).exclude(**{field: 0}).count()
        if populated > 0:
          self.stdout.write(f'    {field}: {populated} students non-null/non-zero')

  # 3. INTERNAL CONSISTENCY
  def section_internal_consistency(self, students):
    self.stdout.write('\n--- 3. INTERNAL CONSISTENCY ---')
    marks_qs = Marks.objects.filter(student__in=students).select_related('student')

    disagreements = []
    over_100_count = 0
    negative_count = 0

    for m in marks_qs:
      subject_sum = 0
      has_over_100 = False
      has_negative = False
      for field in SUBJECT_FIELDS:
        value = getattr(m, field)
        if value is None:
          continue
        subject_sum += value
        if value > 100:
          has_over_100 = True
        if value < 0:
          has_negative = True
      if has_over_100:
        over_100_count += 1
      if has_negative:
        negative_count += 1
      diff = m.total_marks - subject_sum
      if diff != 0:
        disagreements.append((m, subject_sum, diff))

    self.stdout.write(f'Rows compared: {marks_qs.count()}')
    self.stdout.write(f'Rows where total_marks != sum(subject fields): {len(disagreements)}')

    diff_sizes = Counter(abs(diff) for _, _, diff in disagreements)
    self.stdout.write('Disagreement size distribution (abs(diff): count):')
    for size, count in sorted(diff_sizes.items()):
      self.stdout.write(f'  {size}: {count}')

    self.stdout.write(f'Rows with any individual subject mark > 100: {over_100_count}')
    self.stdout.write(f'Rows with any individual subject mark < 0: {negative_count}')

    self.stdout.write('10 example disagreements (full per-subject breakdown):')
    for m, subject_sum, diff in disagreements[:10]:
      self.stdout.write(
        f'  roll={m.student.roll_no} name={m.student.name} group={m.student.group} '
        f'stored_total_marks={m.total_marks} computed_sum={subject_sum} diff={diff}'
      )
      for field in SUBJECT_FIELDS:
        value = getattr(m, field)
        if value is not None:
          self.stdout.write(f'    {field}: {value}')

  # 4. CROSS-CHECK
  def section_cross_check(self, students, exam_type):
    self.stdout.write('\n--- 4. CROSS-CHECK (random sample) ---')
    ids = list(students.values_list('pk', flat=True))
    sample_ids = random.sample(ids, min(5, len(ids)))
    for pk in sample_ids:
      student = StudentInfo.objects.get(pk=pk)
      self.stdout.write(f'\nroll_no={student.roll_no}')
      self.stdout.write(f'  name={student.name}')
      self.stdout.write(f'  board={student.board}')
      self.stdout.write(f'  father_name={student.father_name}')
      self.stdout.write(f'  mother_name={student.mother_name}')
      self.stdout.write(f'  group={student.group}')
      self.stdout.write(f'  session={student.session}')
      self.stdout.write(f'  reg_no={student.reg_no}')
      self.stdout.write(f'  type_of_result={student.type_of_result}')
      self.stdout.write(f'  institute={student.institute}')
      self.stdout.write(f'  result={student.result}')
      self.stdout.write(f'  gpa={student.gpa}')
      self.stdout.write(f'  rank={student.rank}')
      self.stdout.write(f'  exam_type={student.exam_type}')
      try:
        marks = student.marks
        self.stdout.write(f'  total_marks={marks.total_marks}')
        for field in SUBJECT_FIELDS:
          value = getattr(marks, field)
          if value is not None:
            self.stdout.write(f'  {field}={value}')
      except Marks.DoesNotExist:
        self.stdout.write('  Marks: MISSING (no Marks row for this student)')
