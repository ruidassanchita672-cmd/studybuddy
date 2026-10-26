import streamlit as st
from groq import Groq
from pypdf import PdfReader

MODEL = "llama-3.1-8b-instant"  # if you get a "model" error, check Groq's models page for a current Llama name
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

st.set_page_config(page_title="Study Buddy", page_icon="📚", layout="wide")

st.markdown("""
<style>
.hero {
    background: linear-gradient(135deg, #6C63FF, #3EC6E0);
    padding: 2rem; border-radius: 16px; text-align: center;
    margin-bottom: 1.5rem;
}
.hero h1 { margin: 0; font-size: 2.6rem; color: white; }
.hero p { margin: 0.4rem 0 0; font-size: 1.15rem; color: white; opacity: 0.95; }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.header("📚 Study Buddy")
    st.write("AI study assistant")
    st.info("☁️ Cloud version\n\n🔓 Open-weights Llama model\n\n💸 Free and open source")
    st.warning("Your notes are sent to Groq to get the answer. Use the offline version for private notes.")
    st.divider()
    st.caption("Team: Sanchita, Sachi, Sakshi, Sanjana")

st.markdown(
    '<div class="hero"><h1>📚 Study Buddy</h1>'
    '<p>Paste notes. Get summaries, quizzes and simple explanations.</p></div>',
    unsafe_allow_html=True,
)

tab1, tab2 = st.tabs(["✍️ Paste notes", "📄 Upload PDF"])

with tab1:
    typed = st.text_area("Paste your notes here", height=220,
                         placeholder="Paste your class notes here...")

pdf_text = ""
with tab2:
    uploaded = st.file_uploader("Upload a PDF", type="pdf")
    if uploaded:
        reader = PdfReader(uploaded)
        pdf_text = "\n".join(page.extract_text() or "" for page in reader.pages)
        st.success(f"✅ PDF loaded: {len(reader.pages)} pages")

notes = pdf_text if pdf_text else typed
if notes.strip():
    st.caption(f"📝 {len(notes.split())} words ready")

mode = st.radio(
    "What do you want?",
    ["📝 Summarize", "❓ Make a quiz", "🧒 Explain like I'm 5"],
    horizontal=True,
)

prompts = {
    "📝 Summarize": "Summarize these notes in 5 short bullet points. Put each bullet on a new line starting with '- ':\n\n",
    "❓ Make a quiz": "Create 5 quiz questions with answers from these notes:\n\n",
    "🧒 Explain like I'm 5": "Explain these notes in very simple words:\n\n",
}

go = st.button("✨ Generate", type="primary", use_container_width=True)

if go:
    if not notes.strip():
        st.warning("Please paste notes or upload a PDF first.")
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
        except Exception as e:
            st.error(f"Could not get a response: {e}")

if "answer" in st.session_state:
    st.subheader(f"Result: {st.session_state['mode']}")
    with st.container(border=True):
        st.markdown(st.session_state["answer"])
    st.download_button("⬇️ Download answer", st.session_state["answer"],
                       file_name="studybuddy_answer.txt")