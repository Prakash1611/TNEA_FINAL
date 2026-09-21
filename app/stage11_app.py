from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st


ROOT = Path(__file__).resolve().parent.parent
INPUT_PATH = ROOT / "data" / "integrated" / "tnea_integrated_master.csv"
KEY_COLUMNS = ["year", "college_code", "branch_code"]
CATEGORIES = ["OC", "BC", "BCM", "MBC", "SC", "SCA", "ST"]
CATEGORY_COLUMNS = {
    "OC": {"cutoff": "cutoff_oc", "rank": "rank_oc"},
    "BC": {"cutoff": "cutoff_bc", "rank": "rank_bc"},
    "BCM": {"cutoff": "cutoff_bcm", "rank": "rank_bcm"},
    "MBC": {"cutoff": "cutoff_mbc", "rank": "rank_mbc"},
    "SC": {"cutoff": "cutoff_sc", "rank": "rank_sc"},
    "SCA": {"cutoff": "cutoff_sca", "rank": "rank_sca"},
    "ST": {"cutoff": "cutoff_st", "rank": "rank_st"},
}
REQUIRED_COLUMNS = [
    "year",
    "college_code",
    "college_name",
    "district",
    "college_type",
    "branch_code",
    "branch_name",
] + [column for mapping in CATEGORY_COLUMNS.values() for column in mapping.values()]

WARNING_TEXT = (
    "This tool provides a historical comparison based on available TNEA data. "
    "It is not a guaranteed admission prediction or calibrated admission probability. "
    "Cutoff/rank meanings, comparison direction, counselling round, and source "
    "statistic definitions have not been officially verified in this project. "
    "Actual admission depends on counselling rules, seat availability, preferences, "
    "competition, and other factors."
)


@st.cache_data(show_spinner=False)
def load_data() -> pd.DataFrame:
    frame = pd.read_csv(INPUT_PATH)
    missing = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"Dataset is missing required columns: {missing}")
    duplicate_keys = int(frame.duplicated(KEY_COLUMNS).sum())
    if duplicate_keys:
        raise ValueError(f"Dataset contains {duplicate_keys} duplicate primary-key rows")
    return frame


def compare_history(
    frame: pd.DataFrame,
    district: str,
    branch_code: str,
    category: str,
    input_type: str,
    student_value: float,
    years: list[int],
    college_code: int | None = None,
) -> pd.DataFrame:
    district_key = district.strip().casefold()
    branch_key = branch_code.strip().casefold()
    selected = frame[frame["year"].isin(years)].copy()
    if district_key not in {"all", "all districts"}:
        selected = selected[
            selected["district"].astype(str).str.strip().str.casefold().eq(district_key)
        ]
    if branch_key not in {"all", "all courses"}:
        selected = selected[
            selected["branch_code"].astype(str).str.strip().str.casefold().eq(branch_key)
        ]
    if college_code is not None:
        selected = selected[selected["college_code"].eq(college_code)]
    value_column = CATEGORY_COLUMNS[category][input_type]
    rows = []
    for (college_code, exact_branch_code), group in selected.groupby(
        ["college_code", "branch_code"], dropna=False
    ):
        college_names = sorted(group["college_name"].dropna().astype(str).unique())
        branch_names = sorted(group["branch_name"].dropna().astype(str).unique())
        college_type = ", ".join(sorted(group["college_type"].dropna().astype(str).unique()))
        district_names = sorted(group["district"].dropna().astype(str).unique())
        by_year = {}
        meets_by_year = {}
        for year in years:
            year_rows = group[group["year"] == year]
            value = pd.to_numeric(year_rows[value_column], errors="coerce").iloc[0] if len(year_rows) else None
            value = None if pd.isna(value) else float(value)
            by_year[year] = value
            if value is None:
                meets_by_year[year] = None
            elif input_type == "cutoff":
                meets_by_year[year] = bool(student_value >= value)
            else:
                meets_by_year[year] = bool(student_value <= value)
        usable_years = [year for year, value in by_year.items() if value is not None]
        missing_years = [year for year, value in by_year.items() if value is None]
        years_meeting = sum(value is True for value in meets_by_year.values())
        rate = years_meeting / len(usable_years) if usable_years else None
        if not usable_years:
            status = "No comparable records"
        elif len(usable_years) == 1:
            status = "Insufficient historical data"
        elif years_meeting == len(usable_years):
            status = "Historical threshold matched in all usable years"
        elif years_meeting:
            status = "Historical threshold matched in some years"
        else:
            status = "Historical threshold not matched in usable years"
        rows.append(
            {
                "College code": college_code,
                "College name": college_names[0] if college_names else "",
                "District": district_names[0] if district_names else "",
                "College type": college_type,
                "Exact branch code": exact_branch_code,
                "Exact branch name": branch_names[0] if branch_names else "",
                "Years meeting threshold": years_meeting,
                "Usable years": ", ".join(map(str, usable_years)) or "None",
                "Historical match rate": "Unavailable" if rate is None else f"{rate:.2%}",
                "Year-by-year values": "; ".join(
                    f"{year}: {'Missing' if by_year[year] is None else by_year[year]}"
                    for year in years
                ),
                "Data availability notes": (
                    f"Missing years: {', '.join(map(str, missing_years)) or 'None'}; "
                    f"status: {status}; missing values excluded from denominator"
                ),
                "_status": status,
                "_values": by_year,
                "_meets": meets_by_year,
                "_rate": rate,
            }
        )
    return pd.DataFrame(rows)


def render_year_details(results: pd.DataFrame, years: list[int]) -> None:
    st.subheader("Year-by-year comparison")
    for row in results.to_dict("records"):
        title = f"{row['College code']} | {row['Exact branch code']} | {row['_status']}"
        with st.expander(title):
            detail = pd.DataFrame(
                {
                    "Year": years,
                    "Historical value": [row["_values"][year] if row["_values"][year] is not None else "Missing" for year in years],
                    "Threshold met": [
                        "Not comparable" if row["_meets"][year] is None else ("Yes" if row["_meets"][year] else "No")
                        for year in years
                    ],
                }
            )
            st.dataframe(detail, hide_index=True, use_container_width=True)
            st.caption(row["Data availability notes"])


def main() -> None:
    st.set_page_config(page_title="TNEA Historical Comparison", page_icon="🎓", layout="wide")
    st.title("TNEA Historical College Comparison")
    st.caption("Rule-based historical threshold comparison for 2021–2025")
    st.warning(WARNING_TEXT)
    st.markdown("### Status legend")
    st.write(
        "These labels describe historical threshold comparisons only, not admission outcomes: "
        "No comparable records; Insufficient historical data; Historical threshold comparison; "
        "Historical threshold matched in some years; Historical threshold matched in all usable years; "
        "Historical threshold not matched in usable years."
    )

    if not INPUT_PATH.exists():
        st.error(f"Input dataset was not found: {INPUT_PATH}")
        st.stop()
    try:
        frame = load_data()
    except (OSError, ValueError) as error:
        st.error(str(error))
        st.stop()

    st.info(
        "Project working assumptions: cutoff uses student cutoff >= historical cutoff; "
        "rank uses student rank <= historical rank. Official source semantics and direction remain unverified."
    )

    with st.sidebar:
        st.header("Student details")
        districts = sorted(frame["district"].dropna().astype(str).unique().tolist())
        district = st.selectbox("District", ["All Districts", *districts])
        district_frame = frame if district == "All Districts" else frame[frame["district"].eq(district)]
        college_options = (
            district_frame[["college_code", "college_name"]]
            .drop_duplicates()
            .sort_values(["college_name", "college_code"])
        )
        college_labels = {
            f"{row.college_name} | {row.college_code}": int(row.college_code)
            for row in college_options.itertuples(index=False)
        }
        college_label = st.selectbox("College", ["All Colleges", *college_labels])
        college_code = None if college_label == "All Colleges" else college_labels[college_label]
        course_frame = district_frame if college_code is None else district_frame[district_frame["college_code"].eq(college_code)]
        branch_options = (
            course_frame[["branch_code", "branch_name"]]
            .drop_duplicates()
            .sort_values(["branch_code", "branch_name"])
        )
        branch_labels = {
            f"{row.branch_code} | {row.branch_name}": row.branch_code
            for row in branch_options.itertuples(index=False)
        }
        branch_label = st.selectbox("Course/branch", ["All Courses", *branch_labels])
        branch_code = "All Courses" if branch_label == "All Courses" else branch_labels[branch_label]
        category = st.selectbox("Category", CATEGORIES)
        input_type = st.radio(
            "Input type",
            ["cutoff", "rank"],
            horizontal=True,
            help="Cutoff and rank are different input types and use different project working rules.",
        )
        student_value = st.number_input(
            "Student cutoff/rank",
            min_value=0.0,
            value=0.0,
            step=0.01,
            help="Enter a positive value. Zero is invalid input; missing historical values are not zero.",
        )
        available_years = sorted(int(year) for year in frame["year"].unique())
        years = st.multiselect("Historical years", available_years, default=available_years)
        run = st.button("Compare historical records", type="primary", use_container_width=True)

    st.subheader("How this comparison works")
    st.write(
        "The app applies any selected district, college, and exact branch-code filters, then compares the student value with each available historical year. "
        "Cutoff uses student cutoff >= historical cutoff; rank uses student rank <= historical rank. "
        "Missing values are shown as missing and excluded from the usable-year denominator. General searches may return many college-course combinations."
    )

    if not run:
        st.write("Enter the student details in the sidebar and run the comparison.")
        return
    if student_value <= 0:
        st.error("Enter a numeric student value greater than zero.")
        return
    if not years:
        st.error("Select at least one historical year.")
        return

    results = compare_history(
        frame,
        district,
        branch_code,
        category,
        input_type,
        float(student_value),
        years,
        college_code=college_code,
    )
    if results.empty:
        st.warning("No comparable records were found for this exact district, branch code, category, and year selection.")
        return

    st.subheader("Results summary")
    summary_columns = st.columns(6)
    summary_columns[0].metric("College-course combinations", len(results))
    summary_columns[1].metric("Distinct colleges", results["College code"].nunique())
    summary_columns[2].metric("Distinct districts", results["District"].nunique())
    summary_columns[3].metric("Distinct branches", results["Exact branch code"].nunique())
    summary_columns[4].metric("Category", category)
    summary_columns[5].metric("Student value", f"{student_value:g}")
    st.caption(f"Selected historical years: {', '.join(map(str, years))}")

    st.warning(
        "Comparison direction and source cutoff/rank semantics have not been officially verified in this project. "
        "Results are historical threshold comparisons only and must not be interpreted as admission guarantees "
        "or calibrated admission probabilities."
    )
    st.caption(
        "Missing historical values are not treated as zero. They are excluded from the usable-year denominator. "
        "The historical match rate is years meeting threshold divided by usable historical years. "
        "A 100% historical match rate is not an admission guarantee."
    )

    st.subheader("Result controls")
    control_columns = st.columns(2)
    sort_option = control_columns[0].selectbox(
        "Sort results",
        [
            "Historical match rate (high to low)",
            "Historical match rate (low to high)",
            "Usable years (high to low)",
            "College name (A-Z)",
            "District (A-Z)",
            "Course/branch name (A-Z)",
        ],
    )
    minimum_filter = control_columns[1].selectbox(
        "Minimum historical match rate",
        ["All results", "At least 20%", "At least 40%", "At least 60%", "At least 80%", "100%"],
        help="This filters historical comparisons only; it does not indicate admission probability or guarantee.",
    )
    st.caption(f"Results before minimum-rate filtering: {len(results)}")

    minimum_rate = {
        "All results": None,
        "At least 20%": 0.20,
        "At least 40%": 0.40,
        "At least 60%": 0.60,
        "At least 80%": 0.80,
        "100%": 1.00,
    }[minimum_filter]
    displayed_results = results.copy()
    if minimum_rate is not None:
        displayed_results = displayed_results[
            displayed_results["_rate"].notna() & (displayed_results["_rate"] >= minimum_rate)
        ]
    if sort_option == "Historical match rate (high to low)":
        displayed_results = displayed_results.sort_values("_rate", ascending=False, na_position="last")
    elif sort_option == "Historical match rate (low to high)":
        displayed_results = displayed_results.sort_values("_rate", ascending=True, na_position="last")
    elif sort_option == "Usable years (high to low)":
        displayed_results = displayed_results.assign(
            _usable_count=displayed_results["Usable years"].map(lambda value: 0 if value == "None" else len(value.split(", ")))
        ).sort_values("_usable_count", ascending=False)
    elif sort_option == "College name (A-Z)":
        displayed_results = displayed_results.sort_values("College name")
    elif sort_option == "District (A-Z)":
        displayed_results = displayed_results.sort_values("District")
    else:
        displayed_results = displayed_results.sort_values("Exact branch name")

    if displayed_results.empty:
        st.info("No results meet the selected minimum historical match-rate filter. The original result set was not changed.")
        return
    st.caption(f"Displayed results after filtering: {len(displayed_results)}")

    display_columns = [
        "College code",
        "College name",
        "District",
        "College type",
        "Exact branch code",
        "Exact branch name",
        "Years meeting threshold",
        "Usable years",
        "Historical match rate",
        "Year-by-year values",
        "Data availability notes",
    ]
    st.subheader("Historical threshold comparison")
    if len(displayed_results) > 100:
        st.info(
            f"This search returned {len(displayed_results)} displayed college-course combinations. "
            "The table contains the complete result set; expandable year details are shown for smaller result sets to keep the page usable."
        )
    export_columns = {
        "College name": "college_name",
        "College code": "college_code",
        "District": "district",
        "Exact branch name": "branch_name",
        "Exact branch code": "branch_code",
        "Years meeting threshold": "years_meeting_threshold",
        "Usable years": "usable_years",
        "Historical match rate": "historical_match_rate",
        "_status": "status",
        "Data availability notes": "data_availability_notes",
    }
    download_frame = displayed_results[
        [
            "College name",
            "College code",
            "District",
            "Exact branch name",
            "Exact branch code",
            "Years meeting threshold",
            "Usable years",
            "Historical match rate",
            "_status",
            "Data availability notes",
        ]
    ].rename(columns=export_columns)
    st.download_button(
        "Download displayed results (CSV)",
        data=download_frame.to_csv(index=False).encode("utf-8"),
        file_name="tnea_historical_comparison_results.csv",
        mime="text/csv",
        help="Downloads only the currently displayed historical comparison rows; the source dataset is unchanged.",
    )
    st.dataframe(displayed_results[display_columns], hide_index=True, use_container_width=True)
    if len(displayed_results) <= 100:
        render_year_details(displayed_results, years)
    st.caption(
        "Interpretation labels are historical comparison labels only. They are not admission probabilities, guarantees, or safe-college classifications."
    )


if __name__ == "__main__":
    main()
