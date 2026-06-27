import streamlit as st
from PIL import Image

@st.dialog("Add Attendance Photos", width="large")
def add_photos_dialog():

    if "camera_widget_version" not in st.session_state:
        st.session_state.camera_widget_version = 0

    tab1, tab2 = st.tabs(["📁 Upload from Device", "📷 Use Camera"])

    with tab1:
        uploaded_files = st.file_uploader(
            "Choose photo(s)",
            type=["jpg", "jpeg", "png"],
            accept_multiple_files=True,
            key="attendance_file_uploader"
        )
        if uploaded_files:
            for file in uploaded_files:
                if file.file_id not in st.session_state.captured_photo_ids:
                    st.session_state.attendance_images.append(Image.open(file))
                    st.session_state.captured_photo_ids.add(file.file_id)

    with tab2:
        camera_key = f"camera_input_{st.session_state.camera_widget_version}"
        photo = st.camera_input("Take a photo", key=camera_key)

        if photo is not None and photo.file_id not in st.session_state.captured_photo_ids:
            st.session_state.attendance_images.append(Image.open(photo))
            st.session_state.captured_photo_ids.add(photo.file_id)
            st.session_state.camera_widget_version += 1  # forces a fresh camera next time
            st.rerun()

    st.divider()
    st.caption(f"{len(st.session_state.attendance_images)} photo(s) added so far.")

    if st.button("Done", type="primary", width="stretch"):
        st.rerun()
