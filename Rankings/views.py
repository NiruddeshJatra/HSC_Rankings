from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from .models import StudentInfo, Marks

def results(request, group="SCIENCE"):
  if roll_no := request.GET.get('roll_no'):
    return redirect('rankings:individual', roll_no=roll_no)

  students = StudentInfo.objects.filter(group=group).order_by('rank')

  # Pagination
  paginator = Paginator(students, 50)
  page_number = request.GET.get('page')
  page_obj = paginator.get_page(page_number)

  current_page = page_obj.number
  total_pages = paginator.num_pages

  # Logic for displaying more flexible pagination (1,2,3...50,51 etc.)
  if current_page <= 3:
    page_range = range(1, min(total_pages, 6))
  elif current_page >= total_pages - 2:
    page_range = range(max(1, total_pages - 2), total_pages + 1)
  else:
    page_range = range(current_page - 2, current_page + 3)

  return render(request, 'results.html', {'students': page_obj, 'group': group, 'page_range': page_range})


def individual_result(request, roll_no):
  student = get_object_or_404(StudentInfo, roll_no=roll_no)
  marks = get_object_or_404(Marks, student=student)

  return render(request, 'individual_result.html', {'student': student, 'marks': marks})

