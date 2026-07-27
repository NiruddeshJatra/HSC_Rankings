from Rankings.models import ExamSet


def exam_sets(request):
  """Single source of truth for exam-set data: header nav, footer, and the
  homepage 'All rankings' index all render from this same structure."""
  sets = []
  for exam_set in ExamSet.objects.all().order_by('exam_type'):
    exam, year = exam_set.exam_type.split('_')
    sets.append({
      'exam': exam.lower(),
      'year': year,
      'label': exam_set.label,
      'published': exam_set.rankings_published,
    })
  return {
    'exam_sets': sets,
    'any_collecting': any(not s['published'] for s in sets),
  }
