"""
Manifest of trusted official sources (UK government bodies + WHO) for the
Type 2 diabetes knowledge base.

Each entry describes where a document comes from, which extraction
profile to use for that domain, and the licence it is published under.
This is the single place to add/remove/update sources -
scripts/fetch_sources.py reads this list and does the fetching.
"""

# How to find the main article content for each site. BeautifulSoup CSS
# selectors, tried in order until one matches.
DOMAIN_PROFILES = {
    "nhs_uk": {
        "content_selectors": ["main#maincontent", "#maincontent"],
    },
    "england_nhs_uk": {
        "content_selectors": ["article.rich-text", "main.main"],
    },
    "nice_org_uk": {
        "content_selectors": ["div.zone-content", "main"],
    },
    "nidirect_gov_uk": {
        "content_selectors": ["article#main-article", "article.article-content"],
    },
    "who_int": {
        "content_selectors": ["article.sf-detail-body-wrapper", "main"],
    },
}

# license identifiers, for the metadata sidecar written next to each file.
LICENSES = {
    "nhs_ogl": "Open Government Licence v3.0 (Crown copyright, nhs.uk)",
    "england_nhs_ogl": "Open Government Licence v3.0 (Crown copyright, england.nhs.uk)",
    "nice_copyright": (
        "NICE copyright - free to use for personal, educational, "
        "non-commercial research with attribution. Do not imply NICE "
        "endorsement. See https://www.nice.org.uk/re-using-our-content"
    ),
    "nidirect_crown_copyright": (
        "Crown copyright (Northern Ireland Executive, nidirect.gov.uk), "
        "reused under the Open Government Licence v3.0"
    ),
    "who_cc_by_nc_sa": (
        "© World Health Organization - reused under Creative Commons "
        "Attribution-NonCommercial-ShareAlike 3.0 IGO (CC BY-NC-SA 3.0 IGO). "
        "See https://www.who.int/about/policies/publishing/copyright"
    ),
}

SOURCES = [
    # --- NHS.uk: Type 2 diabetes condition pages ---
    {
        "slug": "nhs_type2_diabetes_overview",
        "url": "https://www.nhs.uk/conditions/type-2-diabetes/what-is-type-2-diabetes/",
        "domain_profile": "nhs_uk",
        "license": "nhs_ogl",
    },
    {
        "slug": "nhs_type2_diabetes_symptoms",
        "url": "https://www.nhs.uk/conditions/type-2-diabetes/symptoms/",
        "domain_profile": "nhs_uk",
        "license": "nhs_ogl",
    },
    {
        "slug": "nhs_type2_diabetes_treatment",
        "url": "https://www.nhs.uk/conditions/type-2-diabetes/treatment/",
        "domain_profile": "nhs_uk",
        "license": "nhs_ogl",
    },
    {
        "slug": "nhs_type2_diabetes_complications",
        "url": "https://www.nhs.uk/conditions/type-2-diabetes/complications/",
        "domain_profile": "nhs_uk",
        "license": "nhs_ogl",
    },
    {
        "slug": "nhs_type2_diabetes_support",
        "url": "https://www.nhs.uk/conditions/type-2-diabetes/support/",
        "domain_profile": "nhs_uk",
        "license": "nhs_ogl",
    },
    {
        "slug": "nhs_diabetes_overview",
        "url": "https://www.nhs.uk/conditions/diabetes/",
        "domain_profile": "nhs_uk",
        "license": "nhs_ogl",
    },
    # --- NHS England: national programmes ---
    {
        "slug": "nhs_type2_diabetes_path_to_remission",
        "url": "https://www.england.nhs.uk/diabetes/treatment-care/diabetes-remission/",
        "domain_profile": "england_nhs_uk",
        "license": "england_nhs_ogl",
    },
    # --- NICE: NG28 (Type 2 diabetes in adults: management) ---
    {
        "slug": "nice_type2_diabetes_overview",
        "url": "https://www.nice.org.uk/guidance/ng28",
        "domain_profile": "nice_org_uk",
        "license": "nice_copyright",
    },
    {
        "slug": "nice_type2_diabetes_individualised_care",
        "url": "https://www.nice.org.uk/guidance/ng28/chapter/Individualised-care",
        "domain_profile": "nice_org_uk",
        "license": "nice_copyright",
    },
    {
        "slug": "nice_type2_diabetes_education",
        "url": "https://www.nice.org.uk/guidance/ng28/chapter/Education",
        "domain_profile": "nice_org_uk",
        "license": "nice_copyright",
    },
    {
        "slug": "nice_type2_diabetes_dietary_advice",
        "url": "https://www.nice.org.uk/guidance/ng28/chapter/Dietary-advice-and-interventions",
        "domain_profile": "nice_org_uk",
        "license": "nice_copyright",
    },
    {
        "slug": "nice_type2_diabetes_blood_glucose_management",
        "url": "https://www.nice.org.uk/guidance/ng28/chapter/Blood-glucose-management",
        "domain_profile": "nice_org_uk",
        "license": "nice_copyright",
    },
    {
        "slug": "nice_type2_diabetes_initial_medicines",
        "url": "https://www.nice.org.uk/guidance/ng28/chapter/Initial-medicines",
        "domain_profile": "nice_org_uk",
        "license": "nice_copyright",
    },
    {
        "slug": "nice_type2_diabetes_complications",
        "url": "https://www.nice.org.uk/guidance/ng28/chapter/Complications",
        "domain_profile": "nice_org_uk",
        "license": "nice_copyright",
    },
    {
        "slug": "nice_type2_diabetes_person_centred_care",
        "url": "https://www.nice.org.uk/guidance/ng28/chapter/Person-centred-medicine",
        "domain_profile": "nice_org_uk",
        "license": "nice_copyright",
    },
    {
        "slug": "nice_type2_diabetes_how_to_introduce_medicines",
        "url": "https://www.nice.org.uk/guidance/ng28/chapter/How-to-introduce-medicines",
        "domain_profile": "nice_org_uk",
        "license": "nice_copyright",
    },
    {
        "slug": "nice_type2_diabetes_further_medication",
        "url": "https://www.nice.org.uk/guidance/ng28/chapter/Further-medication",
        "domain_profile": "nice_org_uk",
        "license": "nice_copyright",
    },
    {
        "slug": "nice_type2_diabetes_insulin_based_treatments",
        "url": "https://www.nice.org.uk/guidance/ng28/chapter/Insulin-based-treatments",
        "domain_profile": "nice_org_uk",
        "license": "nice_copyright",
    },
    {
        "slug": "nice_type2_diabetes_reviewing_medicines",
        "url": "https://www.nice.org.uk/guidance/ng28/chapter/Reviewing-medicines",
        "domain_profile": "nice_org_uk",
        "license": "nice_copyright",
    },
    # --- nidirect.gov.uk: Northern Ireland's official health information site ---
    {
        "slug": "nidirect_type2_diabetes_overview",
        "url": "https://www.nidirect.gov.uk/conditions/type-2-diabetes",
        "domain_profile": "nidirect_gov_uk",
        "license": "nidirect_crown_copyright",
    },
    # --- WHO: global fact sheet (general/epidemiological, not UK-specific
    # clinical recommendations, to avoid conflicting with NICE's guidance) ---
    {
        "slug": "who_diabetes_fact_sheet",
        "url": "https://www.who.int/news-room/fact-sheets/detail/diabetes",
        "domain_profile": "who_int",
        "license": "who_cc_by_nc_sa",
    },
    {
        "slug": "nhs_medicine_dapagliflozin",
        "url": "https://www.nhs.uk/medicines/dapagliflozin/",
        "domain_profile": "nhs_uk",
        "license": "nhs_ogl",
    },
    {
        "slug": "nhs_medicine_insulin_overview",
        "url": "https://www.nhs.uk/medicines/insulin/",
        "domain_profile": "nhs_uk",
        "license": "nhs_ogl",
    },
    {
        "slug": "nhs_medicine_insulin_for_type2_diabetes",
        "url": "https://www.nhs.uk/medicines/insulin/insulin-for-type-2-diabetes/",
        "domain_profile": "nhs_uk",
        "license": "nhs_ogl",
    },
]

# NHS.uk medicines A-Z pages for the main Type 2 diabetes medications, each
# broken into several sub-pages (about/dosage/side effects/etc). Generated
# from an explicit drug list and explicit URL templates, not discovered by
# crawling, so every URL fetched is still one we've deliberately chosen.
MEDICINES_WITH_STANDARD_SUBPAGES = ["metformin", "gliclazide", "empagliflozin", "sitagliptin"]

MEDICINE_SUBPAGE_TEMPLATES = [
    ("about-{drug}", "about"),
    ("how-and-when-to-take-{drug}", "how_and_when_to_take"),
    ("side-effects-of-{drug}", "side_effects"),
    ("who-can-and-cannot-take-{drug}", "who_can_take"),
    ("common-questions-about-{drug}", "common_questions"),
    ("pregnancy-breastfeeding-and-fertility-while-taking-{drug}", "pregnancy_and_fertility"),
    ("taking-{drug}-with-other-medicines-and-herbal-supplements", "interactions"),
]

for _drug in MEDICINES_WITH_STANDARD_SUBPAGES:
    for _path_template, _short_name in MEDICINE_SUBPAGE_TEMPLATES:
        SOURCES.append(
            {
                "slug": f"nhs_medicine_{_drug}_{_short_name}",
                "url": f"https://www.nhs.uk/medicines/{_drug}/{_path_template.format(drug=_drug)}/",
                "domain_profile": "nhs_uk",
                "license": "nhs_ogl",
            }
        )

# NICE's Clinical Knowledge Summaries site (cks.nice.org.uk) explicitly
# prohibits automated scraping/data mining in its terms and will block
# offending IPs, so it must never be added to SOURCES above.
# See: https://cks.nice.org.uk/cks-uk-only.html
FORBIDDEN_DOMAINS = ["cks.nice.org.uk"]
