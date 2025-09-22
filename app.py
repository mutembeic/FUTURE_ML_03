import streamlit as st
import os
from google.api_core.exceptions import InvalidArgument
from google.cloud.dialogflow_cx_v3.services.agents import AgentsClient
from google.cloud.dialogflow_cx_v3.services.sessions import SessionsClient
from google.cloud.dialogflow_cx_v3.types.session import TextInput, QueryInput, QueryParameters, DetectIntentRequest

# --- CONFIGURATION (IMPORTANT: Fill these in!) ---

# Find these in your Dialogflow CX agent's URL:
# https://dialogflow.cloud.google.com/cx/projects/PROJECT_ID/locations/LOCATION/agents/AGENT_ID/flows/...
PROJECT_ID = "my-internship-chatbot"  # Your Google Cloud Project ID
LOCATION = "us-central1"           # The location of your agent (e.g., 'us-central1')
AGENT_ID = "YOUR_AGENT_ID"         # The long ID of your agent

# This must match the name of your JSON key file
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = 'google_credentials.json'


# --- DIALOGFLOW CLIENT SETUP ---

def detect_intent_texts(project_id, location_id, agent_id, session_id, texts, language_code):
    """Returns the result of detect intent with texts as inputs."""
    session_path = f"projects/{project_id}/locations/{location_id}/agents/{agent_id}/sessions/{session_id}"
    client_options = {"api_endpoint": f"{location_id}-dialogflow.googleapis.com"}
    
    sessions_client = SessionsClient(client_options=client_options)

    for text in texts:
        text_input = TextInput(text=text)
        query_input = QueryInput(text=text_input, language_code=language_code)
        request = DetectIntentRequest(
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
        session_id = st.session_state.get("session_id", "my-session-12345") # Simple session ID for demo
        st.session_state.session_id = session_id

        # Replace AGENT_ID placeholder check
        if AGENT_ID == "YOUR_AGENT_ID":
             bot_response_texts = ["Error: Please update the AGENT_ID in the app.py script."]
        else:
            bot_response_texts = detect_intent_texts(
                PROJECT_ID, LOCATION, AGENT_ID, session_id, [prompt], 'en'
            )
        
        bot_response = " ".join(bot_response_texts)

    except Exception as e:
        st.error("Sorry, there was an error connecting to the chatbot service.")
        bot_response = "I'm having trouble connecting right now. Please try again later."
        print(e) # For debugging in the logs

    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        st.markdown(bot_response)
    
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": bot_response})