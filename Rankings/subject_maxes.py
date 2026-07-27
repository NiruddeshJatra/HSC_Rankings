# Per-subject maximum marks, by exam level (public BD board syllabus constants,
# not derived from any student's data). Two-paper subjects are worth 200; every
# level has its own default for subjects not explicitly listed.

HSC_SUBJECT_MAX = {
    'bangla': 200,
    'english': 200,
    'ict': 100,
}
HSC_DEFAULT_MAX = 200

SSC_SUBJECT_MAX = {
    'bangla': 200,
    'english': 200,
    'ict': 50,
    'career_education': 50,
}
SSC_DEFAULT_MAX = 100

LEVEL_TABLES = {
    'HSC': (HSC_SUBJECT_MAX, HSC_DEFAULT_MAX),
    'SSC': (SSC_SUBJECT_MAX, SSC_DEFAULT_MAX),
}


def subject_max(exam_type, field_name):
    """Max marks for a subject field, given an exam_type like 'HSC_2024'.

    Level is derived from the exam_type prefix rather than a hardcoded list of
    exam types, since new exam sets are added every year. Raises on an
    unrecognised level rather than silently defaulting.
    """
    for level, (overrides, default) in LEVEL_TABLES.items():
        if exam_type.startswith(level):
            return overrides.get(field_name, default)
    raise ValueError(f"Unknown exam level for exam_type {exam_type!r}; expected prefix in {sorted(LEVEL_TABLES)}")
