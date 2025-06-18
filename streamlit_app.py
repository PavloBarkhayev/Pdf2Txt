import streamlit as st
import os
import pandas as pd
import parsing

st.set_page_config(page_title="Requirements extraction")

st.title("Requirements extraction")

uploaded_file = st.file_uploader("Select PDF-file with requirements", type="pdf")

default_csv_name = ""
if uploaded_file:
    base_name = os.path.splitext(uploaded_file.name)[0]
    default_csv_name = f"_csv/{base_name}.csv"

csv_filename = st.text_input("The name of the output CSV-file", value=default_csv_name)

if st.button("Analyze") and uploaded_file and csv_filename:
    try:
        _,count = parsing.extract_requirements(uploaded_file.name, csv_filename)
        st.success(f"Number of requirements extracted: {count}")
        st.info(f"The results are saved to the file: {csv_filename}")
    except Exception as e:
        st.error(f"An error has occured: {e}")

if st.button("Show results") and csv_filename and os.path.exists(csv_filename):
    try:
        df = pd.read_csv(csv_filename)
        st.dataframe(df)
    except Exception as e:
        st.error(f"Were unable to upload the CSV-file: {e}")