import streamlit as st
from groq import Groq
from pypdf import PdfReader

MODEL = "openai/gpt-oss-20b"
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

st.set_page_config(page_title="Study Buddy", page_icon="📚", layout="wide")

SAMPLE = """Extended Slicing: It is an extension of slicing. Syntax: variable[start_index:end_index:step].
Along with start_index and end_index we also provide a step. The step decides the increment between each index.
A negative step moves backwards, so variable[::-1] reverses a string. A step of 0 is not allowed in Python."""

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700;800&display=swap');

html, body, [class*="css"] { font-family: 'Poppins', sans-serif; }
.stApp {
    background: radial-gradient(circle at top left, #2b1a6b 0%, #0f0c29 45%, #090716 100%);
    color: #f1f1ff;
}
#MainMenu, footer { visibility: hidden; }
.stApp p, .stApp label, .stApp span, .stApp li { color: #e9e9ff; }
.block-container { padding-top: 2rem; max-width: 1100px; }

/* Animated hero */
.hero {
    background: linear-gradient(120deg, #6C63FF, #3EC6E0, #ff6ec4, #6C63FF);
    background-size: 300% 300%;
    animation: gradientMove 8s ease infinite;
    padding: 2.8rem 1.5rem; border-radius: 22px; text-align: center;
    box-shadow: 0 12px 40px rgba(108, 99, 255, 0.45);
    margin-bottom: 1.5rem;
}
.hero h1 { margin: 0; font-size: 3.2rem; font-weight: 800; color: white !important; }
.hero p { margin: 0.6rem 0 0; font-size: 1.2rem; color: white !important; opacity: 0.95; }
.badge {
    display: inline-block; margin-top: 1rem; padding: 0.35rem 1rem;
    border-radius: 999px; background: rgba(255,255,255,0.22);
    color: white !important; font-size: 0.85rem; font-weight: 600;
}
@keyframes gradientMove {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}

/* Feature cards */
.card {
    background: rgba(255,255,255,0.07); border: 1px solid rgba(255,255,255,0.15);
    border-radius: 18px; padding: 1.2rem; text-align: center;
    backdrop-filter: blur(8px); transition: transform 0.25s, box-shadow 0.25s;
    height: 100%;
}
.card:hover { transform: translateY(-6px); box-shadow: 0 10px 30px rgba(62, 198, 224, 0.35); }
.card .icon { font-size: 2.2rem; }
.card h4 { margin: 0.4rem 0 0.2rem; color: white !important; }
.card p { margin: 0; font-size: 0.9rem; opacity: 0.85; }

/* Inputs */
.stTextArea textarea {
    background: rgba(255,255,255,0.07) !important; color: white !important;
    border: 1px solid rgba(255,255,255,0.2) !important; border-radius: 14px !important;
}
[data-testid="stFileUploader"] section {
    background: rgba(255,255,255,0.06); border: 2px dashed #6C63FF; border-radius: 14px;
}
.stTabs [data-baseweb="tab"] { font-weight: 600; font-size: 1rem; }

/* Buttons */
.stButton > button {
    background: linear-gradient(90deg, #6C63FF, #3EC6E0); color: white; border: none;
    border-radius: 14px; padding: 0.7rem 1.2rem; font-weight: 700; font-size: 1.05rem;
    transition: transform 0.2s, box-shadow 0.2s;
}
.stButton > button:hover {
    transform: scale(1.03); box-shadow: 0 0 25px rgba(108, 99, 255, 0.8); color: white;
}

/* Result card */
.result {
    background: rgba(255,255,255,0.08); border-left: 6px solid #3EC6E0;
    border-radius: 16px; padding: 1.2rem 1.5rem; margin-top: 0.5rem;
}
.chip {
    display: inline-block; padding: 0.25rem 0.8rem; border-radius: 999px;
    background: rgba(108, 99, 255, 0.35); font-size: 0.85rem; margin-right: 0.4rem;
}
</style>
""", unsafe_allow_html=True)

# ---------- Sidebar ----------
with st.sidebar:
    st.header("📚 Study Buddy")
    st.write("AI study assistant")
    st.info("☁️ Cloud version\n\n🔓 Open-weights Llama model\n\n💸 Free and open source")
    st.warning("Notes are sent to Groq to get the answer. Use the offline version for private notes.")
    st.divider()
    st.caption("Team: Sanchita, Sachi, Sakshi, Sanjana")
    st.caption("HackoberFest 2026")

# ---------- Hero ----------
st.markdown("""
<div class="hero">
  <h1>📚 Study Buddy</h1>
  <p>Turn messy notes into summaries, quizzes and simple explanations in seconds.</p>
  <span class="badge">🚀 Open-weights AI · HackoberFest 2026</span>
</div>
""", unsafe_allow_html=True)

# ---------- Feature cards ----------
c1, c2, c3 = st.columns(3)
c1.markdown('<div class="card"><div class="icon">📝</div><h4>Summarize</h4><p>5 clear bullet points from any notes</p></div>', unsafe_allow_html=True)
c2.markdown('<div class="card"><div class="icon">❓</div><h4>Quiz Me</h4><p>Practice questions with answers</p></div>', unsafe_allow_html=True)
c3.markdown('<div class="card"><div class="icon">🧒</div><h4>Explain Simply</h4><p>Hard topics in easy words</p></div>', unsafe_allow_html=True)

st.write("")

# ---------- Input ----------
def load_sample():
    st.session_state["typed"] = SAMPLE

tab1, tab2 = st.tabs(["✍️ Paste notes", "📄 Upload PDF"])

with tab1:
    typed = st.text_area("Paste your notes here", height=200, key="typed",
                         placeholder="Paste your class notes here...")
    st.button("✨ Try sample notes", on_click=load_sample)

pdf_text = ""
with tab2:
    uploaded = st.file_uploader("Drop a PDF here", type="pdf")
    if uploaded:
        reader = PdfReader(uploaded)
        pdf_text = "\n".join(page.extract_text() or "" for page in reader.pages)
        st.success(f"✅ PDF loaded: {len(reader.pages)} pages")

notes = pdf_text if pdf_text else typed
if notes.strip():
    st.markdown(f'<span class="chip">📝 {len(notes.split())} words ready</span>', unsafe_allow_html=True)

# ---------- Mode ----------
mode = st.radio(
    "Choose what you want",
    ["📝 Summarize", "❓ Make a quiz", "🧒 Explain like I'm 5"],
    horizontal=True,
)

prompts = {
    "📝 Summarize": "Summarize these notes in 5 short bullet points. Put each bullet on a new line starting with '- ':\n\n",
    "❓ Make a quiz": "Create 5 quiz questions with answers from these notes:\n\n",
    "🧒 Explain like I'm 5": "Explain these notes in very simple words:\n\n",
}

go = st.button("🚀 Generate", use_container_width=True)

# ---------- Run the AI ----------
if go:
    if not notes.strip():
        st.warning("Please paste notes, try the sample notes, or upload a PDF first.")
    else:
        try:
            with st.spinner("🤔 Thinking..."):
                reply = client.chat.completions.create(
                    model=MODEL,
                    messages=[{"role": "user",
                               "content": prompts[mode] + notes[:6000]}],
                )
            st.session_state["answer"] = reply.choices[0].message.content.replace("•", "\n- ")
            st.session_state["mode"] = mode
            st.toast("Done! Your answer is ready 🎉")
        except Exception as e:
            st.error(f"Could not get a response: {e}")

# ---------- Result ----------
if "answer" in st.session_state:
    st.markdown(f"### ✅ Result: {st.session_state['mode']}")
    st.markdown('<div class="result">', unsafe_allow_html=True)
    st.markdown(st.session_state["answer"])
    st.markdown('</div>', unsafe_allow_html=True)
    st.download_button("⬇️ Download answer", st.session_state["answer"],
                       file_name="studybuddy_answer.txt")
