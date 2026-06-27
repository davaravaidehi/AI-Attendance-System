import streamlit as st
from src.ui.base_layout import style_background_dashboard,style_base_layout
from src.componenets.header import header_dashbourd
from PIL import Image
import numpy as np
from src.pipelines.face_pipelines import predict_attendance,get_face_embeddings,train_classifire
from src.pipelines.voice_pipelines import get_voice_embedding
from src.database.db import get_all_students,create_student,get_student_subjects,get_student_attendance,unenroll_student_to_subject
from src.componenets.dialog_enroll import enroll_dialog 
from src.componenets.subject_card import subject_card
from src.database.db import supabase
from src.componenets.auto_enroll_dialog import auto_enroll_dialog
import time

def student_dashbourd():
    student_data = st.session_state.student_data
    student_id = student_data['student_id']
    c1,c2 = st.columns(2,vertical_alignment = 'center',gap='xxlarge')
    with c1:
        header_dashbourd()
    with c2:
        st.header(f"""Welcome ,{student_data['name']}""")
        if st.button("Logout", type='secondary',key='loginbackbtn',shortcut="control+backspace"):
            st.session_state['is_logged_in'] = False
            del st.session_state.student_data
            st.rerun()
    
    st.space()

    c1,c2 = st.columns(2)
    with c1:
        st.header("Your Enrolled Subjects")
    with c2:
        if st.button('Enroll in Subject',type='primary',width='stretch'):
            enroll_dialog()


    st.divider()

    with st.spinner('Loading your enrolled subjects....'):
        subjects = get_student_subjects(student_id)
        logs = get_student_attendance(student_id)
    
    stats_map = {}
    for log in logs:
        sid = log['subject_id']

        if sid not in stats_map:
            stats_map[sid] = {"total":0,"attended":0}

        stats_map[sid]['total'] +=1

        if log.get('is_present'):
            stats_map[sid]['attended'] +=1

    cols = st.columns(2)
    for i, sub_node in enumerate(subjects):
        sub = sub_node['subjects']
        sid = sub['subject_id']

        stats = stats_map.get(sid,{"total":0,"attended":0})
        def unenroll_button(subject_id):
            if st.button(
                "Unenroll from this course",
                type='tertiary',
                width='stretch',
                key=f"unenroll_{sid}"
            ):
                unenroll_student_to_subject(student_id, subject_id)
                st.toast(f"Unenrolled from {sub['name']} Successfully")
                st.rerun()
        with cols[i % 2]:
            subject_card(
                name = sub['name'],
                code = sub['subject_code'],
                section = sub['section'],
                stats = [
                    ('Total',stats['total']),
                    ('Attended', stats['attended']),
                ],
                footer_callback=lambda: unenroll_button(sid)
            )
def student_layout():
    st.header("Student Dashboard")

def student_screen():

    style_background_dashboard()
    style_base_layout()
    join_code = st.query_params.get("join_code")
    if join_code:
        st.session_state.join_code = join_code

    #already logged in
    if "student_data" in st.session_state:
        if "join_code" in st.session_state:
            auto_enroll_dialog(
                st.session_state.join_code
            )

            del st.session_state.join_code


        student_dashbourd()
        return


    # if "student_data" in st.session_state:
    #     student_dashbourd()
    #     return 
       

    c1,c2 = st.columns(2,vertical_alignment = 'center',gap='xxlarge')
    with c1:
        header_dashbourd()
    with c2:
        if st.button("Go Back to Home", type='secondary',key='loginbackbtn',shortcut="control+backspace"):
            st.session_state['login_type'] = None
            st.rerun()
    st.space()
    st.space()

    st.header('Login Using FaceID', text_alignment='center')
    st.space()

    if "show_registration" not in st.session_state:
        st.session_state.show_registration = False
    photo_source = st.camera_input("Position your face in the center")

    if photo_source:
        img = np.array(Image.open(photo_source))

        with st.spinner('AI is scanning....'):
            detected, all_ids,num_faces = predict_attendance(img)

            if num_faces == 0:
                st.warning('Face not found!')
            elif num_faces >1:
                st.warning('Multiple face found')
            else:
                if detected:
                    student_id = list(detected.keys())[0]
                    all_students = get_all_students()
                    student = next((s for s in all_students if str(s['student_id']) == str(student_id)), None)

                    if student:
                        st.session_state.is_logged_in = True
                        st.session_state.user_role = 'student'
                        st.session_state.student_data = student
                        st.toast(f"Welcome Back!{student['name']}")
                        if "join_code" in st.session_state:

                            auto_enroll_dialog(
                                st.session_state.join_code
                            )

                            del st.session_state.join_code
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Face matched an ID that isn't in the database anymore. Please contact your teacher.")


                else:
                    st.info('Face not recognized! You might be a new Student!')
                    st.session_state.show_registration = True

    if st.session_state.show_registration:
        with st.container(border=True):
            st.header('Register new Profile')
            new_name = st.text_input("Enter your name", placeholder='E.g. Mansi Chauhan')
            st.subheader('Optional: Voice Enrollement')
            st.info("Enroll your voice only for attendence")

            audio_data = None
            try:
                audio_data = st.audio_input('Record a short phrase like I am present, My name is Mansi.')
            except Exception:
                st.error('Audio Data failed!')
            
            if st.button('create Account', type='primary'):
                if new_name:
                    if photo_source is None:
                        st.warning("Please capture your face first")
                        return
                    with st.spinner('Creating profile....'):
                        img = np.array(Image.open(photo_source))
                        encodings = get_face_embeddings(img)
                        if encodings:
                            face_emb = encodings[0].tolist()
                            voice_emb = None
                            if audio_data:
                                voice_emb = get_voice_embedding(audio_data.read())

                            response_data = create_student(new_name,face_embedding= face_emb, voice_embedding= voice_emb)

                            if response_data:
                                train_classifire()
                                st.session_state.is_logged_in = True
                                st.session_state.user_role = 'student'
                                st.session_state.student_data = response_data[0]
                                if "join_code" in st.session_state:

                                    auto_enroll_dialog(
                                        st.session_state.join_code
                                    )

                                    del st.session_state.join_code
                                st.toast(f"Profile Created Hi {new_name}!")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error('couldnt capture your facial features for registration')


                else:
                    st.warning('please enter your name!')

        