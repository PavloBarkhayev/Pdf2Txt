import streamlit as st
import os
import pandas as pd
import parsing

st.set_page_config(page_title="Requirements extraction")

st.title("Requirements extraction")

uploaded_file = st.file_uploader("Select PDF-file with requirements", type="pdf")

default_csv_folder = "_csv"
if uploaded_file:
    base_name = os.path.splitext(uploaded_file.name)[0]

csv_folder = st.text_input("The name folder for the output CSV-files", value=default_csv_folder)

if st.button("Analyze") and uploaded_file and csv_folder:
    try:
        count = parsing.extract_and_write(uploaded_file.name, csv_folder)
        st.success(f"Number of requirements extracted: {count}")
        st.info(f"The results are saved to the file: {csv_folder}")
    except Exception as e:
        st.error(f"An error has occured: {e}")

df_dict = {
    'df1': pd.read_csv(f'{csv_folder}/requirements.csv'),
    'df2': pd.read_csv(f'{csv_folder}/requirements.csv'),
    'df3': pd.read_csv(f'{csv_folder}/toc.csv')
}


# Создание трех колонок с кнопками
col1, col2, col3 = st.columns(3)

# Используем session_state для хранения выбранного датафрейма
if 'selected_df' not in st.session_state:
    st.session_state.selected_df = None

with col1:
    if st.button("Show requirements"):
        st.session_state.selected_df = 'df1'

with col2:
    if st.button("Show relations"):
        st.session_state.selected_df = 'df2'

with col3:
    if st.button("Show ToC"):
        st.session_state.selected_df = 'df3'

# Отображение выбранного датафрейма
if st.session_state.selected_df in df_dict:
    st.dataframe(df_dict[st.session_state.selected_df])
else:
    st.write("Press a button to upload the results")