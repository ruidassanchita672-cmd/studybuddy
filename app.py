import streamlit as st
import ollama
from pypdf import PdfReader

MODEL = "llama3.2:3b"

st.title("📚 Study Buddy (Offline AI)")
st.caption("Runs 100% on your laptop with open-source AI. No internet needed, no data leaves your device.")

uploaded = st.file_uploader("Upload a PDF (optional)", type="pdf")
notes = st.text_area("Or paste your notes here", height=250)

if uploaded:
    reader = PdfReader(uploaded)
    notes = "\n".join(page.extract_text() or "" for page in reader.pages)
    st.success(f"PDF loaded: {len(reader.pages)} pages")

mode = st.selectbox("What do you want?", ["Summarize", "Make a quiz", "Explain like I'm 5"])

prompts = {
    "Summarize": "Summarize these notes in 5 short bullet points. Put each bullet on a new line starting with '- ':\n\n",
    "Make a quiz": "Create 5 quiz questions with answers from these notes:\n\n",
    "Explain like I'm 5": "Explain these notes in very simple words:\n\n",
}

if st.button("Go") and notes:
    with st.spinner("Thinking..."):
        reply = ollama.chat(
            model=MODEL,
            messages=[{"role": "user", "content": prompts[mode] + notes[:6000]}],
        )
    st.markdown(reply["message"]["content"].replace("•", "\n- "))