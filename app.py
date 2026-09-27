
import os
import re
from io import BytesIO
from datetime import date

import requests
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="SAP ABAP Job Monitor",
    page_icon="🔎",
    layout="wide"
)

st.title("🔎 SAP ABAP Job Monitor")
st.write("Hyderabad | Remote | Hybrid | 5 Years Experience")

QUERIES = [
    "SAP ABAP Hyderabad 5 years jobs",
    "SAP ABAP Hyderabad remote jobs",
    "SAP ABAP Hyderabad hybrid jobs",
    "SAP S4HANA ABAP Hyderabad jobs",
    "SAP RAP developer Hyderabad jobs",
    "SAP ABAP remote India jobs",
    "SAP ABAP Deloitte PwC EY KPMG Hyderabad",
    "SAP ABAP product companies Hyderabad"
]

COLUMNS = [
    "Date Found",
    "Company",
    "Role",
    "Location",
    "Work Model",
    "Job Type",
    "Experience",
    "Job Link",
    "Description"
]


def get_api_key():
    return st.secrets.get(
        "SERPER_API_KEY",
        os.getenv("SERPER_API_KEY", "")
    )


def detect_work_model(text):
    text = text.lower()

    if re.search(r"\bhybrid\b", text):
        return "Hybrid"

    if re.search(r"\bremote\b|\bwfh\b|work from home", text):
        return "Remote / WFH"

    if re.search(r"work from office|on.site", text):
        return "Office"

    return "Not specified"


def detect_job_type(text):
    text = text.lower()

    if re.search(r"\bcontract\b|\bcontractual\b", text):
        return "Contract"

    if re.search(r"full.time|permanent", text):
        return "Full-time"

    return "Not specified"


def detect_experience(text):
    pattern = (
        r"\d+(?:\.\d+)?\s*[-–]\s*"
        r"\d+(?:\.\d+)?\s*(?:years|yrs)"
        r"|\d+(?:\.\d+)?\s*\+\s*(?:years|yrs)"
    )

    match = re.search(pattern, text, re.I)

    if match:
        return match.group()

    return "Not specified"


def search_jobs(api_key):
    rows = []

    headers = {
        "X-API-KEY": api_key,
        "Content-Type": "application/json"
    }

    for query in QUERIES:
        try:
            response = requests.post(
                "https://google.serper.dev/search",
                headers=headers,
                json={
                    "q": query,
                    "num": 20,
                    "gl": "in"
                },
                timeout=30
            )

            response.raise_for_status()

            results = response.json().get("organic", [])

            for job in results:
                title = job.get("title", "")
                link = job.get("link", "")
                snippet = job.get("snippet", "")

                combined = f"{title} {snippet}"

                if not re.search(
                    r"\bABAP\b", combined, re.I
                ):
                    continue

                rows.append({
                    "Date Found": str(date.today()),
                    "Company": "Verify in job listing",
                    "Role": title,
                    "Location": "Verify in job listing",
                    "Work Model": detect_work_model(combined),
                    "Job Type": detect_job_type(combined),
                    "Experience": detect_experience(combined),
                    "Job Link": link,
                    "Description": snippet
                })

        except requests.RequestException as error:
            st.warning(
                f"Search failed for {query}: {error}"
            )

    if not rows:
        return pd.DataFrame(columns=COLUMNS)

    df = pd.DataFrame(rows)

    df = df.drop_duplicates(
        subset=["Job Link"]
    )

    return df


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

        worksheet = writer.sheets["SAP ABAP Jobs"]

        worksheet.freeze_panes = "A2"
        worksheet.auto_filter.ref = worksheet.dimensions

        for column in worksheet.columns:
            letter = column[0].column_letter
            worksheet.column_dimensions[letter].width = 25

    return output.getvalue()


st.subheader("Today's Job Search")

if st.button(
    "🔎 Run Today's Job Search",
    type="primary",
    use_container_width=True
):

    api_key = get_api_key()

    if not api_key:
        st.error(
            "SERPER_API_KEY is missing. "
            "Configure it in Streamlit Secrets."
        )

    else:
        with st.spinner("Searching SAP ABAP jobs..."):
            st.session_state["jobs"] = search_jobs(api_key)


if "jobs" in st.session_state:

    df = st.session_state["jobs"]

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Jobs Found",
        len(df)
    )

    col2.metric(
        "Remote / Hybrid",
        len(df[
            df["Work Model"].isin([
                "Remote / WFH",
                "Hybrid"
            ])
        ])
    )

    col3.metric(
        "Unique Job Links",
        df["Job Link"].nunique()
    )

    st.subheader("Job Results")

    work_filter = st.multiselect(
        "Filter by Work Model",
        options=[
            "Remote / WFH",
            "Hybrid",
            "Office",
            "Not specified"
        ],
        default=[
            "Remote / WFH",
            "Hybrid",
            "Not specified"
        ]
    )

    filtered = df[
        df["Work Model"].isin(work_filter)
    ]

    st.dataframe(
        filtered,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Job Link": st.column_config.LinkColumn(
                "Apply / View Job"
            )
        }
    )

    excel_file = create_excel(filtered)

    st.download_button(
        label="⬇️ Download Excel",
        data=excel_file,
        file_name=f"SAP_ABAP_Jobs_{date.today()}.xlsx",
        mime=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        use_container_width=True
    )

    st.caption(
        "Work model, experience and job type are extracted "
        "from search snippets. Verify details on the "
        "original job listing before applying."
    )

else:
    st.info(
        "Click Run Today's Job Search to find SAP ABAP jobs."
    )
