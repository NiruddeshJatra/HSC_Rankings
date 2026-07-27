from Rankings.models import ExamSet


def exam_sets(request):
  sets = []
  for exam_set in ExamSet.objects.filter(rankings_published=True).order_by('exam_type'):
    exam, year = exam_set.exam_type.split('_')
    sets.append({'exam': exam.lower(), 'year': year, 'label': exam_set.label})
  return {'footer_exam_sets': sets}
