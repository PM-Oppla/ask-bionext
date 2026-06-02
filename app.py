import streamlit as st
import openai
import os
from pathlib import Path
import tempfile
import json
# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Ask BIONEXT",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded"
)
# ── Branding / CSS ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
  /* Colour palette */
  :root {
    --blue:  #1A6B7C;
    --green: #8A9A3A;
    --light: #F0F5F5;
  }
  /* Header bar */
  .bionext-header {
    background-color: var(--blue);
    padding: 1rem 2rem;
    border-radius: 8px;
    margin-bottom: 1.5rem;
    display: flex;
    align-items: center;
    gap: 1.2rem;
  }
  .bionext-header h1 {
    color: white;
    font-size: 1.8rem;
    margin: 0;
    font-weight: 700;
    letter-spacing: 0.02em;
  }
  .bionext-header p {
    color: var(--green);
    margin: 0;
    font-size: 0.95rem;
    font-weight: 500;
  }
  /* Chat bubbles */
  .user-msg {
    background-color: var(--blue);
    color: white;
    padding: 0.8rem 1.1rem;
    border-radius: 12px 12px 2px 12px;
    margin: 0.5rem 0 0.5rem 15%;
    font-size: 0.95rem;
  }
  .assistant-msg {
    background-color: white;
    border: 1.5px solid #e0e0e0;
    padding: 0.9rem 1.1rem;
    border-radius: 12px 12px 12px 2px;
    margin: 0.5rem 15% 0.5rem 0;
    font-size: 0.95rem;
    line-height: 1.6;
  }
  .source-tag {
    display: inline-block;
    background-color: var(--green);
    color: var(--blue);
    font-size: 0.72rem;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 10px;
    margin: 2px 3px;
  }
  .sources-line {
    margin-top: 0.6rem;
    font-size: 0.8rem;
    color: #555;
  }
  /* Sidebar */
  [data-testid="stSidebar"] {
    background-color: var(--light);
    border-right: 3px solid var(--green);
  }
  .sidebar-title {
    color: var(--blue);
    font-weight: 700;
    font-size: 1rem;
    margin-bottom: 0.4rem;
  }
  /* Input box */
  .stTextInput input {
    border: 2px solid var(--blue) !important;
    border-radius: 8px !important;
  }
  /* Send button */
  .stButton button {
    background-color: var(--blue) !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    padding: 0.5rem 1.5rem !important;
  }
  .stButton button:hover {
    background-color: var(--green) !important;
    color: var(--blue) !important;
  }
  footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)
# ── Header ─────────────────────────────────────────────────────────────────────
logo_url = "[raw.githubusercontent.com](https://raw.githubusercontent.com/PM-Oppla/ask-bionext/main/bionext-logo.png)"
st.markdown(f"""
<div class="bionext-header">
  <img src="{logo_url}" height="55" style="margin-right:1rem; flex-shrink:0;">
  <div>
    <h1 style="color:white; margin:0; font-size:1.8rem; font-weight:700;">Ask BIONEXT</h1>
    <p style="color:#8A9A3A; margin:0; font-size:0.95rem;">Have a conversation with BIONEXT research · The Biodiversity Nexus: Transformative Change for Sustainability</p>
  </div>
</div>
""", unsafe_allow_html=True)
# ── API key ────────────────────────────────────────────────────────────────────
api_key = st.secrets.get("OPENAI_API_KEY", os.environ.get("OPENAI_API_KEY", ""))
client = openai.OpenAI(api_key=api_key)
# ── Session state ──────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "documents" not in st.session_state:
    st.session_state.documents = {}   # filename → text content
# ── Sidebar: document upload ───────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="sidebar-title">📂 BIONEXT Sources</div>', unsafe_allow_html=True)
    st.markdown("Upload project documents to include as sources.")
    uploaded = st.file_uploader(
        "Upload files",
        type=["pdf", "txt", "docx", "xlsx", "csv", "md"],
        accept_multiple_files=True,
        label_visibility="collapsed"
    )
    if uploaded:
        for f in uploaded:
            if f.name not in st.session_state.documents:
                text = extract_text(f)
                if text:
                    st.session_state.documents[f.name] = text
                    st.success(f"✓ {f.name}")
    if st.session_state.documents:
        st.markdown("---")
        st.markdown('<div class="sidebar-title">Loaded sources</div>', unsafe_allow_html=True)
        for name in st.session_state.documents:
            st.markdown(f"📄 `{name}`")
    st.markdown("---")
    if st.button("🗑 Clear conversation"):
        st.session_state.messages = []
        st.rerun()
# ── Text extraction ────────────────────────────────────────────────────────────
def extract_text(file):
    """Extract plain text from uploaded file."""
    import io
    name = file.name.lower()
    try:
        if name.endswith(".pdf"):
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(file.read()))
            return "\n\n".join(p.extract_text() or "" for p in reader.pages)
        elif name.endswith(".docx"):
            import docx
            doc = docx.Document(io.BytesIO(file.read()))
            return "\n".join(p.text for p in doc.paragraphs)
        elif name.endswith(".xlsx"):
            import openpyxl
            wb = openpyxl.load_workbook(io.BytesIO(file.read()), data_only=True)
            lines = []
            for ws in wb.worksheets:
                lines.append(f"[Sheet: {ws.title}]")
                for row in ws.iter_rows(values_only=True):
                    lines.append("\t".join(str(c) if c is not None else "" for c in row))
            return "\n".join(lines)
        elif name.endswith(".csv"):
            return file.read().decode("utf-8", errors="ignore")
        else:
            return file.read().decode("utf-8", errors="ignore")
    except Exception as e:
        st.warning(f"Could not read {file.name}: {e}")
        return ""
# ── Build context from documents ───────────────────────────────────────────────
def build_context():
    if not st.session_state.documents:
        return ""
    parts = []
    for fname, text in st.session_state.documents.items():
        # Trim very large docs to avoid token overflow
        snippet = text[:6000] if len(text) > 6000 else text
        parts.append(f"=== SOURCE: {fname} ===\n{snippet}\n")
    return "\n".join(parts)
# ── System prompt ───────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are 'Ask BIONEXT', an AI research assistant for the BIONEXT project 
(The Biodiversity Nexus: Transformative Change for Sustainability) — a European Union research 
project exploring how biodiversity interconnects with climate, food, water, energy, transport, 
and health.
Your role is to answer questions by drawing EXCLUSIVELY on the source documents provided to you. 
Do not use any outside knowledge. If the answer is not in the sources, say so clearly.
When you answer:
1. Ground every claim in the source documents
2. At the end of each answer, list which source document(s) you drew from, formatted exactly like this:
   📄 Sources: [filename1], [filename2]
3. Be clear, helpful, and accessible — users may be policymakers, researchers, or members of the public
4. If a question cannot be answered from the sources, say: "I don't have information on that in the 
   current BIONEXT documents. You may find more at bionext-project.eu"
Context documents:
{context}
"""
# ── Chat display ───────────────────────────────────────────────────────────────
chat_container = st.container()
with chat_container:
    if not st.session_state.messages:
        st.markdown("""
        <div class="assistant-msg">
        👋 Welcome! I'm <strong>Ask BIONEXT</strong> — your guide to BIONEXT project research.<br><br>
        Upload your BIONEXT documents in the sidebar, then ask me anything about the project's findings, 
        methods, or outputs. I'll answer based exclusively on the uploaded sources and tell you exactly 
        where the information comes from.
        </div>
        """, unsafe_allow_html=True)
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.markdown(f'<div class="user-msg">{msg["content"]}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="assistant-msg">{msg["content"]}</div>', unsafe_allow_html=True)
# ── Input ──────────────────────────────────────────────────────────────────────
st.markdown("---")
col1, col2 = st.columns([5, 1])
with col1:
    user_input = st.text_input(
        "Your question",
        placeholder="e.g. What are the key findings on biodiversity and food systems?",
        label_visibility="collapsed",
        key="input"
    )
with col2:
    send = st.button("Ask →")
# ── Response logic ─────────────────────────────────────────────────────────────
if send and user_input.strip():
    if not st.session_state.documents:
        st.warning("⚠️ Please upload at least one BIONEXT document in the sidebar first.")
    elif not api_key:
        st.error("⚠️ No OpenAI API key found. Add it to your Streamlit secrets.")
    else:
        st.session_state.messages.append({"role": "user", "content": user_input})
        context = build_context()
        system = SYSTEM_PROMPT.format(context=context)
        with st.spinner("Searching BIONEXT research..."):
            try:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system},
                        *[{"role": m["role"], "content": m["content"]}
                          for m in st.session_state.messages]
                    ],
                    temperature=0.2,
                    max_tokens=1000
                )
                answer = response.choices[0].message.content
                st.session_state.messages.append({"role": "assistant", "content": answer})
            except Exception as e:
                st.error(f"API error: {e}")
        st.rerun()
