import streamlit as st
import os
import base64
import json
from google.api_core.exceptions import InvalidArgument
from google.cloud import dialogflowcx_v3 as dialogflowcx

# --- CONFIGURATION  
PROJECT_ID = "futureml-chatbot"   
LOCATION = "us-central1"         
AGENT_ID = "d7b93141-ee5d-4ff9-a7eb-1b2024a41602"   
 
creds_path = "google_credentials.json"

# Deployed on Streamlit Cloud
if "GCP_CREDENTIALS_BASE64" in st.secrets:
    # Decode the base64 secret and write it to a temporary file
    creds_base64 = st.secrets["GCP_CREDENTIALS_BASE64"]
    creds_json_str = base64.b64decode(creds_base64).decode("utf-8")
    with open(creds_path, "w") as f:
        f.write(creds_json_str)

# Set the environment variable to point to the credentials file
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_path


# --- DIALOGFLOW CLIENT SETUP ---

def detect_intent_texts(project_id, location_id, agent_id, session_id, texts, language_code):
    """Returns the result of detect intent with texts as inputs."""
    session_path = f"projects/{project_id}/locations/{location_id}/agents/{agent_id}/sessions/{session_id}"
    client_options = {"api_endpoint": f"{location_id}-dialogflow.googleapis.com"}
    
    sessions_client = dialogflowcx.SessionsClient(client_options=client_options)

    for text in texts:
        text_input = dialogflowcx.TextInput(text=text)
        query_input = dialogflowcx.QueryInput(text=text_input, language_code=language_code)
        request = dialogflowcx.DetectIntentRequest(
            session=session_path, query_input=query_input
        )
        response = sessions_client.detect_intent(request=request)

    # Extract the text from the response messages
    response_messages = [
        " ".join(msg.text.text) for msg in response.query_result.response_messages
    ]
    return response_messages


# --- STREAMLIT APP LAYOUT ---

st.set_page_config(page_title="Customer Support Bot", layout="centered")

st.title("🤖 Globe Trotter Goods Support")
st.write("Welcome! I'm here to help with your questions. Ask me about order status, returns, or shipping.")

# Initialize chat history in session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# React to user input
if prompt := st.chat_input("How can I help you?"):
    # Display user message in chat message container
    st.chat_message("user").markdown(prompt)
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Get bot response
    try:
        # Generate a unique session ID for this user's conversation
        session_id = st.session_state.get("session_id", "my-session-12345")  # Simple session ID for demo
        st.session_state.session_id = session_id

        # Replace AGENT_ID placeholder check
        if AGENT_ID == "YOUR_AGENT_ID":
            bot_response_texts = ["Error: Please update the AGENT_ID in the app.py script."]
        else:
            bot_response_texts = detect_intent_texts(
                PROJECT_ID, LOCATION, AGENT_ID, session_id, [prompt], "en"
            )
        
        bot_response = " ".join(bot_response_texts)

    except Exception as e:
        st.error("Sorry, there was an error connecting to the chatbot service.")
        bot_response = "I'm having trouble connecting right now. Please try again later."
        print(e)   
    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        st.markdown(bot_response)
    
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": bot_response})
