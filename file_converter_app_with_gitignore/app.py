import streamlit as st
import pandas as pd

st.title("File Converter App")

uploaded_file = st.file_uploader("Drop a file here", type=["csv","xlsx","txt"])

if uploaded_file:
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    elif uploaded_file.name.endswith(".xlsx"):
        df = pd.read_excel(uploaded_file)
    else:
        df = pd.read_csv(uploaded_file, sep="\t")

    st.subheader("Preview")
    st.dataframe(df)

    st.subheader("Converted Output")
    st.dataframe(df)

    st.download_button(
        "Download CSV",
        df.to_csv(index=False),
        "converted.csv",
        "text/csv"
    )