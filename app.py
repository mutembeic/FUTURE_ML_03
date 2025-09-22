import streamlit as st
import os
import base64
import json
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

#GLOBAL CONFIGURATION
 
if 'BOT_MODE' not in st.session_state:
    st.session_state.BOT_MODE = "Dialogflow"  

#DIALOGFLOW SETUP (PRIMARY BOT)
try:
    from google.cloud import dialogflowcx_v3 as dialogflowcx

    # Configuration for Dialogflow
    PROJECT_ID = "futureml-chatbot"
    LOCATION = "us-central1"
    AGENT_ID = "d7b93141-ee5d-4ff9-a7eb-1b2024a41602"
    
    # Authentication (will be attempted)
    creds_path = "google_credentials.json"
    if "GCP_CREDENTIALS_BASE64" in st.secrets:
        creds_base64 = st.secrets["GCP_CREDENTIALS_BASE64"]
        creds_json_str = base64.b64decode(creds_base64).decode("utf-8")
        with open(creds_path, "w") as f:
            f.write(creds_json_str)
    
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_path

    # Define the Dialogflow client function
    def detect_intent_texts_dialogflow(session_id, text, language_code='en'):
        session_path = f"projects/{PROJECT_ID}/locations/{LOCATION}/agents/{AGENT_ID}/sessions/{session_id}"
        client_options = {"api_endpoint": f"{LOCATION}-dialogflow.googleapis.com"}
        sessions_client = dialogflowcx.SessionsClient(client_options=client_options)

        text_input = dialogflowcx.TextInput(text=text)
        query_input = dialogflowcx.QueryInput(text=text_input, language_code=language_code)
        request = dialogflowcx.DetectIntentRequest(session=session_path, query_input=query_input)
        response = sessions_client.detect_intent(request=request)
        
        response_messages = [" ".join(msg.text.text) for msg in response.query_result.response_messages]
        return " ".join(response_messages)

    # A simple check to see if credentials are valid on the first run
    if "dialogflow_ready" not in st.session_state:
        try:
            # This will fail if auth is wrong, triggering the fallback
            detect_intent_texts_dialogflow("initial_check_session", "hello")
            st.session_state.dialogflow_ready = True
        except Exception as e:
            st.session_state.dialogflow_ready = False
            st.session_state.BOT_MODE = "Local" 
            print(f"Dialogflow check failed, switching to local bot. Error: {e}")

except Exception:
    # If the import itself fails, we immediately know Dialogflow is not available
    st.session_state.dialogflow_ready = False
    st.session_state.BOT_MODE = "Local"


#LOCAL SEMANTIC BOT SETUP (FALLBACK BOT)  
@st.cache_resource
def load_local_bot_resources():
    """Load resources for the self-contained bot."""
    model = SentenceTransformer('all-MiniLM-L6-v2')
    base_dir = os.path.dirname(os.path.abspath(__file__))
    faq_path = os.path.join(base_dir, 'data', 'faq_data.json')
    embeddings_path = os.path.join(base_dir, 'models', 'faq_embeddings.npy')
    with open(faq_path, 'r') as f:
        faq_data = json.load(f)
    question_embeddings = np.load(embeddings_path)
    return model, faq_data, question_embeddings

model, faq_data, question_embeddings = load_local_bot_resources()
fallback_answer = "I'm sorry, I'm having trouble connecting to my advanced systems. Based on local data, I can't find an answer to that. Please try rephrasing."

def get_local_response(user_query, confidence_threshold=0.5):
    """Local semantic search logic."""
    query_embedding = model.encode([user_query])
    similarities = cosine_similarity(query_embedding, question_embeddings)
    best_match_index = np.argmax(similarities)
    best_match_score = similarities[0][best_match_index]
    if best_match_score >= confidence_threshold:
        return faq_data[best_match_index]['answer']
    else:
        return fallback_answer

#MAIN APP LOGIC
st.set_page_config(page_title="Customer Support Bot", layout="centered")

st.title("🤖 Globe Trotter Goods Support")

# Display a status indicator for which bot is running
if st.session_state.BOT_MODE == "Dialogflow" and st.session_state.get("dialogflow_ready", False):
    st.success("Status: Connected to Google Dialogflow CX Engine.")
else:
    st.warning("Status: Could not connect to Dialogflow. Running in local fallback mode.")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "How can I help you today?"}]

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# React to user input
if prompt := st.chat_input("Ask about shipping, returns, or orders..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    #INTELLIGENT ROUTING LOGIC
    bot_response = ""
    try:
        # Check if we should be using Dialogflow
        if st.session_state.BOT_MODE == "Dialogflow" and st.session_state.get("dialogflow_ready", False):
            session_id = st.session_state.get("session_id", "streamlit-session-123")
            st.session_state.session_id = session_id
            bot_response = detect_intent_texts_dialogflow(session_id, prompt)
        else:
            # If not, use the local bot
            bot_response = get_local_response(prompt)
    
    except Exception as e:
        # If Dialogflow fails at any point, switch to local mode for the rest of the session
        st.session_state.BOT_MODE = "Local"
        st.error("Connection to Dialogflow failed. Switching to local fallback mode.")
        print(f"Dialogflow error: {e}")  
        bot_response = get_local_response(prompt)

    # Display bot response
    with st.chat_message("assistant"):
        st.markdown(bot_response)
    st.session_state.messages.append({"role": "assistant", "content": bot_response})
