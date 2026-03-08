import io
from typing import Any

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Reconciliation Form", layout="wide")

TARGET_FIELDS = [
    "Beginning Total",
    "Contributions",
    "Loan Repay Principal",
    "Loan Reap Interest",
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
SKIP_MAPPING_OPTION = "(Not mapped)"

DEFAULT_FTW_MAPPING = {
    "Beginning Total": "Beginning Balance",
    "Contributions": "Contribution",
    "Takeover Contribution": "Contributions",
    "Loan Repay Principal": "Loan Reap Principal",
    "Loan Reap Principal": "Loan Reap Principal",
    "Loan Reap Interest": "Loan Reap Interest",
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
    "Beginning Total": "Beginning Balance",
    "Contributions": "Contributions",
    "Takeover Contribution": "Takeover Contribution",
    "Loan Reap Principal": "Loan Reap Principal",
    "Loan Reap Interest": "Loan Reap Interest",
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
    """Create a form for user to map headers with skip option."""
    st.subheader("Header Mapping")
    st.write("Select matching headers or skip mapping for each line item.")

    mapping = {}
    options_ftw = [NOT_MAPPED] + list(df_ftwilliam.columns)
    options_rk = [NOT_MAPPED] + list(df_recordkeeper.columns)

    for field in TARGET_FIELDS:
        ftw_header = st.selectbox(f"{field} - FTWilliam header", options=options_ftw, key=f"ftw_{field}")
        rk_header = st.selectbox(f"{field} - Recordkeeper header", options=options_rk, key=f"rk_{field}")
        mapping[field] = {
            "FTWilliam Header": ftw_header,
            "Recordkeeper Header": rk_header
        }
    return mapping

def build_reconciliation(
    df_ftwilliam: pd.DataFrame,
    df_recordkeeper: pd.DataFrame,
    mapping: dict,
) -> pd.DataFrame:
    rows = []

    for field in TARGET_FIELDS:
        ftw_col = mapping[field]["FTWilliam Header"]
        rk_col = mapping[field]["Recordkeeper Header"]

        # If either header is NOT_MAPPED, skip comparison
        if ftw_col == NOT_MAPPED or rk_col == NOT_MAPPED:
            ftw_sum = None
            rk_sum = None
        else:
            ftw_sum = sum_column(df_ftwilliam, ftw_col)
            rk_sum = sum_column(df_recordkeeper, rk_col)

        # Debug info
        st.write(f"Processing: {field}")
        st.write(f"FTWilliam column: {ftw_col} sum: {ftw_sum}")
        st.write(f"Recordkeeper column: {rk_col} sum: {rk_sum}")

        rows.append(
            {
                "Line Item": field,
                "FTWilliam Header": ftw_col,
                "Recordkeeper Header": rk_col,
                "FTWilliam": ftw_sum if ftw_sum is not None else "",
                "Recordkeeper": rk_sum if rk_sum is not None else "",
                "Difference (FTW - RK)": (ftw_sum if ftw_sum is not None else 0) - (rk_sum if rk_sum is not None else 0),
            }
        )

    df = pd.DataFrame(rows)
    return df

def sum_column(df: pd.DataFrame, column_name: str) -> float:
    if column_name == NOT_MAPPED:
        return 0.0
    if column_name not in df.columns:
        st.write(f"Warning: Column '{column_name}' not found.")
        return 0.0
    try:
        total = pd.to_numeric(df[column_name], errors='coerce').fillna(0).sum()
        return float(total)
    except Exception as e:
        st.write(f"Error summing column '{column_name}': {e}")
        return 0.0

def main() -> None:
    st.title("FTWilliam vs Recordkeeper Reconciliation")
    st.write(
        "Upload your FTWilliam and Recordkeeper files (.csv or .xlsx). "
        "Then, review or set the header mappings. You can skip mapping columns if needed."
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

            # Show loaded data
            st.subheader("Data from FTWilliam")
            st.dataframe(df_ftwilliam.head(10))
            st.subheader("Data from Recordkeeper")
            st.dataframe(df_recordkeeper.head(10))

            # Header mapping with skip option
            header_mapping = user_header_mapping(df_ftwilliam, df_recordkeeper)

            # Build comparison
            comparison_df = build_reconciliation(df_ftwilliam, df_recordkeeper, header_mapping)

            # Show comparison
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

            # Download option
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
