import streamlit as st

from src.screens.home_screen import home_screen
from src.screens.teacher_screen import teacher_screen
from src.screens.student_screen import student_screen
from src.componenets.auto_enroll_dialog import auto_enroll_dialog


def main():
    st.set_page_config(
        page_title='SnapClass - Making Attendance faster using AI',
        page_icon = "https://i.ibb.co/YTYGn5qV/logo.png"
    )

    if "login_type" not in st.session_state:
        st.session_state.login_type = None


    # check share link FIRST
    join_code = st.query_params.get("join_code")


    if join_code:
        st.session_state.join_code = join_code

        # force student page
        st.session_state.login_type = "student"


    match st.session_state.login_type:

        case "teacher":
            teacher_screen()


        case "student":
            student_screen()


        case None:
            home_screen()


main()