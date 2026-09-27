import re
from io import BytesIO
from datetime import date

import requests
import pandas as pd
import streamlit as st


st.set_page_config(
    page_title="SAP ABAP Job Monitor",
    page_icon="💼",
    layout="wide"
)

st.title("💼 SAP ABAP Job Monitor")
st.caption("Hyderabad + Remote/Hybrid SAP ABAP opportunities")


# ---------------------------------------------------------
# SEARCH QUERIES
# ---------------------------------------------------------

QUERIES = [
    '"SAP ABAP" Hyderabad jobs 5 years',
    '"SAP ABAP Developer" Hyderabad jobs',
    '"SAP ABAP" Hyderabad remote jobs',
    '"SAP ABAP" Hyderabad hybrid jobs',
    '"SAP S/4HANA ABAP" Hyderabad jobs',
    '"SAP RAP" Hyderabad developer jobs',
    '"SAP ABAP" remote India jobs',
    '"SAP ABAP" Hyderabad Deloitte',
    '"SAP ABAP" Hyderabad PwC',
    '"SAP ABAP" Hyderabad EY',
    '"SAP ABAP" Hyderabad KPMG',
    '"SAP ABAP" Hyderabad product company',
]


# ---------------------------------------------------------
# COMPANY DETECTION
# ---------------------------------------------------------

KNOWN_COMPANIES = [
    "Deloitte",
    "PwC",
    "EY",
    "KPMG",
    "Accenture",
    "IBM",
    "SAP",
    "Microsoft",
    "Amazon",
    "Google",
    "Cognizant",
    "Capgemini",
    "Infosys",
    "Wipro",
    "TCS",
    "Tech Mahindra",
    "HCLTech",
    "NTT DATA",
    "EPAM",
    "Genpact",
    "DXC Technology",
    "LTIMindtree",
    "Mphasis",
    "Oracle",
    "Thomson Reuters",
    "ArcelorMittal",
    "Regal Rexnord",
    "Hitachi",
    "Bosch",
    "Siemens",
]


def detect_company(title, snippet, link):
    text = f"{title} {snippet} {link}"

    # First check known companies
    for company in KNOWN_COMPANIES:
        if company.lower() in text.lower():
            return company

    # Try common title formats
    patterns = [
        r"\bat\s+([A-Z][A-Za-z0-9& .-]{2,50})",
        r"\|\s*([A-Z][A-Za-z0-9& .-]{2,50})$",
        r"-\s*([A-Z][A-Za-z0-9& .-]{2,50})$",
    ]

    for pattern in patterns:
        match = re.search(pattern, title)
        if match:
            company = match.group(1).strip()
            if len(company) < 60:
                return company

    # Try extracting company from domain
    domain_match = re.search(
        r"https?://(?:www\.)?([^/]+)",
        link
    )

    if domain_match:
        domain = domain_match.group(1)

        ignored = [
            "google.com",
            "linkedin.com",
            "indeed.com",
            "naukri.com",
            "foundit.in",
            "glassdoor.com",
            "jobstreet.com",
        ]

        if domain not in ignored:
            name = domain.split(".")[0]
            return name.replace("-", " ").title()

    return "Verify in listing"


# ---------------------------------------------------------
# ROLE CLEANING
# ---------------------------------------------------------

def clean_role(title):
    role = title.strip()

    # Remove common website suffixes
    role = re.sub(
        r"\s*[-|]\s*(LinkedIn|Indeed|Glassdoor|Naukri|Foundit).*$",
        "",
        role,
        flags=re.IGNORECASE
    )

    return role[:150]


# ---------------------------------------------------------
# WORK MODEL
# ---------------------------------------------------------

def detect_work_model(text):
    text = text.lower()

    if any(x in text for x in [
        "remote",
        "work from home",
        "wfh",
        "fully remote"
    ]):
        return "Remote / WFH"

    if any(x in text for x in [
        "hybrid",
        "work from office and home"
    ]):
        return "Hybrid"

    if any(x in text for x in [
        "on-site",
        "onsite",
        "office",
        "work from office"
    ]):
        return "Office"

    return "Not specified"


# ---------------------------------------------------------
# JOB TYPE
# ---------------------------------------------------------

def detect_job_type(text):
    text = text.lower()

    if any(x in text for x in [
        "contract",
        "contractor",
        "contractual"
    ]):
        return "Contract"

    if any(x in text for x in [
        "full time",
        "full-time",
        "permanent"
    ]):
        return "Full-time"

    return "Not specified"


# ---------------------------------------------------------
# EXPERIENCE
# ---------------------------------------------------------

def detect_experience(text):
    text = text.lower()

    patterns = [
        r"(\d+)\s*(?:-|to)\s*(\d+)\s*years?",
        r"(\d+)\+\s*years?",
        r"(\d+)\s*years?",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)

        if match:
            if len(match.groups()) == 2:
                return f"{match.group(1)}-{match.group(2)} years"

            return f"{match.group(1)}+ years"

    return "Not specified"


# ---------------------------------------------------------
# SAP ABAP FILTER
# ---------------------------------------------------------

def is_relevant(title, snippet):
    text = f"{title} {snippet}".lower()

    keywords = [
        "sap abap",
        "abap developer",
        "abap consultant",
        "s/4hana abap",
        "sap rap",
        "rap developer",
    ]

    return any(keyword in text for keyword in keywords)


# ---------------------------------------------------------
# SERPER SEARCH
# ---------------------------------------------------------

def search_serper(query, api_key):

    url = "https://google.serper.dev/search"

    headers = {
        "X-API-KEY": api_key,
        "Content-Type": "application/json",
    }

    payload = {
        "q": query,
        "num": 10,
        "gl": "in",
        "hl": "en",
    }

    response = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=30
    )

    response.raise_for_status()

    return response.json()


# ---------------------------------------------------------
# COLLECT JOBS
# ---------------------------------------------------------

def collect_jobs(api_key):

    jobs = []
    seen_links = set()

    for query in QUERIES:

        try:
            data = search_serper(query, api_key)

        except Exception as e:
            st.warning(f"Search failed for: {query}")
            continue

        results = data.get("organic", [])

        for item in results:

            title = item.get("title", "").strip()
            link = item.get("link", "").strip()
            snippet = item.get("snippet", "").strip()

            if not title or not link:
                continue

            if link in seen_links:
                continue

            if not is_relevant(title, snippet):
                continue

            seen_links.add(link)

            combined_text = f"{title} {snippet}"

            company = detect_company(
                title,
                snippet,
                link
            )

            role = clean_role(title)

            work_model = detect_work_model(
                combined_text
            )

            job_type = detect_job_type(
                combined_text
            )

            experience = detect_experience(
                combined_text
            )

            jobs.append({
                "Date Found": date.today().isoformat(),
                "Company": company,
                "Role": role,
                "Location": "Hyderabad / India",
                "Work Model": work_model,
                "Job Type": job_type,
                "Experience": experience,
                "Job Link": link,
                "Description": snippet,
                "Search Query": query,
            })

    return pd.DataFrame(jobs)


# ---------------------------------------------------------
# EXCEL
# ---------------------------------------------------------

def create_excel(df):

    output = BytesIO()

    with pd.ExcelWriter(
        output,
        engine="openpyxl"
    ) as writer:

        df.to_excel(
            writer,
            index=False,
            sheet_name="SAP ABAP Jobs"
        )

    output.seek(0)

    return output


# ---------------------------------------------------------
# API KEY
# ---------------------------------------------------------

try:
    API_KEY = st.secrets["SERPER_API_KEY"]

except Exception:
    API_KEY = ""


if not API_KEY:

    st.error(
        "SERPER_API_KEY is not configured."
    )

    st.info(
        "Add SERPER_API_KEY in Streamlit → "
        "Manage app → Settings → Secrets."
    )

    st.stop()


# ---------------------------------------------------------
# RUN SEARCH
# ---------------------------------------------------------

if st.button(
    "🔎 Run Today's Job Search",
    type="primary"
):

    with st.spinner(
        "Searching SAP ABAP jobs..."
    ):

        df = collect_jobs(API_KEY)

    if df.empty:

        st.warning(
            "No relevant jobs found."
        )

    else:

        st.session_state["jobs"] = df


# ---------------------------------------------------------
# DISPLAY RESULTS
# ---------------------------------------------------------

if "jobs" in st.session_state:

    df = st.session_state["jobs"].copy()

    st.success(
        f"Found {len(df)} unique job links."
    )

    st.metric(
        "Unique Job Links",
        len(df)
    )

    st.subheader("🔎 Filters")

    work_models = st.multiselect(
        "Filter by Work Model",
        [
            "Remote / WFH",
            "Hybrid",
            "Office",
            "Not specified",
        ],
        default=[
            "Remote / WFH",
            "Hybrid",
            "Not specified",
        ]
    )

    filtered = df[
        df["Work Model"].isin(work_models)
    ]

    st.subheader("💼 Job Results")

    st.dataframe(
        filtered,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Job Link": st.column_config.LinkColumn(
                "Job Link"
            )
        }
    )

    excel_file = create_excel(filtered)

    st.download_button(
        label="⬇️ Download Excel",
        data=excel_file,
        file_name=(
            "SAP_ABAP_Hyderabad_Jobs_"
            f"{date.today().isoformat()}.xlsx"
        ),
        mime=(
            "application/vnd.openxmlformats-"
            "officedocument.spreadsheetml.sheet"
        )
)
