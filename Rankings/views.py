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
        'last_ranked_at': exam_set.last_ranked_at,
    }
    return render(request, 'results.html', context)

def individual_result(request, exam, year, roll_no):
    exam, year = _validate_exam_year(exam, year)
    exam_type_db = f"{exam.upper()}_{year}"

    student = StudentInfo.objects.filter(roll_no=roll_no, exam_type=exam_type_db).first()
    if not student:
        context = {'exam': exam, 'year': year, 'roll_no': roll_no}
        return render(request, 'roll_not_found.html', context, status=404)
    marks = get_object_or_404(Marks, student=student)

    # Subject name mapping
    SUBJECT_LABELS_MAP = {
        'bangla': 'Bangla',
        'english': 'English',
        'math': 'Mathematics',
        'physics': 'Physics',
        'chemistry': 'Chemistry',
        'biology': 'Biology',
        'higher_math': 'Higher Mathematics',
        'ict': 'ICT',
        'islam_moral': 'Islam and Moral Education',
        'hindu_moral': 'Hindu Religion and Moral Education',
        'buddha_moral': 'Buddhist Religion and Moral Education',
        'christian_moral': 'Christian Religion and Moral Education',
        'bangladesh_world': 'Bangladesh and Global Studies',
        'agriculture': 'Agriculture Studies',
        'home_science': 'Home Science',
        'finance_banking': 'Finance and Banking',
        'accounting': 'Accounting',
        'business_ent': 'Business Entrepreneurship',
        'general_science': 'General Science',
        'music': 'Music',
        'geography': 'Geography',
        'civics': 'Civics and Good Governance',
        'economics': 'Economics',
        'history_bd': 'Bangladesh History',
        'statistics': 'Statistics',
        'management': 'Business Organization and Management',
        'finance': 'Finance, Banking and Insurance',
        'production': 'Production Management and Marketing',
        'logic': 'Logic',
        'history': 'History',
        'islamic_history': 'Islamic History and Culture',
        'social_work': 'Social Work',
        'sociology': 'Sociology',
        'physical_education': 'Physical Education, Health and Sports',
        'career_education': 'Career Education',
    }
    # Standard BD board syllabus max marks per subject (public curriculum constants,
    # not derived from this student's data) — used only to draw the progress bars.
    SUBJECT_MAX_MARKS = {'bangla': 200, 'english': 200, 'ict': 50}

    subjects = []
    for field in Marks._meta.get_fields():
        if (
            field.name not in ['id', 'student', 'total_marks']
            and hasattr(field, 'get_internal_type')
            and field.get_internal_type() in ['IntegerField', 'PositiveIntegerField']
        ):
            value = getattr(marks, field.name)
            if not value:
                continue
            label = SUBJECT_LABELS_MAP.get(field.name)
            if not label:
                label = field.name.replace('_', ' ').title()
            max_marks = SUBJECT_MAX_MARKS.get(field.name, 100)
            subjects.append({
                'label': label,
                'marks': value,
                'max': max_marks,
                'pct': min(round(value / max_marks * 100), 100),
            })

    context = {
        'student': student,
        'marks': marks,
        'exam': exam,
        'year': year,
        'exam_type': exam_type_db,
        'subjects': subjects,
        'total_max': sum(s['max'] for s in subjects),
    }
    return render(request, 'individual_result.html', context)
