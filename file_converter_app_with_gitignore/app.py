import io
from typing import Any

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Reconciliation Form", layout="wide")

TARGET_FIELDS = [
    "Beginning Total",
    "Contributions",
    "Loan Repayments",
    "Loan Repay Principal",
    "Loan Repay Interest",
    "Loan Issue",
    "Withdrawals",
    "Fund Transfers",
    "Forfeitures",
    "Internal Transfers",
    "Fees",
    "TPA Fees",
    "Misc",
    "Dividends Earnings",
    "Gain/Loss",
]

NOT_MAPPED = "(Not mapped)"

DEFAULT_FTW_MAPPING = {
    "Beginning Total": "Beginning Balance",
    "Contributions": "Contribution",
    "Takeover Contribution": "Contributions",
    "Loan Repayments": "Loan Repayments",
    "Loan Repay Principal": "Loan Reap Principal",
    "Loan Repay Interest": "Loan Reap Interest",
    "Loan Issue": "Loan Issue",
    "Withdrawals": "Distributions",
    "Fund Transfers": "Transfers",
    "Forfeitures": "Forfeiture",
    "Internal Transfers": "Transfers",
    "Fees": "Fees",
    "TPA Fees": "TPA Fees",
    "Misc": "Other",
    "Dividends Earnings": "Earnings",
    "Gain/Loss": "Earnings",
}

DEFAULT_RK_MAPPING = {
    "Beginning Total": "Beginning Balance",
    "Contributions": "Contributions",
    "Takeover Contribution": "Takeover Contribution",
    "Loan Repayments": "Loan Repayments",
    "Loan Repay Principal": "Loan Reap Principal",
    "Loan Repay Interest": "Loan Reap Interest",
    "Loan Issue": "Loan Issue",
    "Withdrawals": "Withdrawals",
    "Fund Transfers": "Fund Transfers",
    "Forfeitures": "Forfeitures",
    "Internal Transfers": "Internal Transfers",
    "Fees": "Fees",
    "TPA Fees": "TPA Fees",
    "Misc": "Misc",
    "Dividends Earnings": "Dividends Earnings",
    "Gain/Loss": "Gain/Loss",
}

def _clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Remove empty helper columns and normalize header spacing."""
    cleaned = df.dropna(axis=1, how="all").copy()
    cleaned.columns = [str(col).strip() for col in cleaned.columns]
    return cleaned

def _read_csv_with_fallbacks(file_bytes: bytes) -> pd.DataFrame:
    """Read CSV content using delimiter fallbacks for vendor exports."""
    csv_text = file_bytes.decode("utf-8-sig", errors="replace")
    parse_attempts = [
        {"sep": None, "engine": "python"},
        {"sep": "\t", "engine": "python"},
        {"sep": ",", "engine": "python"},
        {"sep": "|", "engine": "python"},
        {"sep": ";", "engine": "python"},
    ]

    best_df = None
    best_column_count = 0

    for opts in parse_attempts:
        try:
            candidate = pd.read_csv(io.StringIO(csv_text), **opts)
            column_count = len(candidate.columns)
            if column_count > best_column_count:
                best_df = candidate
                best_column_count = column_count
        except Exception:
            continue

    if best_df is None:
        raise ValueError("Could not parse CSV. Please verify the file format.")

    return _clean_dataframe(best_df)

def load_uploaded_file(uploaded_file: Any) -> pd.DataFrame:
    """Load CSV or XLSX file into a DataFrame with debug info."""
    file_bytes = uploaded_file.getvalue()

    st.write(f"Uploading file: {uploaded_file.name}")
    st.write("First 500 bytes of file:", file_bytes[:500])

    if uploaded_file.name.lower().endswith(".csv"):
        st.write("Attempting to parse as CSV.")
        return _read_csv_with_fallbacks(file_bytes)
    else:
        st.write("Attempting to parse as Excel.")
        try:
            df = pd.read_excel(io.BytesIO(file_bytes))
            return _clean_dataframe(df)
        except Exception as e:
            st.write(f"Error reading Excel: {e}")
            raise

def sum_all_numeric(df: pd.DataFrame) -> float:
    """Sum all numeric values in the DataFrame."""
    total = float(pd.to_numeric(df.select_dtypes(include='number').sum().sum(), errors='coerce'))
    return total

def add_total_row(df: pd.DataFrame, label: str) -> pd.DataFrame:
    """Add a total row for the DataFrame with the sum of all numeric values."""
    total_value = sum_all_numeric(df)
    total_row = {col: "" for col in df.columns}
    total_row[list(df.columns)[0]] = label
    total_row["Total"] = total_value  # add a 'Total' column if exists, or you can customize
    # Append the total row
    return pd.concat([df, pd.DataFrame([total_row])], ignore_index=True)

def create_mapping_table(df_ftwilliam: pd.DataFrame, df_recordkeeper: pd.DataFrame) -> pd.DataFrame:
    """Build default mapping table for line items."""
    ftw_columns = set(df_ftwilliam.columns)
    rk_columns = set(df_recordkeeper.columns)

    rows = []
    for field in TARGET_FIELDS:
        ftw_default = DEFAULT_FTW_MAPPING.get(field, NOT_MAPPED)
        rk_default = DEFAULT_RK_MAPPING.get(field, NOT_MAPPED)

        rows.append(
            {
                "Line Item": field,
                "FTWilliam Header": ftw_default if ftw_default in ftw_columns else NOT_MAPPED,
                "Recordkeeper Header": rk_default if rk_default in rk_columns else NOT_MAPPED,
            }
        )

    return pd.DataFrame(rows)

def build_reconciliation(
    df_ftwilliam: pd.DataFrame,
    df_recordkeeper: pd.DataFrame,
    mapping_df: pd.DataFrame,
) -> pd.DataFrame:
    """Build total lines for each file and compare for reconciliation."""
    # Sum all numeric in FTWilliam
    total_ftw_value = sum_all_numeric(df_ftwilliam)
    # Sum all numeric in Recordkeeper
    total_rk_value = sum_all_numeric(df_recordkeeper)

    # Create total lines
    total_ftw_line = {
        "Line Item": "TOTAL FTWilliam",
        "FTWilliam": total_ftw_value,
        "Recordkeeper": "",
        "Difference (FTW - RK)": ""
    }

    total_rk_line = {
        "Line Item": "TOTAL Recordkeeper",
        "FTWilliam": "",
        "Recordkeeper": total_rk_value,
        "Difference (FTW - RK)": ""
    }

    # Now compare totals
    diff = total_ftw_value - total_rk_value

    # Prepare the reconciliation DataFrame
    rows = []

    # For each mapping, sum specific columns
    for _, mapping in mapping_df.iterrows():
        field = mapping["Line Item"]
        ftw_col = mapping["FTWilliam Header"]
        rk_col = mapping["Recordkeeper Header"]

        # Debug info
        st.write(f"Processing line item: {field}")
        st.write(f"FTWilliam column: {ftw_col}")
        st.write(f"Recordkeeper column: {rk_col}")

        ftw_sum = sum_column(df_ftwilliam, ftw_col)
        rk_sum = sum_column(df_recordkeeper, rk_col)

        # Debug sums
        st.write(f"Sum FTWilliam for {ftw_col}: {ftw_sum}")
        st.write(f"Sum Recordkeeper for {rk_col}: {rk_sum}")

        rows.append(
            {
                "Line Item": field,
                "FTWilliam Header": ftw_col,
                "Recordkeeper Header": rk_col,
                "FTWilliam": ftw_sum,
                "Recordkeeper": rk_sum,
                "Difference (FTW - RK)": ftw_sum - rk_sum,
            }
        )

    reconciliation = pd.DataFrame(rows)

    # Add total lines
    totals = {
        "Line Item": "TOTAL",
        "FTWilliam Header": "",
        "Recordkeeper Header": "",
        "FTWilliam": total_ftw_value,
        "Recordkeeper": total_rk_value,
        "Difference (FTW - RK)": diff,
    }

    return pd.concat([reconciliation, pd.DataFrame([totals])], ignore_index=True)

def sum_column(df: pd.DataFrame, column_name: str) -> float:
    """Sum a specific column in a DataFrame with debug info."""
    if column_name == NOT_MAPPED:
        return 0.0
    if column_name not in df.columns:
        st.write(f"Warning: Column '{column_name}' not found in DataFrame columns: {list(df.columns)}")
        return 0.0
    try:
        total = float(pd.to_numeric(df[column_name], errors='coerce').fillna(0).sum())
        return total
    except Exception as e:
        st.write(f"Error summing column '{column_name}': {e}")
        return 0.0

def main() -> None:
    st.title("FTWilliam vs Recordkeeper Reconciliation")
    st.write(
        "Upload one FTWilliam file and one Recordkeeper file (.csv or .xlsx). "
        "Review or adjust header mappings, then generate the reconciliation."
    )

    col1, col2 = st.columns(2)

    with col1:
        ftwilliam_file = st.file_uploader(
            "Upload FTWilliam file (.csv or .xlsx)", type=["csv", "xlsx"], key="ftw"
        )

    with col2:
        recordkeeper_file = st.file_uploader(
            "Upload Recordkeeper file (.csv or .xlsx)", type=["csv", "xlsx"], key="rk"
        )

    if ftwilliam_file and recordkeeper_file:
        try:
            df_ftwilliam = load_uploaded_file(ftwilliam_file)
            df_recordkeeper = load_uploaded_file(recordkeeper_file)

            # Debug: show loaded data columns
            st.write("FTWilliam columns:", list(df_ftwilliam.columns))
            st.write("Recordkeeper columns:", list(df_recordkeeper.columns))

            # Create mapping table (not used directly here but for reference)
            mapping_df = create_mapping_table(df_ftwilliam, df_recordkeeper)

            # Build reconciliation with total lines
            reconciliation_df = build_reconciliation(df_ftwilliam, df_recordkeeper, mapping_df)

            # Show results
            st.subheader("Reconciliation Results")
            st.dataframe(
                reconciliation_df.style.format(
                    {
                        "FTWilliam": "{:,.2f}",
                        "Recordkeeper": "{:,.2f}",
                        "Difference (FTW - RK)": "{:,.2f}",
                    }
                ),
                use_container_width=True,
            )

            # Download button
            st.download_button(
                "Download Reconciliation CSV",
                reconciliation_df.to_csv(index=False),
                "reconciliation.csv",
                "text/csv"
            )

            # Show some preview of uploaded data
            with st.expander("Preview FTWilliam data"):
                st.dataframe(df_ftwilliam.head(25))
            with st.expander("Preview Recordkeeper data"):
                st.dataframe(df_recordkeeper.head(25))
        except Exception as e:
            st.error(f"Error during processing: {e}")

if __name__ == "__main__":
    main()
