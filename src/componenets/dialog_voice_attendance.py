import streamlit as st
from src.pipelines.voice_pipelines import process_bulk_audio
from src.database.config import supabase
from datetime import datetime
import pandas as pd
from src.componenets.dialog_attendance_results import show_atteandance_result



@st.dialog('Voice Attendance')
def voice_attendance_dialog(selected_subject_id):
    st.write('Record audio of students saying I am prsent.Then AI will recognize the student')
    audio_data = None
    audio_data = st.audio_input("Record classroom audio")
    if st.button('Analyze Audio',width='stretch',type='primary'):
        if audio_data is None:
            st.warning('Please record audio first')
        with st.spinner('Processing Audio data'):
            enrolled_res = supabase.table("subject_students").select(
            "student_id, students(student_id,name,voice_embedding)"
            ).eq("subject_id", selected_subject_id).execute()

            enrolled_students = enrolled_res.data
            if not enrolled_students:
                st.warning('No student enrolled in course')
                return
            candidates_dict={
                s['students']['student_id']:s['students']['voice_embedding']
                for s in enrolled_students if s['students'].get('voice_embedding')
            }
            if not candidates_dict:
                st.error('No enrolled students have voice profile registred')
                return
            audio_bytes = audio_data.read()
            detected_scores = process_bulk_audio(audio_bytes,candidates_dict)

            results = []
            attendance_to_log = []

            current_timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

            for node in enrolled_students:
                student = node["students"]
                student_id = student["student_id"]

                score = detected_scores.get(student['student_id'],0.0)
                is_present = bool(score>0)

                results.append({
                    "Name": student["name"],
                    "ID": student['student_id'],
                    "Source":score if is_present else "-",
                    "Status": "Present" if is_present else "Absent"
                })

                attendance_to_log.append({
                    "student_id": student_id,
                    "subject_id": selected_subject_id,
                    "timestamp": current_timestamp,
                    "is_present": is_present
                })
            st.session_state.voice_attendance_results = (pd.DataFrame(results),attendance_to_log)
    
    if st.session_state.get('voice_attendance_results'):
        st.divider()
        df_results, logs = st.session_state.voice_attendance_results
        show_atteandance_result(df_results,logs)