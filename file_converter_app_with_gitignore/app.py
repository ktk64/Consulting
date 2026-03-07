import pandas as pd
import streamlit as st

st.set_page_config(page_title="Reconciliation Form", layout="wide")
st.title("FTWilliam vs Recordkeeper Reconciliation")
st.write(
    "Upload one FTWilliam file and one Recordkeeper file (.csv or .xlsx). "
    "The app will extract key reconciliation fields and calculate differences."
)

TARGET_FIELDS = [
    "Beginning Total",
    "Contributions",
    "Takeover Contribution",
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


def load_uploaded_file(uploaded_file) -> pd.DataFrame:
    """Load a CSV or Excel file into a DataFrame."""
    file_name = uploaded_file.name.lower()
    if file_name.endswith(".csv"):
        try:
            return pd.read_csv(uploaded_file)
        except UnicodeDecodeError:
            uploaded_file.seek(0)
            return pd.read_csv(uploaded_file, encoding="latin1")
    return pd.read_excel(uploaded_file)


def normalize_label(value: str) -> str:
    """Normalize labels for fuzzy column/row matching."""
    return "".join(ch.lower() for ch in str(value) if ch.isalnum())


def find_field_value(df: pd.DataFrame, field_name: str) -> float:
    """Find a field value by checking both columns and first-column row labels."""
    normalized_target = normalize_label(field_name)

    # 1) Direct column match
    for column in df.columns:
        if normalize_label(column) == normalized_target:
            series = pd.to_numeric(df[column], errors="coerce").dropna()
            return float(series.sum()) if not series.empty else 0.0

    # 2) Row-label match (first column as label, second column as amount)
    if len(df.columns) >= 2:
        label_col = df.columns[0]
        value_col = df.columns[1]
        pair_df = df[[label_col, value_col]].dropna(subset=[label_col])
        for _, row in pair_df.iterrows():
            if normalize_label(row[label_col]) == normalized_target:
                value = pd.to_numeric(pd.Series([row[value_col]]), errors="coerce").iloc[0]
                return float(value) if pd.notna(value) else 0.0

    return 0.0


def build_reconciliation(df_ftwilliam: pd.DataFrame, df_recordkeeper: pd.DataFrame) -> pd.DataFrame:
    """Construct reconciliation output from two input DataFrames."""
    rows = []
    for field in TARGET_FIELDS:
        ftw_value = find_field_value(df_ftwilliam, field)
        rk_value = find_field_value(df_recordkeeper, field)
        rows.append(
            {
                "Line Item": field,
                "FTWilliam": ftw_value,
                "Recordkeeper": rk_value,
                "Difference (FTW - RK)": ftw_value - rk_value,
            }
        )

    reconciliation = pd.DataFrame(rows)
    totals = {
        "Line Item": "TOTAL",
        "FTWilliam": reconciliation["FTWilliam"].sum(),
        "Recordkeeper": reconciliation["Recordkeeper"].sum(),
        "Difference (FTW - RK)": reconciliation["Difference (FTW - RK)"].sum(),
    }
    return pd.concat([reconciliation, pd.DataFrame([totals])], ignore_index=True)


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

        reconciliation_df = build_reconciliation(df_ftwilliam, df_recordkeeper)

        st.subheader("Reconciliation Form")
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

        st.download_button(
            "Download Reconciliation CSV",
            reconciliation_df.to_csv(index=False),
            "reconciliation_form.csv",
            "text/csv",
        )

        with st.expander("Preview uploaded data"):
            st.markdown("**FTWilliam file preview**")
            st.dataframe(df_ftwilliam.head(25), use_container_width=True)
            st.markdown("**Recordkeeper file preview**")
            st.dataframe(df_recordkeeper.head(25), use_container_width=True)

    except Exception as exc:
        st.error(f"Unable to process one or both files: {exc}")
else:
    st.info("Upload both files to generate the reconciliation form.")
