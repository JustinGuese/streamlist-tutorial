from os import environ

import jwt
import numpy as np
import pandas as pd
import requests
import streamlit as st
from streamlit_oauth import OAuth2Component

from pages.Chat import BACKEND_URL, load_data, load_data_per_project

OAUTH_BASE_URL = environ["OAUTH_BASE_URL"]


AUTHORIZATION_URL = OAUTH_BASE_URL + "authorize"
TOKEN_URL = OAUTH_BASE_URL + "token"
REVOKE_URL = OAUTH_BASE_URL + "revoke"

REDIRECT_URI = environ.get("REDIRECT_URI", "http://localhost:8501")
SCOPE = "openid email"

oauth2 = OAuth2Component(
    environ["CLIENT_ID"],
    environ["CLIENT_SECRET"],
    AUTHORIZATION_URL,
    TOKEN_URL,
    TOKEN_URL,
    REVOKE_URL,
)


def decodeJWT(t: str):
    t = jwt.decode(
        t["id_token"], options={"verify_signature": False}, algorithms=["RS256"]
    )
    return t["email"]


if "token" not in st.session_state:
    st.write("please log in:")
    result = oauth2.authorize_button(
        "Continue with AWS Login",
        REDIRECT_URI,
        SCOPE,
    )

    if result and "token" in result:
        # If authorization successful, save token in session state
        st.session_state.token = result.get("token")

        if "user" not in st.session_state:
            st.session_state.user = decodeJWT(st.session_state.token)
        st.rerun()

else:
    st.session_state.user = decodeJWT(st.session_state.token)
    st.session_state["projects"] = load_data(st.session_state.user)
    if "current_project" not in st.session_state:
        st.session_state["current_project"] = 0
    st.session_state["project_names"] = [
        x["name"] for x in st.session_state["projects"]
    ]

    DOCUMENTS, st.session_state["chats"] = load_data_per_project(
        st.session_state.user,
        st.session_state["project_names"][st.session_state["current_project"]],
    )

    st.session_state["current_chat_id"] = 0

    with st.sidebar:
        st.text("User: " + st.session_state.user)

        st.subheader("Projects")
        option = st.selectbox(
            "Current Project",
            st.session_state["project_names"],
            index=st.session_state["current_project"],
        )
        # if option changes, set st-session_state["current_project"] to the index of the selected project
        if (
            option
            != st.session_state["project_names"][st.session_state["current_project"]]
        ):
            st.session_state["current_project"] = st.session_state[
                "project_names"
            ].index(option)
            # reload chats for new project
            DOCUMENTS, st.session_state["chats"] = load_data_per_project(
                st.session_state.user,
                st.session_state["project_names"][st.session_state["current_project"]],
            )
            st.rerun()

        # new project input and button
        with st.form("new_project"):
            new_project = st.text_input("New Project Name")
            submit_button = st.form_submit_button("Create New Project")

        if submit_button:
            # eeet isss what it eeez
            response = requests.get(
                BACKEND_URL
                + "conversation/"
                + st.session_state.user
                + "/"
                + new_project
            )
            assert response.status_code == 200, (
                "Failed to create new project: " + response.json()
            )
            # refresh session state data
            st.cache_data.clear()
            st.session_state["projects"] = load_data(st.session_state.user)
            st.session_state["project_names"] = [
                x["name"] for x in st.session_state["projects"]
            ]
            st.session_state["current_project"] = st.session_state[
                "project_names"
            ].index(new_project)

    st.title("AI Documents")
    st.text(
        "Current Project: "
        + st.session_state["project_names"][st.session_state["current_project"]]
    )
    # st.write("session state: ", st.session_state)
    st.markdown(
        """Welcome to AI Documents! You can upload documents below, or go an fuck yourself!"""
    )

    st.subheader("Upload Documents")

    with st.form("doc_upload", clear_on_submit=True):
        uploaded_files = st.file_uploader(
            "upload any documents you want to include in the project",
            accept_multiple_files=True,
            type=("ppt", "docx", "doc", "txt", "eml", "pdf"),
        )
        doc_submit = st.form_submit_button("Upload")
        if len(uploaded_files) > 0 and doc_submit:
            files = []
            for file in uploaded_files:
                files.append(("upload_files", (file.name, file.getvalue(), file.type)))

            resp = requests.post(
                BACKEND_URL + "upload/",
                files=files,
                params={
                    "user_id": st.session_state.user,
                    "project": st.session_state["project_names"][
                        st.session_state["current_project"]
                    ],
                },
                headers={
                    # "Content-Type": "multipart/form-data",
                    "Accept": "application/json",
                },
            )
            resp.raise_for_status()
            st.info("Upload success!")

    st.subheader("Continue your previous chats")

    st.page_link("pages/Chat.py", label="Chats", icon="🤖")

    st.subheader("Your documents")

    st.dataframe(
        DOCUMENTS,
        column_config={
            "Download": st.column_config.LinkColumn(display_text="Download"),
            "Uploaded at": st.column_config.DateColumn(),
        },
    )
