+import pandas as pd
+import streamlit as st
+
+st.set_page_config(page_title="Reconciliation Form", layout="wide")
+st.title("FTWilliam vs Recordkeeper Reconciliation")
+st.write(
+    "Upload one FTWilliam file and one Recordkeeper file (.csv or .xlsx). "
+    "Review or adjust header mappings, then generate the reconciliation form."
+)
+
+TARGET_FIELDS = [
+    "Beginning Total",
+    "Contributions",
+    "Takeover Contribution",
+    "Loan Repayments",
+    "Loan Repay Principal",
+    "Loan Repay Interest",
+    "Loan Issue",
+    "Withdrawals",
+    "Fund Transfers",
+    "Forfeitures",
+    "Internal Transfers",
+    "Fees",
+    "TPA Fees",
+    "Misc",
+    "Dividends Earnings",
+    "Gain/Loss",
+]
+
+NOT_MAPPED = "(Not mapped)"
+
+DEFAULT_FTW_MAPPING = {
+    "Beginning Total": "Beginning Balance",
+    "Contributions": "Contribution",
+    "Takeover Contribution": NOT_MAPPED,
+    "Loan Repayments": NOT_MAPPED,
+    "Loan Repay Principal": NOT_MAPPED,
+    "Loan Repay Interest": NOT_MAPPED,
+    "Loan Issue": NOT_MAPPED,
+    "Withdrawals": "Distributions",
+    "Fund Transfers": "Transfers",
+    "Forfeitures": "Forfeiture",
+    "Internal Transfers": "Transfers",
+    "Fees": "Fees",
+    "TPA Fees": NOT_MAPPED,
+    "Misc": "Other",
+    "Dividends Earnings": "Earnings",
+    "Gain/Loss": "Earnings",
+}
+
+DEFAULT_RK_MAPPING = {
+    "Beginning Total": "Beginning Balance",
+    "Contributions": "Contributions",
+    "Takeover Contribution": "Takeover Contribution",
+    "Loan Repayments": "Loan Repayments",
+    "Loan Repay Principal": "Loan Repay Principal",
+    "Loan Repay Interest": "Loan Repay Interest",
+    "Loan Issue": "Loan Issue",
+    "Withdrawals": "Withdrawals",
+    "Fund Transfers": "Fund Transfers",
+    "Forfeitures": "Forfeitures",
+    "Internal Transfers": "Internal Transfers",
+    "Fees": "Fees",
+    "TPA Fees": "TPA Fees",
+    "Misc": "Misc",
+    "Dividends Earnings": "Dividends Earnings",
+    "Gain/Loss": "Gain/Loss",
+}
+
+
+def _clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
+    """Remove empty helper columns and normalize header spacing."""
+    df = df.dropna(axis=1, how="all")
+    df.columns = [str(col).strip() for col in df.columns]
+    return df
+
+
+def _read_csv_with_fallbacks(file_bytes: bytes) -> pd.DataFrame:
+    """Read CSV content using delimiter fallbacks for vendor exports."""
+    csv_text = file_bytes.decode("utf-8-sig", errors="replace")
+
+    parse_attempts = [
+        {"sep": None, "engine": "python"},
+        {"sep": "	", "engine": "python"},
+        {"sep": ",", "engine": "python"},
+        {"sep": "|", "engine": "python"},
+        {"sep": ";", "engine": "python"},
+    ]
+
+    best_df = None
+    best_column_count = 0
+
+    for opts in parse_attempts:
+        try:
+            candidate = pd.read_csv(io.StringIO(csv_text), **opts)
+            column_count = len(candidate.columns)
+            if column_count > best_column_count:
+                best_df = candidate
+                best_column_count = column_count
+        except Exception:
+            continue
+
+    if best_df is None:
+        raise ValueError("Could not parse CSV. Please verify the file format.")
+
+    return _clean_dataframe(best_df)
+
+
+def load_uploaded_file(uploaded_file: st.runtime.uploaded_file_manager.UploadedFile) -> pd.DataFrame:
+    """Load CSV or XLSX file into a DataFrame."""
+    file_bytes = uploaded_file.getvalue()
+
+    if uploaded_file.name.lower().endswith(".csv"):
+        return _read_csv_with_fallbacks(file_bytes)
+
+    df = pd.read_excel(io.BytesIO(file_bytes))
+    return _clean_dataframe(df)
+
+
+def sum_column(df: pd.DataFrame, column_name: str) -> float:
+    """Safely sum a numeric column and return float."""
+    if column_name == NOT_MAPPED or column_name not in df.columns:
+        return 0.0
+    return float(pd.to_numeric(df[column_name], errors="coerce").fillna(0).sum())
+
+
+def create_mapping_table(df_ftwilliam: pd.DataFrame, df_recordkeeper: pd.DataFrame) -> pd.DataFrame:
+    """Build default mapping table for line items."""
+    ftw_columns = set(df_ftwilliam.columns)
+    rk_columns = set(df_recordkeeper.columns)
+
+    rows = []
+    for field in TARGET_FIELDS:
+        ftw_default = DEFAULT_FTW_MAPPING.get(field, NOT_MAPPED)
+        rk_default = DEFAULT_RK_MAPPING.get(field, NOT_MAPPED)
+
+        rows.append(
+            {
+                "Line Item": field,
+                "FTWilliam Header": ftw_default if ftw_default in ftw_columns else NOT_MAPPED,
+                "Recordkeeper Header": rk_default if rk_default in rk_columns else NOT_MAPPED,
+            }
+        )
+
+    return pd.DataFrame(rows)
+
+
+def build_reconciliation(
+    df_ftwilliam: pd.DataFrame,
+    df_recordkeeper: pd.DataFrame,
+    mapping_df: pd.DataFrame,
+) -> pd.DataFrame:
+    """Construct reconciliation output from mapping table and two input DataFrames."""
+    rows = []
+    for _, mapping in mapping_df.iterrows():
+        field = mapping["Line Item"]
+        ftw_column = mapping["FTWilliam Header"]
+        rk_column = mapping["Recordkeeper Header"]
+
+        ftw_value = sum_column(df_ftwilliam, ftw_column)
+        rk_value = sum_column(df_recordkeeper, rk_column)
+        rows.append(
+            {
+                "Line Item": field,
+                "FTWilliam Header": ftw_column,
+                "Recordkeeper Header": rk_column,
+                "FTWilliam": ftw_value,
+                "Recordkeeper": rk_value,
+                "Difference (FTW - RK)": ftw_value - rk_value,
+            }
+        )
+
+    reconciliation = pd.DataFrame(rows)
+    totals = {
+        "Line Item": "TOTAL",
+        "FTWilliam Header": "",
+        "Recordkeeper Header": "",
+        "FTWilliam": reconciliation["FTWilliam"].sum(),
+        "Recordkeeper": reconciliation["Recordkeeper"].sum(),
+        "Difference (FTW - RK)": reconciliation["Difference (FTW - RK)"].sum(),
+    }
+    return pd.concat([reconciliation, pd.DataFrame([totals])], ignore_index=True)
+
+
+col1, col2 = st.columns(2)
+
+with col1:
+    ftwilliam_file = st.file_uploader(
+        "Upload FTWilliam file (.csv or .xlsx)", type=["csv", "xlsx"], key="ftw"
+    )
+
+with col2:
+    recordkeeper_file = st.file_uploader(
+        "Upload Recordkeeper file (.csv or .xlsx)", type=["csv", "xlsx"], key="rk"
+    )
+
+if ftwilliam_file and recordkeeper_file:
+    try:
+        df_ftwilliam = load_uploaded_file(ftwilliam_file)
+        df_recordkeeper = load_uploaded_file(recordkeeper_file)
+
+        mapping_df = create_mapping_table(df_ftwilliam, df_recordkeeper)
+
+        st.subheader("Header Mapping")
+        st.caption(
+            "Verify which FTWilliam and Recordkeeper headers map to each reconciliation line item."
+        )
+
+        ftw_options = [NOT_MAPPED] + list(df_ftwilliam.columns)
+        rk_options = [NOT_MAPPED] + list(df_recordkeeper.columns)
 
-st.title("File Converter App")
+        edited_mapping = st.data_editor(
+            mapping_df,
+            use_container_width=True,
+            hide_index=True,
+            disabled=["Line Item"],
+            column_config={
+                "FTWilliam Header": st.column_config.SelectboxColumn(
+                    "FTWilliam Header", options=ftw_options, required=True
+                ),
+                "Recordkeeper Header": st.column_config.SelectboxColumn(
+                    "Recordkeeper Header", options=rk_options, required=True
+                ),
+            },
+            key="mapping_editor",
+        )
 
-uploaded_file = st.file_uploader("Drop a file here", type=["csv","xlsx","txt"])
+        reconciliation_df = build_reconciliation(df_ftwilliam, df_recordkeeper, edited_mapping)
 
-if uploaded_file:
-    if uploaded_file.name.endswith(".csv"):
-        df = pd.read_csv(uploaded_file)
-    elif uploaded_file.name.endswith(".xlsx"):
-        df = pd.read_excel(uploaded_file)
-    else:
-        df = pd.read_csv(uploaded_file, sep="\t")
+        st.subheader("Reconciliation Form")
+        st.dataframe(
+            reconciliation_df.style.format(
+                {
+                    "FTWilliam": "{:,.2f}",
+                    "Recordkeeper": "{:,.2f}",
+                    "Difference (FTW - RK)": "{:,.2f}",
+                }
+            ),
+            use_container_width=True,
+        )
 
-    st.subheader("Preview")
-    st.dataframe(df)
+        st.download_button(
+            "Download Reconciliation CSV",
+            reconciliation_df.to_csv(index=False),
+            "reconciliation_form.csv",
+            "text/csv",
+        )
 
-    st.subheader("Converted Output")
-    st.dataframe(df)
+        with st.expander("Preview uploaded data"):
+            st.markdown("**FTWilliam file preview**")
+            st.dataframe(df_ftwilliam.head(25), use_container_width=True)
+            st.markdown("**Recordkeeper file preview**")
+            st.dataframe(df_recordkeeper.head(25), use_container_width=True)
 
-    st.download_button(
-        "Download CSV",
-        df.to_csv(index=False),
-        "converted.csv",
-        "text/csv"
-    )
\ No newline at end of file
+    except Exception as exc:
+        st.error(f"Unable to process one or both files: {exc}")
+else:
+    st.info("Upload both files to configure mapping and generate the reconciliation form.")

