import streamlit as st


def subject_card(
    name,
    code,
    section,
    stats=None,
    footer_callback=None
):

    with st.container():

        st.markdown(
            f"""
            <div style="
                background:white;
                padding:25px;
                border-radius:20px;
                border:1px solid #dcdcdc;
                box-shadow:0px 4px 12px rgba(0,0,0,0.12);
                margin-bottom:15px;
            ">

            <h2 style="
                color:#111827;
                margin-bottom:10px;
            ">
                {name}
            </h2>


            <p style="
                color:#4b5563;
                font-size:16px;
            ">
                Code:
                <b style="color:#111827">
                {code} , {section}
                </b>
                
            </p>

            </div>
            """,
            unsafe_allow_html=True
        )


        if stats:

            c1,c2 = st.columns(2)

            with c1:
                st.markdown(
                    f"""
                    <div style="
                        background:#f3f4f6;
                        padding:12px;
                        border-radius:15px;
                    ">
                    <p style="color:#374151">
                    Total
                    </p>

                    <h2 style="color:#111827">
                    {stats[0][1]}
                    </h2>

                    </div>
                    """,
                    unsafe_allow_html=True
                )


            with c2:
                st.markdown(
                    f"""
                    <div style="
                        background:#f3f4f6;
                        padding:12px;
                        border-radius:15px;
                    ">
                    <p style="color:#374151">
                    Attended
                    </p>

                    <h2 style="color:#111827">
                    {stats[1][1]}
                    </h2>

                    </div>
                    """,
                    unsafe_allow_html=True
                )


        if footer_callback:
            footer_callback()