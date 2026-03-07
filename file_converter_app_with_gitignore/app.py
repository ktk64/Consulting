 (cd "$(git rev-parse --show-toplevel)" && git apply --3way <<'EOF' 
diff --git a/file_converter_app_with_gitignore/README.md b/file_converter_app_with_gitignore/README.md
index 486e1b5af1f865c0bc31630c273c7241275e0b5e..7d787344c3a2d7cb8f0baa18f883b7dffb8b8bf5 100644
--- a/file_converter_app_with_gitignore/README.md
+++ b/file_converter_app_with_gitignore/README.md
@@ -1,8 +1,33 @@
-# File Converter App
+# Reconciliation Form App
 
-Simple drag-and-drop app that reads CSV, Excel, or TXT files and converts them to a target format.
+Streamlit app to compare FTWilliam and Recordkeeper files (`.csv` or `.xlsx`) and generate a reconciliation form.
+
+## What it does
+
+- Accepts one FTWilliam file and one Recordkeeper file.
+- Pulls these line items from both files:
+  - Beginning Total
+  - Contributions
+  - Takeover Contribution
+  - Loan Repayments
+  - Loan Repay Principal
+  - Loan Repay Interest
+  - Loan Issue
+  - Withdrawals
+  - Fund Transfers
+  - Forfeitures
+  - Internal Transfers
+  - Fees
+  - TPA Fees
+  - Misc
+  - Dividends Earnings
+  - Gain/Loss
+- Displays FTWilliam value, Recordkeeper value, and difference (`FTW - RK`) for each line item.
+- Adds a total row and supports CSV download of the reconciliation form.
 
 ## Run locally
 
+```bash
 pip install -r requirements.txt
-streamlit run app.py
\ No newline at end of file
+streamlit run app.py
+```
diff --git a/file_converter_app_with_gitignore/app.py b/file_converter_app_with_gitignore/app.py
index 862c51244dde370c137198cc0fd97b239b447cb9..6a26cb8520208582e1bc4d2a3fab757bee3350f6 100644
--- a/file_converter_app_with_gitignore/app.py
+++ b/file_converter_app_with_gitignore/app.py
@@ -1,27 +1,137 @@
-import streamlit as st
 import pandas as pd
+import streamlit as st
+
+st.set_page_config(page_title="Reconciliation Form", layout="wide")
+st.title("FTWilliam vs Recordkeeper Reconciliation")
+st.write(
+    "Upload one FTWilliam file and one Recordkeeper file (.csv or .xlsx). "
+    "The app will extract key reconciliation fields and calculate differences."
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
+
+def load_uploaded_file(uploaded_file: st.runtime.uploaded_file_manager.UploadedFile) -> pd.DataFrame:
+    """Load CSV or XLSX file into a DataFrame."""
+    if uploaded_file.name.lower().endswith(".csv"):
+        return pd.read_csv(uploaded_file)
+    return pd.read_excel(uploaded_file)
+
+
+def normalize_label(value: str) -> str:
+    """Normalize labels for fuzzy column/row matching."""
+    return "".join(ch.lower() for ch in str(value) if ch.isalnum())
+
+
+def find_field_value(df: pd.DataFrame, field_name: str) -> float:
+    """Find a field value by checking both columns and first-column row labels."""
+    normalized_target = normalize_label(field_name)
+
+    # 1) Direct column match
+    for column in df.columns:
+        if normalize_label(column) == normalized_target:
+            series = pd.to_numeric(df[column], errors="coerce").dropna()
+            return float(series.sum()) if not series.empty else 0.0
+
+    # 2) Row-label match (first column as label, second column as amount)
+    if len(df.columns) >= 2:
+        label_col = df.columns[0]
+        value_col = df.columns[1]
+        for _, row in df[[label_col, value_col]].dropna(subset=[label_col]).iterrows():
+            if normalize_label(row[label_col]) == normalized_target:
+                value = pd.to_numeric(pd.Series([row[value_col]]), errors="coerce").iloc[0]
+                return float(value) if pd.notna(value) else 0.0
+
+    return 0.0
+
+
+def build_reconciliation(df_ftwilliam: pd.DataFrame, df_recordkeeper: pd.DataFrame) -> pd.DataFrame:
+    """Construct reconciliation output from two input DataFrames."""
+    rows = []
+    for field in TARGET_FIELDS:
+        ftw_value = find_field_value(df_ftwilliam, field)
+        rk_value = find_field_value(df_recordkeeper, field)
+        rows.append(
+            {
+                "Line Item": field,
+                "FTWilliam": ftw_value,
+                "Recordkeeper": rk_value,
+                "Difference (FTW - RK)": ftw_value - rk_value,
+            }
+        )
+
+    reconciliation = pd.DataFrame(rows)
+    totals = {
+        "Line Item": "TOTAL",
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
 
-st.title("File Converter App")
+if ftwilliam_file and recordkeeper_file:
+    try:
+        df_ftwilliam = load_uploaded_file(ftwilliam_file)
+        df_recordkeeper = load_uploaded_file(recordkeeper_file)
 
-uploaded_file = st.file_uploader("Drop a file here", type=["csv","xlsx","txt"])
+        reconciliation_df = build_reconciliation(df_ftwilliam, df_recordkeeper)
 
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
+    st.info("Upload both files to generate the reconciliation form.")
 
EOF
)
