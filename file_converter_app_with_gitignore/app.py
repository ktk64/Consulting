import io
from typing import Any

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Reconciliation Form", layout="wide")

TARGET_FIELDS = [
    "Beginning Balance",
    "Contributions",
    "Loan Principal",
    "Loan Interest",
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
    "Beginning Balance": "Beginning Balance",
    "Contributions": "Contribution",
    "Loan Principal": "Loan Principal",
    "Loan Interest": "Loan Interest",
    "Loan Issue": "Loan Issue",
    "Withdrawals": "Distributions",
    "Fund Transfers": "Transfers",
    "Forfeitures": "Forfeiture",
    "Internal Transfers": "Transfers",
    "Fees": "Fees",
    "TPA Fees": "TPA Fees",
    "Misc": "Other",
    "Dividends Earnings": "Dividends Earnings",
    "Gain/Loss": "Earnings",
}

DEFAULT_RK_MAPPING = {
    "Beginning Balance": "Beginning Balance",
    "Contributions": "Contributions",
    "Loan Principal": "Loan Principal",
    "Loan Interest": "Loan Interest",
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
    cleaned = df.dropna(axis=1, how="all").copy()
    cleaned.columns = [str(col).strip() for col in cleaned.columns]
    return cleaned

def _read_csv_with_fallbacks(file_bytes: bytes) -> pd.DataFrame:
    csv_text = file_bytes.decode("utf-8-sig", errors="replace")
    try:
        df = pd.read_csv(io.StringIO(csv_text), thousands=",")
        return _clean_dataframe(df)
    except Exception:
        df = pd.read_csv(io.StringIO(csv_text))
        return _clean_dataframe(df)

def load_uploaded_file(uploaded_file: Any) -> pd.DataFrame:
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

def user_header_mapping(df_ftwilliam, df_recordkeeper):
    """Create a form for user to map headers with multiselect for multiple columns."""
    st.subheader("Header Mapping")
    st.write("Select multiple columns for each line item, or choose '(Not mapped)' to skip.")

    options_ftw = [NOT_MAPPED] + list(df_ftwilliam.columns)
    options_rk = [NOT_MAPPED] + list(df_recordkeeper.columns)

    mapping = {}
    for field in TARGET_FIELDS:
        ftw_headers = st.multiselect(f"{field} - FTWilliam columns", options=options_ftw, key=f"ftw_{field}")
        rk_headers = st.multiselect(f"{field} - Recordkeeper columns", options=options_rk, key=f"rk_{field}")
        mapping[field] = {
            "FTWilliam Headers": ftw_headers,
            "Recordkeeper Headers": rk_headers
        }
    return mapping

def sum_columns(df: pd.DataFrame, columns: list) -> float:
    """Sum multiple columns."""
    total = 0.0
    for col in columns:
        if col != NOT_MAPPED and col in df.columns:
            total += pd.to_numeric(df[col], errors='coerce').fillna(0).sum()
    return float(total)

def build_reconciliation(df_ftwilliam, df_recordkeeper, mapping):
    rows = []

    for field in TARGET_FIELDS:
        ftw_cols = mapping[field]["FTWilliam Headers"]
        rk_cols = mapping[field]["Recordkeeper Headers"]
        if not ftw_cols:
            ftw_cols = [NOT_MAPPED]
        if not rk_cols:
            rk_cols = [NOT_MAPPED]

        if NOT_MAPPED in ftw_cols:
            ftw_sum = None
        else:
            ftw_sum = sum_columns(df_ftwilliam, ftw_cols)

        if NOT_MAPPED in rk_cols:
            rk_sum = None
        else:
            rk_sum = sum_columns(df_recordkeeper, rk_cols)

        # Debug info
        st.write(f"Processing: {field}")
        st.write(f"FTWilliam columns: {ftw_cols} sum: {ftw_sum}")
        st.write(f"Recordkeeper columns: {rk_cols} sum: {rk_sum}")

        rows.append(
            {
                "Line Item": field,
                "FTWilliam Header": ", ".join(ftw_cols) if ftw_cols != [NOT_MAPPED] else NOT_MAPPED,
                "Recordkeeper Header": ", ".join(rk_cols) if rk_cols != [NOT_MAPPED] else NOT_MAPPED,
                "FTWilliam": ftw_sum if ftw_sum is not None else "",
                "Recordkeeper": rk_sum if rk_sum is not None else "",
                "Difference (FTW - RK)": (ftw_sum if ftw_sum is not None else 0) - (rk_sum if rk_sum is not None else 0),
            }
        )

    df = pd.DataFrame(rows)
    return df

# Main app
def main():
    st.title("FTWilliam vs Recordkeeper Reconciliation")
    st.write(
        "Upload your FTWilliam and Recordkeeper files (.csv or .xlsx). "
        "Set the header mappings. When ready, click 'Run Comparison' to see results."
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

    # After files are uploaded, show header mapping
    if ftwilliam_file and recordkeeper_file:
        try:
            df_ftwilliam = load_uploaded_file(ftwilliam_file)
            df_recordkeeper = load_uploaded_file(recordkeeper_file)

            # Show first rows for verification
            st.subheader("Data from FTWilliam")
            st.dataframe(df_ftwilliam.head(10))
            st.subheader("Data from Recordkeeper")
            st.dataframe(df_recordkeeper.head(10))

            # Header mapping
            mapping = user_header_mapping(df_ftwilliam, df_recordkeeper)

            # Only run if user clicks button
            if st.button("Run Comparison"):
                # Generate comparison DataFrame
                comparison_df = build_reconciliation(df_ftwilliam, df_recordkeeper, mapping)

                # Convert columns explicitly to numeric to avoid string formatting errors
                comparison_df["FTWilliam"] = pd.to_numeric(comparison_df["FTWilliam"], errors='coerce').fillna(0.0)
                comparison_df["Recordkeeper"] = pd.to_numeric(comparison_df["Recordkeeper"], errors='coerce').fillna(0.0)
                comparison_df["Difference (FTW - RK)"] = pd.to_numeric(comparison_df["Difference (FTW - RK)"], errors='coerce').fillna(0.0)

                # Show the formatted table
                st.subheader("Comparison Results")
                st.dataframe(
                    comparison_df.style.format(
                        {
                            "FTWilliam": "{:,.2f}",
                            "Recordkeeper": "{:,.2f}",
                            "Difference (FTW - RK)": "{:,.2f}"
                        }
                    ),
                    use_container_width=True
                )

                # Download link
                st.download_button(
                    "Download CSV",
                    comparison_df.to_csv(index=False),
                    "comparison.csv",
                    "text/csv"
                )

        except Exception as e:
            st.error(f"Error during processing: {e}")

if __name__ == "__main__":
    main()
