import streamlit as st
from src.ui.base_layout import style_background_dashboard,style_base_layout
from src.componenets.header import header_dashbourd
from src.database.db import check_teacher_exists, create_teacher,teacher_login,get_teacher_subjects
from src.componenets.dialog_create_subject import create_subject_dialog
from src.database.db import create_subject,get_attendance_for_teacher
from src.componenets.subject_card import subject_card
from src.componenets.dialog_share_subject import share_subject_dialog
from src.componenets.add_photos_dialog import add_photos_dialog
from src.pipelines.face_pipelines import predict_attendance
import numpy as np
import pandas as pd
import cv2
from src.database.config import supabase
from datetime import datetime
from src.componenets.dialog_attendance_results import attendance_result_dialog
from src.componenets.dialog_voice_attendance import voice_attendance_dialog

def teacher_screen():
    style_background_dashboard()
    style_base_layout()

    if "teacher_data" in st.session_state:
        teacher_dashbourd()
    elif 'teacher_login_type' not in st.session_state or st.session_state.teacher_login_type=="login":
        teacher_screen_login()
    elif st.session_state.teacher_login_type =="register":
        teacher_screen_register()


def teacher_dashbourd():
    if "attendance_images" not in st.session_state:
        st.session_state.attendance_images = []

    if "captured_photo_ids" not in st.session_state:
        st.session_state.captured_photo_ids = set()

    teacher_data = st.session_state.teacher_data
    c1,c2 = st.columns(2,vertical_alignment = 'center',gap='xxlarge')
    with c1:
        header_dashbourd()
    with c2:
        st.header(f"""Welcome ,{teacher_data['name']}""")
        if st.button("Logout", type='secondary',key='loginbackbtn',shortcut="control+backspace"):
            st.session_state['is_logged_in'] = False
            del st.session_state.teacher_data
            st.rerun()
    
    st.space()

    if "current_teacher_tab" not in st.session_state:
        st.session_state.current_teacher_tab = 'take_attendence'
    tab1, tab2, tab3 = st.columns(3)

    with tab1:
        type1 = "primary" if st.session_state.current_teacher_tab == 'take_attendence' else "tertiary"
        if st.button('Take Attendence', type=type1,width='stretch',icon=':material/ar_on_you:'):
            st.session_state.current_teacher_tab = 'take_attendence'
            st.rerun()

    with tab2:
        type2 = "primary" if st.session_state.current_teacher_tab == 'manage_subject' else "secondary"
        if st.button('Manage_Subject',type=type2, width='stretch',icon=':material/book_ribbon:'):
            st.session_state.current_teacher_tab = 'manage_subject'
            st.rerun()

    with tab3:
        type3 = "primary" if st.session_state.current_teacher_tab == 'attendence_records' else "tertiary"
        if st.button('Attendence Records',type=type3, width='stretch',icon=':material/cards_stack:'):
            st.session_state.current_teacher_tab = 'attendence_records'
            st.rerun()
    st.divider()

    if st.session_state.current_teacher_tab == "take_attendence":
        teacher_tab_take_attendence()
    if st.session_state.current_teacher_tab == "manage_subject":
        teacher_tab_manage_subjects()
    if st.session_state.current_teacher_tab == "attendence_records":
        teacher_tab_attendence_records()

def teacher_tab_take_attendence():
    teacher_id = st.session_state.teacher_data['teacher_id']
    st.header('Take AI Attendence')

    if 'attendance_images' not in st.session_state:
        st.session_state.attendance_images =[]

    subjects = get_teacher_subjects(teacher_id)

    if not subjects:
        st.warning('Youn havent created any subjects yet! Please create one to begin!')
        return
    
    subject_options = {f"{s['name']} - {s['subject_code']}": s['subject_id'] for s in subjects}

    col1,col2 = st.columns([3,1],vertical_alignment='bottom')

    with col1:
        selected_subject_label = st.selectbox('Select Subject',options=list(subject_options.keys()))

    with col2:
        if st.button('Add Photos', type='primary', icon=':material/photo_prints:',width='stretch'):
            add_photos_dialog()
    selected_subject_id = subject_options[selected_subject_label]

    st.divider()


    if st.session_state.attendance_images:
        st.header('Added Photos')
        gallery_cols = st.columns(4)

        for idx,img in enumerate(st.session_state.attendance_images):
            with gallery_cols[idx % 4]:
                st.image(img,width='stretch',caption=f'Photo {idx+1}')
    
    has_photos = bool(st.session_state.attendance_images)
    c1,c2,c3 = st.columns(3)
    with c1:
        if st.button('Clear all Photos', width='stretch',type='tertiary',icon=':material/delete:',disabled=not has_photos):
            st.session_state.attendance_images =[]
            st.session_state.last_camera_photo = False

            st.rerun()
    with c2:
        if st.button(
            'Run Face Analysis',
            width='stretch',
            type='tertiary',
            icon=':material/face:',
            disabled=not has_photos
        ):
            with st.spinner('Deep scanning classroom photos...'):

                all_detected_id = {}

                for idx, img in enumerate(st.session_state.attendance_images):
                    img_np = np.array(img.convert("RGB")).astype(np.uint8)
                    detected, _, _ = predict_attendance(img_np)
                    print("AI DETECTED:", detected)

                    if not detected:
                        continue

                    for sid in detected.keys():
                        sid = str(sid)   # keep as string consistently (see Bug 2)
                        all_detected_id.setdefault(sid, []).append(f"Photo {idx+1}")

                print("FINAL AI IDS:", all_detected_id)

                enrolled_res = supabase.table("subject_students").select(
                    "student_id, students(student_id,name)"
                ).eq("subject_id", selected_subject_id).execute()

                enrolled_students = enrolled_res.data

                results = []
                attendance_to_log = []
                current_timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

                for node in enrolled_students:
                    student = node["students"]
                    student_id = student["student_id"]

                    sources = all_detected_id.get(str(student_id), [])
                    is_present = len(sources) > 0

                    results.append({
                        "Name": student["name"],
                        "ID": student_id,
                        "Source": ", ".join(sources) if sources else "-",
                        "Status": "Present" if is_present else "Absent"
                    })

                    attendance_to_log.append({
                        "student_id": student_id,
                        "subject_id": selected_subject_id,
                        "timestamp": current_timestamp,
                        "is_present": is_present
                    })

                df = pd.DataFrame(results)

            attendance_result_dialog(df, attendance_to_log)
    with c3:
        if st.button('Use Voice Attendance', type='primary',width='stretch'):
            voice_attendance_dialog(selected_subject_id)

def teacher_tab_manage_subjects():

    teacher_id = st.session_state.teacher_data['teacher_id']

    col1, col2 = st.columns(2)

    with col1:
        st.header("Manage Subjects")

    with col2:
        if st.button("Create New Subject"):
            create_subject_dialog(teacher_id)


    subjects = get_teacher_subjects(teacher_id)


    if not subjects:
        st.info("NO SUBJECTS FOUND. CREATE ONE ABOVE")
        return


    for sub in subjects:

        subject_card(
            name=sub["name"],
            code=sub["subject_code"],
            section=sub["section"]
        )


        if st.button(
            f"Share Code: {sub['subject_code']}",
            key=f"share_{sub['subject_id']}",
            icon=":material/share:"
        ):
            share_subject_dialog(
                sub["name"],
                sub["subject_code"]
            )

def teacher_tab_attendence_records():

    st.header('Attendence Records')
    teacher_id = st.session_state.teacher_data['teacher_id']
    records = get_attendance_for_teacher(teacher_id)
    if not records:
        return
    data = []

    for r in records:
        ts = r.get('timestamp')

        data.append({
            "ts_group": ts.split(".")[0] if ts else None,
            "Time": datetime.fromisoformat(ts).strftime("%Y-%m-%d %I:%M %p") if ts else "N/A",
            "Subject": r['subjects']['name'],
            "Subject Code": r['subjects']['subject_code'],
            "is_present": bool(r.get('is_present', False))
        })

   
    df = pd.DataFrame(data)

    summary = (
        df.groupby(['ts_group', 'Time', 'Subject', 'Subject Code'])
        .agg(
            Present_Count=('is_present', 'sum'),
            Total_Count=('is_present', 'count')
        ).reset_index()
    )

    summary['Atteandance Stats'] = (
        summary['Present_Count'].astype(str) + " / "
        + summary['Total_Count'].astype(str) + ' Students'
    )

    display_df = (
        summary.sort_values(by='ts_group', ascending=False)
        [['Time', 'Subject', 'Subject Code', 'Atteandance Stats']]
    )

    st.dataframe(display_df, width='stretch', hide_index=True)


def login_teacher(username,password):
    if not username or not password:
        return False
    
    teacher = teacher_login(username,password)

    if teacher:
        st.session_state.user_role = 'teacher'
        st.session_state.teacher_data = teacher
        st.session_state.is_logged_in = True
        return True
def teacher_screen_login():
    c1,c2 = st.columns(2,vertical_alignment = 'center',gap='xxlarge')
    with c1:
        header_dashbourd()
    with c2:
        if st.button("Go Back to Home", type='secondary',key='loginbackbtn',shortcut="control+backspace"):
            st.session_state['login_type'] = None
            st.rerun()



    st.header('Login Using Password', text_alignment='center')
    st.space()
    st.space()

    teacher_username = st.text_input("Enter Username",placeholder='Enter your name') 
    teacher_pass = st.text_input("Enter password",type='password',placeholder='Enter Password')
    st.divider()
    btnc1,btnc2 = st.columns(2)
    with btnc1:
        if st.button('Login',icon=':material/passkey:',shortcut='control+enter',width='stretch'):
            if login_teacher(teacher_username,teacher_pass):
                st.toast("welcome back!")
                import time
                time.sleep(1)
                st.rerun()
            else:
                st.error("Invalid username and password combo")

    with btnc2:
        if st.button('Register Instead',type="primary",icon=':material/passkey:',width='stretch'):
            st.session_state.teacher_login_type = 'register'


def register_teacher(teacher_username,teacher_name,teacher_pass, teacher_pass_confirm):
    print("username =", repr(teacher_username))
    print("name =", repr(teacher_name))
    print("pass =", repr(teacher_pass))
    print("confirm =", repr(teacher_pass_confirm))

    if not teacher_username or not teacher_name or not teacher_pass or not teacher_pass_confirm:
        return False, "All Fields are required!"
    try:
        if check_teacher_exists(teacher_username):
            return False, "Username already taken"
    except Exception as e:
        return False, f"Database Error: {e}"
    if teacher_pass != teacher_pass_confirm:
        return False, "Password doesn't match"
    
    try:
        create_teacher(teacher_username,teacher_pass,teacher_name)
        return True, "Successfully Created Login Now"
    except Exception as e:
        return False, f"Unexpected Error!:{e}"


def teacher_screen_register():
    c1,c2 = st.columns(2,vertical_alignment = 'center',gap='xxlarge')
    with c1:
        header_dashbourd()

    with c2:
        if st.button("Go Back to Home", type='secondary',shortcut="control+backspace"):
            st.session_state['login_type'] = None
            st.rerun()
    st.space()
    st.space()
    st.header('Registre Your Profile', text_alignment='center')
    st.space()
    st.space()
    teacher_username = st.text_input("Enter Username",placeholder='isnam@12') 
    teacher_name = st.text_input("Enter name",placeholder='Mansi Chauhan') 
    teacher_pass = st.text_input("Password",type='password',placeholder='Enter Password',key="teacher_pass")
    teacher_pass_confirm = st.text_input("Confirm Password",type='password',placeholder='Confirm your Password', key="teacher_pass_confirm")
    st.divider()
    btnc1,btnc2 = st.columns(2)

    with btnc1:
        if st.button('Register now',
                 icon=':material/passkey:',
                 shortcut='control+enter',
                 width='stretch'):
            st.write("Username:", repr(teacher_username))
            st.write("Name:", repr(teacher_name))
            st.write("Password:", repr(teacher_pass))
            st.write("Confirm:", repr(teacher_pass_confirm))

            success, message = register_teacher(
                teacher_username,
                teacher_name,
                teacher_pass,
                teacher_pass_confirm
            )

            st.write("Result:", success, message)



    with btnc2:
        if st.button('Login Instead',type="primary",icon=':material/passkey:',width='stretch'):
            st.session_state.teacher_login_type= 'login'
            st.rerun()



