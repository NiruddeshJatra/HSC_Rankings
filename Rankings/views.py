from django.shortcuts import render, get_object_or_404
from .models import StudentInfo, Marks
from django.core.paginator import Paginator

def home(request):
    return render(request, 'home.html')

def results(request, exam_type, group):
    exam_type = exam_type.lower()
    group = group.lower()
    if request.GET.get('roll_no'):
        roll_no = request.GET['roll_no']
        from django.urls import reverse
        from django.shortcuts import redirect
        return redirect(reverse('rankings:individual', kwargs={'exam_type': exam_type, 'roll_no': roll_no}))
    # Map group to DB value if needed (e.g., 'science' -> 'SCIENCE')
    group_db = group.upper()
    if group_db == 'BUSINESS_STUDIES':
        group_db = 'BUSINESS STUDIES'
    students = StudentInfo.objects.filter(exam_type=exam_type.upper(), group=group_db).order_by('rank').select_related('marks')
    paginator = Paginator(students, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    page_range = paginator.get_elided_page_range(number=page_obj.number, on_each_side=2, on_ends=1)
    context = {
        'students': page_obj,
        'group': group_db,
        'exam_type': exam_type,  # Keep lowercase for URLs
        'page_range': page_range,
    }
    return render(request, 'results.html', context)

def individual_result(request, exam_type, roll_no):
    exam_type = exam_type.lower()
    student = get_object_or_404(StudentInfo, roll_no=roll_no, exam_type=exam_type.upper())
    marks = get_object_or_404(Marks, student=student)
    context = {
        'student': student,
        'marks': marks,
        'exam_type': exam_type,  # Keep lowercase for URLs
    }
    return render(request, 'individual_result.html', context)

