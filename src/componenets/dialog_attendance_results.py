import streamlit as st
from src.database.db import create_attendance

def show_atteandance_result(df, logs):

    st.write("Please review attendance before confirming.")

    st.dataframe(
        df,
        hide_index=True,
        width="stretch"
    )


    col1, col2 = st.columns(2)
    with col1:
        if st.button("Discard", key="discard_attendance_unique"):
            st.session_state.voice_attendance_results = None
            st.session_state.show_attendance_dialog = False
            st.session_state.attendance_images = []
            st.rerun()

    with col2:
        if st.button("Confirm & Save", key="save_attendance_unique", type="primary"):
            create_attendance(logs)
            st.session_state.show_attendance_dialog = False
            st.session_state.attendance_images = []
            st.session_state.voice_attendance_results = None
            st.success("Attendance Saved")
            st.rerun()


@st.dialog("Attendance Records", width="large")
def attendance_result_dialog(df, logs):
    show_atteandance_result(df,logs)

    