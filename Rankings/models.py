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
  # Add exam_type to distinguish between HSC and SSC
  EXAM_TYPE_CHOICES = [
    ('HSC', 'HSC'),
    ('SSC', 'SSC'),
  ]
  exam_type = models.CharField(max_length=10, choices=EXAM_TYPE_CHOICES, default='HSC')

  class Meta:
    unique_together = ('roll_no', 'exam_type')


class Marks(models.Model):
  student = models.OneToOneField(StudentInfo, on_delete=models.CASCADE)
  # HSC/SSC Common Subjects
  bangla = models.IntegerField(null=True, blank=True, default=0)  # 101
  english = models.IntegerField(null=True, blank=True, default=0)  # 107
  math = models.IntegerField(null=True, blank=True, default=0)  # 109 (SSC)
  physics = models.IntegerField(null=True, blank=True, default=0)  # 136
  chemistry = models.IntegerField(null=True, blank=True, default=0)  # 137
  biology = models.IntegerField(null=True, blank=True, default=0)  # 138
  higher_math = models.IntegerField(null=True, blank=True, default=0)  # 126 (SSC)
  ict = models.IntegerField(null=True, blank=True, default=0)  # 154 (SSC: Information & Technology)
  islam_moral = models.IntegerField(null=True, blank=True, default=0)  # 111 (Islam & Moral Education)
  hindu_moral = models.IntegerField(null=True, blank=True, default=0)  # 112 (Hindu Religion & Moral Education)
  buddha_moral = models.IntegerField(null=True, blank=True, default=0)  # 113 (Buddha Religion & Moral Education)
  christian_moral = models.IntegerField(null=True, blank=True, default=0)  # 114 (Christian Religion & Moral Education)
  bangladesh_world = models.IntegerField(null=True, blank=True, default=0)  # 150 (Bangladesh & World)
  agriculture = models.IntegerField(null=True, blank=True, default=0)  # 134 (Agriculture Studies)
  home_science = models.IntegerField(null=True, blank=True, default=0)  # 151
  finance_banking = models.IntegerField(null=True, blank=True, default=0)  # 152
  accounting = models.IntegerField(null=True, blank=True, default=0)  # 146
  business_ent = models.IntegerField(null=True, blank=True, default=0)  # 143 (Business Ent.)
  general_science = models.IntegerField(null=True, blank=True, default=0)  # 127
  music = models.IntegerField(null=True, blank=True, default=0)  # 149
  geography = models.IntegerField(null=True, blank=True, default=0)  # 110
  civics = models.IntegerField(null=True, blank=True, default=0)  # 140 (Civic & Citizenship)
  economics = models.IntegerField(null=True, blank=True, default=0)  # 141
  history_bd = models.IntegerField(null=True, blank=True, default=0)  # 153 (History of Bangladesh)
  # Existing HSC fields (keep for compatibility)
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
    