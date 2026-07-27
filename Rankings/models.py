from django.db import models


class StudentInfo(models.Model):
  roll_no = models.CharField(max_length=20)
  name = models.CharField(max_length=100, null=True, blank=True)
  board = models.CharField(max_length=100, null=True, blank=True)
  father_name = models.CharField(max_length=100, null=True, blank=True)
  group = models.CharField(max_length=100, null=True, blank=True)
  mother_name = models.CharField(max_length=100, null=True, blank=True)
  session = models.CharField(max_length=100, null=True, blank=True)
  reg_no = models.CharField(max_length=100, null=True, blank=True)
  type_of_result = models.CharField(max_length=100, null=True, blank=True)
  institute = models.CharField(max_length=100, null=True, blank=True)
  result = models.CharField(max_length=100, null=True, blank=True)
  gpa = models.CharField(max_length=100, null=True, blank=True)
  rank = models.IntegerField(null=True, blank=True)
  EXAM_TYPE_CHOICES = [
    ('HSC_2024', 'HSC 2024'),
    ('SSC_2025', 'SSC 2025'),
    ('HSC_2025', 'HSC 2025'),
    ('SSC_2026', 'SSC 2026'),
  ]
  exam_type = models.CharField(max_length=10, choices=EXAM_TYPE_CHOICES, default='HSC_2024')

  class Meta:
    unique_together = ('roll_no', 'exam_type')
    indexes = [
      models.Index(fields=['exam_type', 'group', 'rank']),
      models.Index(fields=['institute']),
    ]


class ExamSet(models.Model):
  exam_type = models.CharField(max_length=10, unique=True)
  label = models.CharField(max_length=50)
  rankings_published = models.BooleanField(default=False)
  scrape_complete = models.BooleanField(default=False)
  last_ranked_at = models.DateTimeField(null=True, blank=True)
  notes = models.CharField(max_length=255, blank=True)

  def __str__(self):
    return self.label


class Marks(models.Model):
  student = models.OneToOneField(StudentInfo, on_delete=models.CASCADE)
  # HSC/SSC Common Subjects (NO CHANGES - keep existing fields)
  bangla = models.IntegerField(null=True, blank=True, default=0)
  english = models.IntegerField(null=True, blank=True, default=0)
  math = models.IntegerField(null=True, blank=True, default=0)
  physics = models.IntegerField(null=True, blank=True, default=0)
  chemistry = models.IntegerField(null=True, blank=True, default=0)
  biology = models.IntegerField(null=True, blank=True, default=0)
  higher_math = models.IntegerField(null=True, blank=True, default=0)
  ict = models.IntegerField(null=True, blank=True, default=0)
  islam_moral = models.IntegerField(null=True, blank=True, default=0)
  hindu_moral = models.IntegerField(null=True, blank=True, default=0)
  buddha_moral = models.IntegerField(null=True, blank=True, default=0)
  christian_moral = models.IntegerField(null=True, blank=True, default=0)
  bangladesh_world = models.IntegerField(null=True, blank=True, default=0)
  agriculture = models.IntegerField(null=True, blank=True, default=0)
  home_science = models.IntegerField(null=True, blank=True, default=0)
  finance_banking = models.IntegerField(null=True, blank=True, default=0)
  accounting = models.IntegerField(null=True, blank=True, default=0)
  business_ent = models.IntegerField(null=True, blank=True, default=0)
  general_science = models.IntegerField(null=True, blank=True, default=0)
  music = models.IntegerField(null=True, blank=True, default=0)
  geography = models.IntegerField(null=True, blank=True, default=0)
  civics = models.IntegerField(null=True, blank=True, default=0)
  economics = models.IntegerField(null=True, blank=True, default=0)
  history_bd = models.IntegerField(null=True, blank=True, default=0)
  statistics = models.IntegerField(null=True, blank=True, default=0)
  management = models.IntegerField(null=True, blank=True, default=0)
  finance = models.IntegerField(null=True, blank=True, default=0)
  production = models.IntegerField(null=True, blank=True, default=0)
  logic = models.IntegerField(null=True, blank=True, default=0)
  history = models.IntegerField(null=True, blank=True, default=0)
  islamic_history = models.IntegerField(null=True, blank=True, default=0)
  social_work = models.IntegerField(null=True, blank=True, default=0)
  sociology = models.IntegerField(null=True, blank=True, default=0)
  total_marks = models.IntegerField(default=0)
  physical_education = models.IntegerField(default=0, verbose_name='Physical Education, Health and Sports')
  career_education = models.IntegerField(default=0, verbose_name='Career Education')

  class Meta:
    indexes = [
      models.Index(fields=['total_marks']),
    ]
