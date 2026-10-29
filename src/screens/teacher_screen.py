import re
import time
import streamlit as st
from src.ui.base_layout import style_background_dashboard,style_base_layout
from src.componenets.header import header_dashbourd
from src.database.db import check_teacher_exists, create_teacher,teacher_login,get_teacher_subjects, get_teacher_by_username, check_pass, get_all_teachers
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


def login_teacher(username, password):
    """Returns (success, field_errors_dict)

    NOTE: To satisfy the requirement that a wrong-username-but-right-password
    case shows only a username error, this checks the entered password
    against ALL teacher accounts, not just the one matching the typed
    username. This is unusual for production login forms (real systems never
    reveal that a password matches someone else's account) but is done here
    per project spec for a non-production student app.
    """
    field_errors = {}
    username = (username or "").strip()

    if not username:
        field_errors['username'] = "Username is required"
    if not password:
        field_errors['pass'] = "Password is required"

    if field_errors:
        return False, field_errors

    teacher = get_teacher_by_username(username)
    username_valid = teacher is not None

    # Does this password match the typed username's own account?
    password_matches_this_account = bool(teacher and check_pass(password, teacher['password']))

    # Does this password match ANY teacher account at all?
    password_valid_somewhere = password_matches_this_account
    if not password_valid_somewhere:
        for t in get_all_teachers():
            if check_pass(password, t['password']):
                password_valid_somewhere = True
                break

    # Success: username exists AND password matches that same account
    if username_valid and password_matches_this_account:
        st.session_state.user_role = 'teacher'
        st.session_state.teacher_data = teacher
        st.session_state.is_logged_in = True
        return True, {}

    # Both wrong
    if not username_valid and not password_valid_somewhere:
        field_errors['username'] = "Username is incorrect"
        field_errors['pass'] = "Password is incorrect"
        return False, field_errors

    # Username correct, password wrong for this account
    if username_valid and not password_matches_this_account:
        field_errors['pass'] = "Password is incorrect"
        return False, field_errors

    # Username incorrect, but password is valid for some account
    if not username_valid and password_valid_somewhere:
        field_errors['username'] = "Username is incorrect"
        return False, field_errors

    # Fallback (shouldn't normally hit this)
    field_errors['pass'] = "Password is incorrect"
    return False, field_errors


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

    if "login_field_errors" not in st.session_state:
        st.session_state.login_field_errors = {}
    errors = st.session_state.login_field_errors

    teacher_username = st.text_input("Enter Username",placeholder='Enter your name')
    if errors.get('username'):
        st.error(errors['username'])

    teacher_pass = st.text_input("Enter password",type='password',placeholder='Enter Password')
    if errors.get('pass'):
        st.error(errors['pass'])

    st.divider()
    btnc1,btnc2 = st.columns(2)
    with btnc1:
        if st.button('Login',icon=':material/passkey:',shortcut='control+enter',width='stretch'):
            success, field_errors = login_teacher(teacher_username, teacher_pass)
            if success:
                st.session_state.login_field_errors = {}
                st.toast("welcome back!")
                time.sleep(1)
                st.rerun()
            else:
                st.session_state.login_field_errors = field_errors
                st.rerun()

    with btnc2:
        if st.button('Register Instead',type="primary",icon=':material/passkey:',width='stretch'):
            st.session_state.login_field_errors = {}
            st.session_state.teacher_login_type = 'register'
            st.rerun()


# ---------------------------------------------------------------------------
# Registration: field-level validation + password rules + success dialog
# ---------------------------------------------------------------------------

def validate_password(pwd):
    """Returns (is_valid, list_of_error_messages)"""
    errors = []
    if len(pwd) < 8:
        errors.append("At least 8 characters")
    if not re.search(r"[A-Z]", pwd):
        errors.append("At least 1 uppercase letter")
    if not re.search(r"[0-9]", pwd):
        errors.append("At least 1 number")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>_\-]", pwd):
        errors.append("At least 1 special character")
    return (len(errors) == 0, errors)


def register_teacher(teacher_username, teacher_name, teacher_pass, teacher_pass_confirm):
    """Returns (success, message, field_errors_dict)"""
    field_errors = {}

    if not teacher_username:
        field_errors['username'] = "Username is required"
    if not teacher_name:
        field_errors['name'] = "Name is required"
    if not teacher_pass:
        field_errors['pass'] = "Password is required"
    if not teacher_pass_confirm:
        field_errors['confirm'] = "Please confirm your password"

    # Stop early if any required field is empty
    if field_errors:
        return False, "Please fill in all required fields", field_errors

    # Password strength check
    is_valid, pwd_errors = validate_password(teacher_pass)
    if not is_valid:
        field_errors['pass'] = "Missing: " + ", ".join(pwd_errors)
        return False, "Password does not meet requirements", field_errors

    if teacher_pass != teacher_pass_confirm:
        field_errors['confirm'] = "Passwords do not match"
        return False, "Passwords do not match", field_errors

    try:
        if check_teacher_exists(teacher_username):
            field_errors['username'] = "Username already taken"
            return False, "Username already taken", field_errors
    except Exception as e:
        return False, f"Database Error: {e}", {}

    try:
        create_teacher(teacher_username, teacher_pass, teacher_name)
        return True, "Account created successfully!", {}
    except Exception as e:
        return False, f"Unexpected Error: {e}", {}


@st.dialog("Success")
def registration_success_dialog():
    st.success("🎉 Registration Successful!")
    st.write("Your teacher account has been created. You can now log in.")
    if st.button("OK", type='primary', width='stretch'):
        st.session_state.teacher_login_type = 'login'
        st.session_state.register_field_errors = {}
        st.rerun()


def teacher_screen_register():
    c1, c2 = st.columns(2, vertical_alignment='center', gap='xxlarge')
    with c1:
        header_dashbourd()

    with c2:
        if st.button("Go Back to Home", type='secondary',key='backbtn_register', shortcut="control+backspace"):
            st.session_state['login_type'] = None
            st.rerun()

    st.space()
    st.space()
    st.header('Register Your Profile', text_alignment='center')
    st.space()
    st.space()

    if "register_field_errors" not in st.session_state:
        st.session_state.register_field_errors = {}
    errors = st.session_state.register_field_errors

    teacher_username = st.text_input("Enter Username", placeholder='isnam@12')
    if errors.get('username'):
        st.error(errors['username'])

    teacher_name = st.text_input("Enter name", placeholder='Mansi Chauhan')
    if errors.get('name'):
        st.error(errors['name'])

    teacher_pass = st.text_input(
        "Password", type='password',
        placeholder='Min 8 chars, 1 uppercase, 1 number, 1 special char',
        key="teacher_pass"
    )
    if errors.get('pass'):
        st.error(errors['pass'])

    teacher_pass_confirm = st.text_input(
        "Confirm Password", type='password',
        placeholder='Confirm your Password', key="teacher_pass_confirm"
    )
    if errors.get('confirm'):
        st.error(errors['confirm'])

    st.divider()
    btnc1, btnc2 = st.columns(2)

    with btnc1:
        if st.button('Register now', icon=':material/passkey:',
                     shortcut='control+enter', width='stretch'):
            success, message, field_errors = register_teacher(
                teacher_username,
                teacher_name,
                teacher_pass,
                teacher_pass_confirm
            )

            if success:
                st.session_state.register_field_errors = {}
                registration_success_dialog()
            else:
                st.session_state.register_field_errors = field_errors
                st.rerun()

    with btnc2:
        if st.button('Login Instead', type="primary", icon=':material/passkey:', width='stretch'):
            st.session_state.register_field_errors = {}
            st.session_state.teacher_login_type = 'login'
            st.rerun()