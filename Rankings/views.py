import re
from django.http import Http404, HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from .models import StudentInfo, Marks, ExamSet
from django.core.paginator import Paginator

VALID_EXAMS = {'hsc', 'ssc'}
YEAR_RE = re.compile(r'^\d{4}$')


def _validate_exam_year(exam, year):
    exam = exam.lower()
    if exam not in VALID_EXAMS or not YEAR_RE.match(year):
        raise Http404('Unknown exam or year')
    return exam, year


def home(request):
    return render(request, 'home.html')

def methodology(request):
    return render(request, 'methodology.html')

def robots_txt(request):
    scheme = request.scheme
    host = request.get_host()
    content = (
        "User-agent: *\n"
        "Disallow: /admin/\n"
        f"Sitemap: {scheme}://{host}/sitemap.xml\n"
    )
    return HttpResponse(content, content_type="text/plain")

def results(request, exam, year, group):
    exam, year = _validate_exam_year(exam, year)
    group = group.lower()
    if request.GET.get('roll_no'):
        roll_no = request.GET['roll_no']
        return redirect(reverse('rankings:individual', kwargs={'exam': exam, 'year': year, 'roll_no': roll_no}))

    # Map group to DB value if needed (e.g., 'science' -> 'SCIENCE')
    group_db = group.upper()
    if group_db == 'BUSINESS_STUDIES':
        group_db = 'BUSINESS STUDIES'

    exam_type_db = f"{exam.upper()}_{year}"

    exam_set = ExamSet.objects.filter(exam_type=exam_type_db).first()
    rankings_published = bool(exam_set and exam_set.rankings_published)

    if not rankings_published:
        context = {
            'group': group_db,
            'exam': exam,
            'year': year,
            'exam_type': exam_type_db,
            'rankings_published': False,
        }
        return render(request, 'results.html', context)

    students = StudentInfo.objects.filter(exam_type=exam_type_db, group=group_db).order_by('rank').select_related('marks')
    paginator = Paginator(students, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    page_range = paginator.get_elided_page_range(number=page_obj.number, on_each_side=2, on_ends=1)

    context = {
        'students': page_obj,
        'group': group_db,
        'exam': exam,
        'year': year,
        'exam_type': exam_type_db,
        'page_range': page_range,
        'rankings_published': True,
    }
    return render(request, 'results.html', context)

def individual_result(request, exam, year, roll_no):
    exam, year = _validate_exam_year(exam, year)
    exam_type_db = f"{exam.upper()}_{year}"

    student = get_object_or_404(StudentInfo, roll_no=roll_no, exam_type=exam_type_db)
    marks = get_object_or_404(Marks, student=student)

    # Subject name mapping (unchanged)
    SUBJECT_LABELS_MAP = {
        'bangla': 'Bangla',
        'english': 'English',
        # ... (keep all existing subject mappings)
        'islamic_history': 'Islamic History',
    }
    subject_fields = []
    for field in Marks._meta.get_fields():
        if (
            field.name not in ['id', 'student', 'total_marks']
            and hasattr(field, 'get_internal_type')
            and field.get_internal_type() in ['IntegerField', 'PositiveIntegerField']
        ):
            label = SUBJECT_LABELS_MAP.get(field.name)
            if not label:
                label = field.name.replace('_', ' ').title()
            subject_fields.append((field.name, label))

    context = {
        'student': student,
        'marks': marks,
        'exam': exam,
        'year': year,
        'exam_type': exam_type_db,
        'subject_fields': subject_fields,
    }
    return render(request, 'individual_result.html', context)
