from os import environ
from urllib.parse import quote

import numpy as np
import pandas as pd
import requests
import streamlit as st

# USER = "guese.justin@gmail.com"
BACKEND_URL = environ.get("BACKEND_URL", "http://127.0.0.1:8001/")

st.set_page_config(page_title="AI Documenterator", layout="wide", page_icon="🤖")


def loadChat():
    if len(st.session_state["chats"]) == 0:
        st.session_state["chat_history"] = []
        st.session_state["crnt_source_documents"] = []
        return
    resp = requests.get(
        BACKEND_URL
        + "conversation/fromid/"
        + quote(st.session_state.user)
        + "/"
        + str(st.session_state["chats"][st.session_state["current_chat_id"]]["id"])
    )
    if resp.status_code == 404:
        st.session_state["chat_history"] = []
        st.session_state["crnt_source_documents"] = []
        return

    resp.raise_for_status()
    resp = resp.json()
    # {
    # "conversation_id": 0,
    # "currentQuestion": "string",
    # "currentAnswer": "string",
    # "sourceDocuments": [
    #     {
    #     "id": 0,
    #     "project_id": 0,
    #     "owner_id": "string",
    #     "summary": "string",
    #     "title": "string",
    #     "signed_url": "string",
    #     "expires_at": "2024-03-21T09:16:20.838Z",
    #     "created_at": "2024-03-21T09:16:20.838Z"
    #     }
    # ],
    # "chatHistory": [
    #     {
    #     "id": 0,
    #     "conversation_id": 0,
    #     "query": "string",
    #     "answer": "string",
    #     "created_at": "2024-03-21T09:16:20.838Z"
    #     }
    # ]
    # }
    if resp == []:
        st.session_state["chat_history"] = []
        st.session_state["crnt_source_documents"] = []
    else:
        st.session_state["chat_history"] = resp["chatHistory"]
        st.session_state["crnt_source_documents"] = resp["sourceDocuments"]


@st.cache_data
def load_data(user: str):
    projects = requests.get(BACKEND_URL + "projects/" + quote(user)).json()
    return projects


@st.cache_data
def load_data_per_project(user: str, projectname: str):
    documents = requests.get(
        BACKEND_URL + "list-documents/" + quote(user) + "/" + quote(projectname)
    ).json()
    documents = pd.DataFrame(documents)
    if len(documents) == 0:
        documents = pd.DataFrame(
            columns=["title", "summary", "signed_url", "created_at"]
        )
    documents = documents[["title", "summary", "signed_url", "created_at"]]
    documents.columns = ["Title", "Content", "Download", "Uploaded at"]
    documents = documents.set_index("Title")
    documents = documents.sort_values("Uploaded at", ascending=False)

    # [
    #     {
    #         "id": 0,
    #         "project_id": 0,
    #         "owner_id": "string",
    #         "summary": "string",
    #         "title": "string",
    #         "signed_url": "string",
    #         "expires_at": "2024-03-21T07:27:05.540Z",
    #         "created_at": "2024-03-21T07:27:05.540Z"
    #     }
    # ]
    chats = requests.get(
        BACKEND_URL + "conversation/" + quote(user) + "/" + quote(projectname)
    ).json()
    # transform to id : chat format
    # chats = {chat["id"]: chat for chat in chats}
    # [
    #     {
    #         "id": 0,
    #         "name": "string",
    #         "project_id": 0,
    #         "user_id": "string",
    #         "created_at": "2024-03-21T07:28:07.968Z",
    #         "last_update": "2024-03-21T07:28:07.968Z",
    #         "latest_source_ids": [
    #         "string"
    #         ]
    #     }
    # ]
    # chats = pd.DataFrame(chats)
    # chats = chats[["name", "last_update", "id"]].set_index("name")
    # chats.columns = ["Last Update", "ID"]
    return documents, chats


if "token" not in st.session_state:
    # redirect to "/"
    st.write("Please log in to access this page.")
else:

    ### Authentication success

    st.session_state["loading"] = False

    with st.sidebar:
        if "project_names" not in st.session_state:
            st.session_state["current_project"] = 0
            st.session_state["projects"] = load_data(st.session_state.user)
            st.session_state["project_names"] = [
                x["name"] for x in st.session_state["projects"]
            ]
            DOCUMENTS, st.session_state["chats"] = load_data_per_project(
                st.session_state.user,
                st.session_state["project_names"][st.session_state["current_project"]],
            )

            st.session_state["current_chat_id"] = 0

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

        st.subheader("Your Chats")

        st.write("Current Chat ID: ", st.session_state["current_chat_id"])

        with st.form("new_chat"):
            submit_button = st.form_submit_button("Create New Chat")
        if submit_button:
            new_chat_id = len(st.session_state["chats"])
            st.session_state["chats"].append(
                {
                    "chat_id": new_chat_id,
                    "project_id": st.session_state["current_project"],
                    "messages": [],
                }
            )
            st.session_state["current_chat_id"] = new_chat_id
            # reload current page
            st.rerun()

        # list all chats
        chat = st.radio(
            "Select Chat",
            st.session_state["chats"],
            format_func=lambda chat: chat["name"],
            index=st.session_state["current_chat_id"],
        )
        if len(st.session_state["chats"]) > 0:
            if (
                chat["id"]
                != st.session_state["chats"][st.session_state["current_chat_id"]]["id"]
            ):
                st.session_state["current_chat_id"] = st.session_state["chats"].index(
                    chat
                )
                st.rerun()

    st.title("Your Chat with Documents:")
    # st.write(st.session_state)

    st.text(
        "Current Project: "
        + st.session_state["project_names"][st.session_state["current_project"]]
    )

    st.text("Current chat id: " + str(st.session_state["current_chat_id"]))

    loadChat()

    for message in st.session_state["chat_history"]:
        with st.chat_message("assistant"):
            st.write(message["query"])
        with st.chat_message("user"):
            st.write(message["answer"])
    # finally
    if len(st.session_state["crnt_source_documents"]) > 0:
        st.info("Documents used for the answer of your last query:", icon="📄")

        for doc in st.session_state["crnt_source_documents"]:
            with st.expander(doc["title"]):
                st.write(doc["summary"])
                st.link_button(url=doc["signed_url"], label="Download")

    # user input
    qp = (
        "Ask a question in the project realm of "
        + st.session_state["project_names"][st.session_state["current_project"]]
        + ":"
    )
    prompt = st.chat_input(qp, disabled=st.session_state["loading"])

    if prompt:
        if st.session_state["loading"]:
            st.warning("Please wait for the response before asking another question.")
        else:
            st.session_state["loading"] = True
            # block further input
            with st.spinner("Loading..."):
                resp = requests.post(
                    BACKEND_URL + "question/",
                    params={
                        "user_id": st.session_state.user,
                        "project": st.session_state["project_names"][
                            st.session_state["current_project"]
                        ],
                        "query": prompt,
                        "convo_id": st.session_state["chats"][
                            st.session_state["current_chat_id"]
                        ]["id"],
                    },
                )
                resp.raise_for_status()
                loadChat()
            st.session_state["loading"] = False
            st.rerun()
