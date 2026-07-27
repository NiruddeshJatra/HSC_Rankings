# Subject code -> Marks model field, per exam type.
HSC_SUBJECT_CODE_MAP = {
    '101': 'bangla',
    '107': 'english',
    '275': 'ict',
    '174': 'physics',
    '176': 'chemistry',
    '178': 'biology',
    '265': 'higher_math',
    '129': 'statistics',
    '292': 'finance',
    '277': 'management',
    '253': 'accounting',
    '286': 'production',
    '109': 'economics',
    '121': 'logic',
    '117': 'sociology',
    '271': 'social_work',
    '273': 'home_science',
    '267': 'islamic_history',
    '269': 'civics',
}

SSC_SUBJECT_CODE_MAP = {
    '101': 'bangla',
    '107': 'english',
    '109': 'math',
    '136': 'physics',
    '137': 'chemistry',
    '138': 'biology',
    '126': 'higher_math',
    '154': 'ict',
    '111': 'islam_moral',
    '112': 'hindu_moral',
    '113': 'buddha_moral',
    '114': 'christian_moral',
    '150': 'bangladesh_world',
    '134': 'agriculture',
    '151': 'home_science',
    '152': 'finance_banking',
    '146': 'accounting',
    '143': 'business_ent',
    '127': 'general_science',
    '149': 'music',
    '110': 'geography',
    '140': 'civics',
    '141': 'economics',
    '153': 'history_bd',
    '147': 'physical_education',
    '156': 'career_education',
}

SUBJECT_MAPS = {
    'hsc': HSC_SUBJECT_CODE_MAP,
    'ssc': SSC_SUBJECT_CODE_MAP,
}


def get_subject_map(exam):
    try:
        return SUBJECT_MAPS[exam.lower()]
    except KeyError:
        raise ValueError(f"Unknown exam type {exam!r}; must be one of {sorted(SUBJECT_MAPS)}")
