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

    # Subject name mapping as provided by the user
    SUBJECT_LABELS_MAP = {
        'bangla': 'Bangla',
        'english': 'English',
        'math': 'Mathematics',
        'physics': 'Physics',
        'chemistry': 'Chemistry',
        'biology': 'Biology',
        'higher_math': 'Higher Mathematics',
        'ict': 'Information & Communication Technology',
        'islam_moral': 'Islam and Moral Education',
        'hindu_moral': 'Hindu Religion and Moral Education',
        'buddha_moral': 'Buddha Religion and Moral Education',
        'christian_moral': 'Christian Religion and Moral Education',
        'bangladesh_world': 'Bangladesh and Global Studies',
        'agriculture': 'Agriculture Studies',
        'home_science': 'Home Science',
        'finance_banking': 'Finance & Banking',
        'accounting': 'Accounting',
        'business_ent': 'Business Entrepreneurship',
        'general_science': 'General Science',
        'music': 'Music',
        'geography': 'Geography',
        'civics': 'Civics',
        'economics': 'Economics',
        'history_bd': 'History of Bangladesh',
        'physical_education': 'Physical Education, Health and Sports',
        'career_education': 'Career Education',
        'management': 'Business Organization & Management',
        'finance': 'Finance, Banking & Insurance',
        'production': 'Production Management & Marketing',
        'statistics': 'Statistics',
        'logic': 'Logic',
        'sociology': 'Sociology',
        'social_work': 'Social Work',
        'history': 'History',
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
                # fallback: humanize
                label = field.name.replace('_', ' ').title()
            subject_fields.append((field.name, label))

    context = {
        'student': student,
        'marks': marks,
        'exam_type': exam_type,  # Keep lowercase for URLs
        'subject_fields': subject_fields,
    }
    return render(request, 'individual_result.html', context)

