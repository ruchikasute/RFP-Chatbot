

from dotenv import load_dotenv
load_dotenv()
import os
import streamlit as st
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from openai import AzureOpenAI
from Modules import  doc_utils, creds

# ------------------------------
# Initialize Azure OpenAI client
# # ------------------------------
api_key = st.secrets.get("AZURE_OPENAI_KEY") or os.getenv("AZURE_OPENAI_KEY")
endpoint = st.secrets.get("AZURE_OPENAI_ENDPOINT") or os.getenv("AZURE_OPENAI_ENDPOINT")
api_version = st.secrets.get("AZURE_OPENAI_API_VERSION") or os.getenv("AZURE_OPENAI_API_VERSION", "2023-03-15-preview")

client = AzureOpenAI(
    api_key=api_key,
    azure_endpoint=endpoint,
    api_version=api_version
)


# ------------------------------
# Streamlit page config
# ------------------------------
st.set_page_config(layout="wide")
st.title("📄 Chat with your Document(s)")


# >>> NEW CODE TO INCREASE SIDEBAR WIDTH <<<
st.markdown(
    """
    <style>
    section[data-testid="stSidebar"] {
        width: 400px !important; 
    }
    </style>
    """,
    unsafe_allow_html=True,
)
# >>> END NEW CODE <<<

# ------------------------------
# Initialize session state
# ------------------------------
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "all_docs" not in st.session_state:
    st.session_state.all_docs = []

# ------------------------------
# Load embedding model once
# ------------------------------
@st.cache_resource
def load_embedding_model():
    return SentenceTransformer('all-MiniLM-L6-v2')

embed_model = load_embedding_model()

# ------------------------------
# SIDEBAR IMPLEMENTATION START
# ------------------------------

with st.sidebar:
    st.header("Document")
    st.write("Upload your Document")
    
    # ------------------------------
    # File uploader moved to sidebar
    # ------------------------------
    uploaded_files = st.file_uploader(
        "Drag and drop file here (PDF, DOCX, TXT)", 
        type=["pdf", "docx", "txt"], 
        accept_multiple_files=True,
        # Optional: Hide the default label for a cleaner look
        label_visibility="collapsed" 
    )
    
    st.markdown("---")

    # ------------------------------
    # Process uploaded files
    # ------------------------------
    if uploaded_files:
        for uploaded_file in uploaded_files:
            existing_files = [doc["name"] for doc in st.session_state.all_docs]
            if uploaded_file.name in existing_files:
                st.info(f"{uploaded_file.name} is already uploaded, skipping.")
                continue

            with st.spinner(f"Processing {uploaded_file.name} and computing embeddings..."):
                sections = doc_utils.extract_sections(uploaded_file)
                section_texts = [s["text"] for s in sections]
                section_embeddings = embed_model.encode(section_texts)

                st.session_state.all_docs.append({
                    "name": uploaded_file.name,
                    "sections": sections,
                    "embeddings": section_embeddings
                })
            st.success(f"Loaded {uploaded_file.name} with {len(sections)} sections")
    
# ------------------------------
# Display previous chat messages
# ------------------------------
# Optional: show older messages if user reloads the page
for msg in st.session_state.chat_history[:-2]:  # exclude last 2 messages already displayed
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if msg.get("context") and msg["role"] == "assistant":
            with st.expander("📑 Sources used for this QA"):
                st.write(msg["context"])



# ------------------------------
# Chat input
# ------------------------------
user_q = st.chat_input("Ask a question about your document(s)...")
if user_q:
    # 1️⃣ Append user message to session history
    st.session_state.chat_history.append({
        "role": "user",
        "content": user_q,
        "context": None
    })

    # 2️⃣ Display user message immediately
    # st.chat_message("user").write(user_q)
    st.chat_message("user").write(f"**{user_q}**")


    # 3️⃣ Create placeholder for assistant
    assistant_placeholder = st.empty()
    with assistant_placeholder.container():
        with st.chat_message("assistant"):
            st.write("⏳ Thinking...")

    # ------------------------------
    # Generate context using embeddings
    # ------------------------------
    q_emb = embed_model.encode([user_q])
    all_texts = [sec["text"] for doc in st.session_state.all_docs for sec in doc["sections"]]
    all_meta = [(doc["name"], sec["header"]) for doc in st.session_state.all_docs for sec in doc["sections"]]
    all_embeddings = [emb for doc in st.session_state.all_docs for emb in doc["embeddings"]]

    sims = cosine_similarity(q_emb, all_embeddings)[0]
    top_idx = sims.argsort()[-10:][::-1]  # top 10 relevant sections

    context = "\n\n".join([
        f"📄 Doc: {all_meta[i][0]} | Section: {all_meta[i][1]}\n{all_texts[i]}"
        for i in top_idx
    ])

    prompt = f"""
Use the context below to answer the question in a detailed and comprehensive manner. 
Summarize the main points related to the question and provide specifics from the documents if available. 
If the answer is not found in the documents, state that clearly.

Context:
{context}

Question: {user_q}
"""

    # ------------------------------
    # Call Azure OpenAI
    # ------------------------------
    try:
        response = client.chat.completions.create(
            model="Codetest",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500
        )
        answer = response.choices[0].message.content
    except Exception as e:
        answer = f"⚠️ Error from Azure OpenAI: {e}"

    # ------------------------------
    # Replace placeholder with actual answer + expander
    # ------------------------------
    with assistant_placeholder.container():
        with st.chat_message("assistant"):
            st.write(answer)


            with st.expander("📑 Sources used for this QA"):
                st.write(context)

    # ------------------------------
    # Append assistant response to session history
    # ------------------------------
    st.session_state.chat_history.append({
        "role": "assistant",
        "content": answer,
        "context": context
    })

