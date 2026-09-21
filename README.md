# CollegeConnect TNEA

CollegeConnect TNEA is a Streamlit application for exploring historical TNEA
college-course cutoff and rank records. It provides historical comparisons by
district, college, exact branch code, category, and selected year range.

## Setup

Create and activate a Python virtual environment, then install the project
dependencies:

```powershell
python -m pip install -r requirements.txt
```

Run the application from the project root:

```powershell
python -m streamlit run app\stage11_app.py
```

## Project layout

- `app/` contains the Streamlit application.
- `data/raw/` contains original cutoff and rank source datasets.
- `data/cleaned/` contains cleaned and final master datasets.
- `data/integrated/` contains `tnea_integrated_master.csv`, the application's
  read-only input dataset.
- `scripts/` contains collection, integration, audit, comparison, and
  feasibility utilities.
- `backups/` contains application and dataset backups, plus reports retained
  pending review.
- `documentation/` contains project documentation and inventory records.
- `tests/` contains verification and API utility scripts.
- `exports/` is reserved for generated, user-requested exports.

## Historical comparison

The application compares a supplied student value with recorded historical
values for the selected category and exact college-course combination:

- Cutoff comparison: `student cutoff >= historical cutoff`
- Rank comparison: `student rank <= historical rank`
- Historical match rate: `years meeting the threshold / usable historical years`

Missing historical values remain missing and are excluded from the match-rate
denominator. Cutoff and rank are separate measures and are not interchangeable.

## Important limitations

Results are historical comparisons, not a guarantee of admission or an actual
admission probability. The dataset does not include confirmed student-level
admission outcomes, counselling preferences, seat availability, or verified
round-level semantics. A future AI/ML forecast would require an explicitly
approved target, verified source definitions, prediction-time features, and
validated outcome data.
