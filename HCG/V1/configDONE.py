# Basic keys for tables with 5 columns.
BASIC_KEYS_5 = [
    'acronym_author_year',
    'type_design_size',
    'patient_population',
    'endpoint_results',
    'summary'
]

BASIC_KEYS_5_3 = [
    'author',
    'type_of_study/years_of_recruitment',
    'number_of_patients',
    'short_term_results_PCI_vs_CABG',
    'long_term_results_PCI_vs_CABG',
]
# Basic keys for tables with 6 columns.
BASIC_KEYS_6 = [
    'acronym_author_year',
    'type_design_size',
    'patient_population',
    'intervention_comparator',
    'endpoint_results',
    'limitations_adverse_events'
]

BASIC_KEYS_6_2 = [
    'acronym_author_year',
    'type_design',
    'size',
    'inclusion_exclusion_criteria',
    'primary_endpoint',
    'results_pValues',
]

BASIC_KEYS_6_4  = [
    'acronym_author_year',
    'study_design',
    'type_of_surgery',
    'number_of_patients',
    'outcome_assessed',
    'findings',
]

BASIC_KEYS_7 = [
    'acronym_author_year',
    'type_design_size',
    'patient_population',
    'HBPM',
    'Daytime_ABPM',
    '24-h_ABPM',
    'Results/Comments'
]

BASIC_KEYS_7_4 = [
    'acronym_author_year',
    'aim',
    'type',
    'size',
    'intervention_group',
    'comparator_group',
    'outcome',
]


BASIC_KEYS_6_4 = [
    'acronym_author_year',
    'aim',
    'type',
    'size_details',
    'outcomes',
    'comments_limitations',
]


BASIC_KEYS_7_2 = [
    "acronym_author_year",
    "type_design",
    "size",
    "inclusion_exclusion_criteria",
    "primary_endpoint",
    "results_pValues",
    "summary_conclusions"
]

BASIC_KEYS_8 = [
    "acronym_author_year",
    "type_design",
    "size",
    "inclusion_exclusion_criteria",
    "classification_system",
    "primary_endpoint",
    "results_pValues",
    "summary_conclusions"
]

BASIC_KEYS_9 = [
    "study_author_year",
    "aim",
    "type_size",
    "intervention_vs_comparator",
    "inclusion_criteria",
    "exclusion_criteria",
    "intervention",
    "comparator",
    "results",
]

BASIC_KEYS_13 = [
    "study_author_year",
    "aim",
    "type_design",
    "size",
    "inclusion_criteria",
    "exclusion_criteria",
    "primary_endpoint",
    "secondary_endpoint",
    "results",
    "pValues",
    "OR_HR_RR",
    "study_limitations",
    "comments"
]

BASIC_KEYS_14 = [
    'trial',
    'no.',
    'age',
    'femal',
    'CAD',
    'acute_death',
    'acute_Q_Wave_MI',
    'late_death',
    'late_Q_Wave_MI',
    'late_angina',
    'repeat_revascularization',
    'primary_endpoint',
    'primary_endpoint_CABG',
    'follow-up_years'

]

BASIC_KEYS_11 = [
    'study',
    'location',
    'number_of_patients',
    'average_age',
    'female_patients',
    'CAD',
    'enrollment_period',
    'combined_death/MI/CVA_HR_95%_CI',
    'repeat_revascularization_HR_95%_CI',
    'MACCE_HR_95%_CI',
    'follow-up_in_months',
]

SCRAPING = [
    {
        'directory': 'DONE/blood-cholesterol-management',
        'guideline_xml': 'CIR.0000000000000625.xml',
        'datasup_xml': 'data supplement.xml',
        'cit_version': 1,
        'left_down': 90,
        'left_up': 110,
        'dsup_version': 1,
        'guideline_version': 1,
        'row_filed_gap': 60,
    },
    {
        'directory': 'DONE/bradycardia-and-cardiac-conduction-delay',
        'guideline_xml': 'bradycardia-and-cardiac-conduction-delay.xml',
        'datasup_xml': 'data supplement.xml',
        'cit_version': 1,
        'left_down': 95,
        'left_up': 110,
        'dsup_version': 1,
        'guideline_version': 1,
        'row_filed_gap': 60,
    },
    {
        'directory': 'DONE/CHF',
        'guideline_xml': '1-s2.0-S0735109718368451-main.xml',
        'datasup_xml': 'ACHD_Guideline_ES-FT_Data_Supplements_08-02-18.xml',
        'cit_version': 1,
        'left_down': 63,
        'left_up': 80,
        'dsup_version': 2,
        'guideline_version': 2,
        'row_filed_gap': 60,
    },
    {
        'directory': 'DONE/Congenital HeartDisease',
        'guideline_xml': 'j.jacc.2018.08.1029.full.xml',
        'datasup_xml': 'ACHD_Guideline_ES-FT_Data_Supplements_08-02-18.xml',
        'cit_version': 1,
        'left_down': 63,
        'left_up': 80,
        'dsup_version': 2,
        'guideline_version': 1,
        'row_filed_gap': 60,
    },
    {
        'directory': 'DONE/Coronary artery disease',
        'guideline_xml': '1082.full.xml',
        'datasup_xml': 'DAPT_Data_Supplement_1.xml',
        'cit_version': 2,
        'left_down': 53,
        'left_up': 70,
        'dsup_version': 1,
        'guideline_version': 2,
        'row_filed_gap': 60,
    },
    {
        'directory': 'DONE/High Blood Pressure',
        'guideline_xml': 'e127.full.xml',
        'datasup_xml': '2017_HBP_FT_DATA_SUPPLEMENT.xml',
        'cit_version': 1,
        'left_down': 88,
        'left_up': 110,
        'dsup_version': 1,
        'guideline_version': 2,
        'row_filed_gap': 60,
    },
    {
        'directory': 'DONE/Primary Prevention of Cardiovascular Disease',
        'guideline_xml': 'j.jacc.2019.03.010.full.xml',
        'datasup_xml': '20190301_Prevention_Data_Supplement_Tables.xml',
        'cit_version': 1,
        'left_down': 74,
        'left_up': 95,
        'dsup_version': 1,
        'guideline_version': 1,
        'row_filed_gap': 60,
    },
    {
        'directory': 'DONE/Supraventricular Tachycardia',
        'guideline_xml': 'CIR.0000000000000311.xml',
        'datasup_xml': 'data_supplement.xml',
        'cit_version': 2,
        'left_down': 53,
        'left_up': 70,
        'dsup_version': 2,
        'guideline_version': 1,
        'row_filed_gap': 60,
    },
    {
        'directory': 'DONE/Ventricular Arrhythmia',
        'guideline_xml': 'CIR.0000000000000549.xml',
        'datasup_xml': 'data_supplement.xml',
        'cit_version': 1,
        'left_down': 122,
        'left_up': 140,
        'dsup_version': 1,
        'guideline_version': 1,
        'row_filed_gap': 60,
    },
]

#I removed the files that were not in the "DONE" folder
