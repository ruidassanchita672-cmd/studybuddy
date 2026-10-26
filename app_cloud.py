import json
import re
import time
from datetime import datetime, timedelta, timezone

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from groq import Groq
from pypdf import PdfReader

MODEL = "openai/gpt-oss-20b"
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

IST = timezone(timedelta(hours=5, minutes=30))
CHUNK_CHARS = 6000
MAX_CHUNKS = 8
CHAT_CHARS = 20000
MAX_HISTORY = 30

st.set_page_config(page_title="Study Buddy", page_icon="📚", layout="wide")

SAMPLE = """Extended Slicing: It is an extension of slicing. Syntax: variable[start_index:end_index:step].
Along with start_index and end_index we also provide a step. The step decides the increment between each index.
A negative step moves backwards, so variable[::-1] reverses a string. A step of 0 is not allowed in Python."""

for k, v in {"history": [], "log": [], "chat": []}.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ---------- Helpers ----------
def now():
    return datetime.now(IST)


def ask_ai(prompt):
    for attempt in range(2):
        try:
            r = client.chat.completions.create(
                model=MODEL, messages=[{"role": "user", "content": prompt}]
            )
            return (r.choices[0].message.content or "").strip()
        except Exception:
            if attempt == 1:
                raise
            time.sleep(4)


def ask_chat(history, notes):
    system = (
        "You are Study Buddy, a friendly tutor. Answer using the student's notes below. "
        "If the answer is not in the notes, say so briefly, then give a short general explanation. "
        "Keep answers clear and short.\n\nNOTES:\n" + notes[:CHAT_CHARS]
    )
    msgs = [{"role": "system", "content": system}] + history[-10:]
    for attempt in range(2):
        try:
            r = client.chat.completions.create(model=MODEL, messages=msgs)
            return (r.choices[0].message.content or "").strip()
        except Exception:
            if attempt == 1:
                raise
            time.sleep(4)


def read_pdf(file):
    reader = PdfReader(file)
    if reader.is_encrypted:
        try:
            if reader.decrypt("") == 0:
                return "", len(reader.pages), "locked"
        except Exception:
            return "", len(reader.pages), "locked"
    pages = []
    for p in reader.pages:
        try:
            pages.append(p.extract_text() or "")
        except Exception:
            pages.append("")
    return "\n".join(pages), len(reader.pages), "ok"


def split_chunks(text):
    chunks, cur = [], ""
    for line in text.split("\n"):
        while len(line) > CHUNK_CHARS:
            if cur:
                chunks.append(cur)
                cur = ""
            chunks.append(line[:CHUNK_CHARS])
            line = line[CHUNK_CHARS:]
        if len(cur) + len(line) + 1 > CHUNK_CHARS and cur:
            chunks.append(cur)
            cur = ""
        cur += line + "\n"
    if cur.strip():
        chunks.append(cur)
    return chunks


def prepare(text, progress):
    text = "\n".join(l.strip() for l in text.splitlines() if l.strip())
    if len(text) <= CHUNK_CHARS:
        return text, None
    chunks = split_chunks(text)
    total = len(chunks)
    note = None
    if total > MAX_CHUNKS:
        idx = [round(i * (total - 1) / (MAX_CHUNKS - 1)) for i in range(MAX_CHUNKS)]
        chunks = [chunks[i] for i in idx]
        note = f"Large file: used {MAX_CHUNKS} sections spread across all {total}."
    points = []
    for i, c in enumerate(chunks):
        progress.progress((i + 1) / len(chunks), text=f"Reading section {i + 1} of {len(chunks)}...")
        points.append(ask_ai(
            "Extract the key points, definitions and facts from this part of study notes "
            "as short bullet points:\n\n" + c))
    progress.empty()
    return "\n\n".join(points), note


def record_history(mode, answer, title):
    t = now()
    st.session_state["history"].insert(0, {
        "time": t.strftime("%d %b %Y, %I:%M %p"),
        "date": t.strftime("%Y-%m-%d"),
        "mode": mode,
        "title": title,
        "answer": answer,
    })
    del st.session_state["history"][MAX_HISTORY:]
    st.session_state["log"].append({"date": t.strftime("%Y-%m-%d"), "kind": mode})


def calc_streak(dates):
    days = set(dates)
    d = now().date()
    if d.strftime("%Y-%m-%d") not in days:
        d -= timedelta(days=1)
    streak = 0
    while d.strftime("%Y-%m-%d") in days:
        streak += 1
        d -= timedelta(days=1)
    return streak


# ---------- Text to speech (uses the browser's built-in voice) ----------
TTS_HTML = """
<div style="font-family:sans-serif;display:flex;gap:8px;align-items:center;flex-wrap:wrap">
  <button id="play">🔊 Listen</button>
  <button id="pause">⏸️ Pause / Resume</button>
  <button id="stop">⏹️ Stop</button>
  <select id="rate">
    <option value="0.8">Slow</option>
    <option value="1" selected>Normal</option>
    <option value="1.25">Fast</option>
  </select>
  <span id="msg" style="color:#e9e9ff;font-size:13px"></span>
</div>
<style>
  button { background: linear-gradient(90deg,#6C63FF,#3EC6E0); color:white; border:none;
           border-radius:10px; padding:8px 14px; font-weight:700; cursor:pointer; }
  select { padding:7px; border-radius:10px; }
</style>
<script>
  const text = __TEXT__;
  const synth = window.speechSynthesis;
  const msg = document.getElementById('msg');
  if (!synth) { msg.textContent = 'Speech is not supported in this browser. Try Chrome or Edge.'; }

  function chunks(t) {
    const parts = t.match(/[^.!?]+[.!?]*\\s*/g) || [t];
    const out = []; let cur = "";
    for (const p of parts) {
      if ((cur + p).length > 200 && cur) { out.push(cur); cur = ""; }
      cur += p;
    }
    if (cur) out.push(cur);
    return out;
  }

  document.getElementById('play').onclick = () => {
    if (!synth) return;
    synth.cancel();
    const rate = parseFloat(document.getElementById('rate').value);
    chunks(text).forEach(c => {
      const u = new SpeechSynthesisUtterance(c);
      u.rate = rate;
      u.lang = 'en-IN';
      synth.speak(u);
    });
  };
  document.getElementById('pause').onclick = () => {
    if (!synth) return;
    if (synth.speaking && !synth.paused) synth.pause(); else synth.resume();
  };
  document.getElementById('stop').onclick = () => { if (synth) synth.cancel(); };
  window.addEventListener('beforeunload', () => { if (synth) synth.cancel(); });
</script>
"""


def clean_for_speech(text):
    text = re.sub(r"[*_`#>]", "", text)
    text = re.sub(r"^\s*[-•]\s*", "", text, flags=re.M)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def speak_widget(text):
    clean = clean_for_speech(text or "")
    if not clean:
        return
    payload = json.dumps(clean).replace("</", "<\\/")
    components.html(TTS_HTML.replace("__TEXT__", payload), height=70)
# ---------- Style ----------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700;800&display=swap');
html, body, [class*="css"] { font-family: 'Poppins', sans-serif; }
.stApp { background: radial-gradient(circle at top left, #2b1a6b 0%, #0f0c29 45%, #090716 100%); color: #f1f1ff; }
#MainMenu, footer { visibility: hidden; }
.stApp p, .stApp label, .stApp span, .stApp li { color: #e9e9ff; }
.block-container { padding-top: 2rem; max-width: 1100px; }
.hero { background: linear-gradient(120deg, #6C63FF, #3EC6E0, #ff6ec4, #6C63FF); background-size: 300% 300%;
    animation: gradientMove 8s ease infinite; padding: 2.4rem 1.5rem; border-radius: 22px; text-align: center;
    box-shadow: 0 12px 40px rgba(108, 99, 255, 0.45); margin-bottom: 1.5rem; }
.hero h1 { margin: 0; font-size: 3rem; font-weight: 800; color: white !important; }
.hero p { margin: 0.6rem 0 0; font-size: 1.15rem; color: white !important; opacity: 0.95; }
.badge { display: inline-block; margin-top: 1rem; padding: 0.35rem 1rem; border-radius: 999px;
    background: rgba(255,255,255,0.22); color: white !important; font-size: 0.85rem; font-weight: 600; }
@keyframes gradientMove { 0% {background-position: 0% 50%;} 50% {background-position: 100% 50%;} 100% {background-position: 0% 50%;} }
.stTextArea textarea, .stTextInput input { background: rgba(255,255,255,0.07) !important; color: white !important;
    border: 1px solid rgba(255,255,255,0.2) !important; border-radius: 14px !important; }
[data-testid="stFileUploader"] section { background: rgba(255,255,255,0.06); border: 2px dashed #6C63FF; border-radius: 14px; }
.stTabs [data-baseweb="tab"] { font-weight: 600; font-size: 1rem; }
.stButton > button, .stDownloadButton > button { background: linear-gradient(90deg, #6C63FF, #3EC6E0); color: white; border: none;
    border-radius: 14px; padding: 0.6rem 1.2rem; font-weight: 700; transition: transform 0.2s, box-shadow 0.2s; }
.stButton > button:hover, .stDownloadButton > button:hover { transform: scale(1.03); box-shadow: 0 0 25px rgba(108, 99, 255, 0.8); color: white; }
.result { background: rgba(255,255,255,0.08); border-left: 6px solid #3EC6E0; border-radius: 16px;
    padding: 1.2rem 1.5rem; margin-top: 0.5rem; }
.chip { display: inline-block; padding: 0.3rem 0.9rem; border-radius: 999px;
    background: rgba(108, 99, 255, 0.35); font-size: 0.9rem; margin: 0.2rem 0.4rem 0.2rem 0; }
[data-testid="stMetric"] { background: rgba(255,255,255,0.07); border: 1px solid rgba(255,255,255,0.15);
    border-radius: 16px; padding: 0.8rem 1rem; }
[data-testid="stMetricValue"] { color: white; }
</style>
""", unsafe_allow_html=True)

# ---------- Sidebar ----------
with st.sidebar:
    st.header("📚 Study Buddy")
    st.write("AI study assistant")
    st.slider("🎯 Daily goal (sessions)", 1, 10, 3, key="goal")
    st.info("☁️ Cloud version\n\n🔓 Open-weights AI model (GPT-OSS)\n\n💸 Free and open source")
    st.warning("Notes are sent to Groq to get the answer. Use the offline version for private notes.")
    st.caption("History and streak stay in this browser session. Use Export progress (Progress tab) to keep them.")
    st.divider()
    st.caption("Team: Sanchita, Sachi, Sakshi, Sanjana")
    st.caption("HackoberFest 2026")

# ---------- Hero ----------
st.markdown("""
<div class="hero">
  <h1>📚 Study Buddy</h1>
  <p>Summaries, quizzes, flashcards, chat and daily tracking, all from your own notes.</p>
  <span class="badge">🚀 Open-weights AI · HackoberFest 2026</span>
</div>
""", unsafe_allow_html=True)

# ---------- Notes input ----------
def load_sample():
    st.session_state["typed"] = SAMPLE


st.markdown("### 1️⃣ Add your notes")
in1, in2 = st.tabs(["✍️ Paste notes", "📄 Upload PDF or TXT"])

with in1:
    typed = st.text_area("Paste your notes here", height=180, key="typed",
                         placeholder="Paste your class notes here...")
    st.button("✨ Try sample notes", on_click=load_sample)

file_text = ""
with in2:
    uploaded = st.file_uploader("Drop a PDF or TXT file here", type=["pdf", "txt"])
    if uploaded:
        try:
            if uploaded.name.lower().endswith(".pdf"):
                file_text, pages, status = read_pdf(uploaded)
                if status == "locked":
                    st.error("🔒 This PDF is password-protected. Remove the password or paste the text instead.")
                elif not file_text.strip():
                    st.warning("⚠️ No readable text found. This looks like a scanned PDF. "
                               "Paste the text instead, or open it in Google Drive with 'Open with Google Docs'.")
                else:
                    st.success(f"✅ PDF loaded: {pages} pages")
            else:
                file_text = uploaded.read().decode("utf-8", errors="ignore")
                st.success("✅ Text file loaded")
        except Exception:
            st.error("Could not read this file. Try another file or paste the text.")

notes = file_text if file_text.strip() else typed
if notes.strip():
    st.markdown(f'<span class="chip">📝 {len(notes.split())} words ready</span>', unsafe_allow_html=True)

st.markdown("### 2️⃣ Learn")
tab_tools, tab_chat, tab_prog, tab_hist = st.tabs(
    ["🛠️ Study tools", "💬 Chat with notes", "📅 Progress", "🕘 History"]
)

# ---------- Study tools ----------
prompts = {
    "📝 Summarize": "Summarize these notes in 5 short bullet points. Put each bullet on a new line starting with '- ':\n\n",
    "❓ Make a quiz": "Create 5 quiz questions with answers from these notes:\n\n",
    "🧒 Explain like I'm 5": "Explain these notes in very simple words:\n\n",
    "🃏 Flashcards": "Create 8 flashcards from these notes. Format each as:\n**Q:** question\n**A:** answer\n\n",
    "🔑 Key terms": "List the 8 most important key terms from these notes, each with a one-line simple definition. Use '- **term**: definition':\n\n",
}

with tab_tools:
    mode = st.radio("Choose what you want", list(prompts.keys()), horizontal=True)
    go = st.button("🚀 Generate", use_container_width=True)

    if go:
        if not notes.strip():
            st.warning("Please add notes first: paste, try the sample, or upload a file.")
        else:
            try:
                progress = st.progress(0.0, text="Starting...")
                prepared, note = prepare(notes, progress)
                with st.spinner("🤔 Thinking..."):
                    answer = ask_ai(prompts[mode] + prepared)
                if not answer:
                    st.error("The AI returned an empty answer. Please click Generate again.")
                else:
                    answer = answer.replace("•", "\n- ")
                    title = (notes.strip().split("\n")[0])[:50]
                    st.session_state["answer"] = answer
                    st.session_state["mode"] = mode
                    st.session_state["note"] = note
                    record_history(mode, answer, title)
                    st.toast("Done! Saved to History 🎉")
            except Exception as e:
                st.error(f"Could not get a response. Wait a minute and try again. ({e})")

    if "answer" in st.session_state:
        st.markdown(f"### ✅ Result: {st.session_state['mode']}")
        if st.session_state.get("note"):
            st.caption(st.session_state["note"])
        st.markdown('<div class="result">', unsafe_allow_html=True)
        st.markdown(st.session_state["answer"])
        st.markdown('</div>', unsafe_allow_html=True)
        st.download_button("⬇️ Download answer", st.session_state["answer"],
                           file_name="studybuddy_answer.txt")

# ---------- Chat ----------
with tab_chat:
    st.caption("Ask anything about your notes, like ChatGPT. Answers come from the notes you added above.")
    if not notes.strip():
        st.info("Add notes above first, then ask questions here.")
    for m in st.session_state["chat"]:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])
    q = st.chat_input("Ask a question about your notes...")
    if q:
        if not notes.strip():
            st.warning("Please add notes first.")
        else:
            st.session_state["chat"].append({"role": "user", "content": q})
            with st.chat_message("user"):
                st.markdown(q)
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    try:
                        reply = ask_chat(st.session_state["chat"], notes)
                    except Exception:
                        reply = "Sorry, I could not answer right now. Please try again in a minute."
                st.markdown(reply or "I could not find an answer. Please try rephrasing.")
            st.session_state["chat"].append({"role": "assistant", "content": reply})
            st.session_state["log"].append({"date": now().strftime("%Y-%m-%d"), "kind": "💬 Chat"})
    if st.session_state["chat"] and st.button("🧹 Clear chat"):
        st.session_state["chat"] = []
        st.rerun()

# ---------- Progress ----------
with tab_prog:
    log = st.session_state["log"]
    today = now().strftime("%Y-%m-%d")
    goal = st.session_state.get("goal", 3)
    today_count = sum(1 for e in log if e.get("date") == today)
    streak = calc_streak([e.get("date") for e in log if e.get("date")])

    m1, m2, m3 = st.columns(3)
    m1.metric("Today", f"{today_count} / {goal}")
    m2.metric("🔥 Study streak", f"{streak} day(s)")
    m3.metric("Total sessions", len(log))

    st.progress(min(today_count / goal, 1.0), text=f"Daily goal: {today_count} of {goal} sessions")
    if today_count >= goal:
        st.success("🎉 Daily goal reached. Great work!")

    days = [now().date() - timedelta(days=i) for i in range(6, -1, -1)]
    df = pd.DataFrame(
        {"Sessions": [sum(1 for e in log if e.get("date") == d.strftime("%Y-%m-%d")) for d in days]},
        index=[d.strftime("%m-%d") for d in days],
    )
    st.markdown("**Last 7 days**")
    st.bar_chart(df)

    total = len(log)
    badges = []
    if total >= 1:
        badges.append("🥉 First step")
    if total >= 5:
        badges.append("🥈 5 sessions")
    if total >= 15:
        badges.append("🥇 15 sessions")
    if streak >= 3:
        badges.append("🔥 3-day streak")
    if streak >= 7:
        badges.append("🏆 7-day streak")
    if badges:
        st.markdown("**Badges**")
        st.markdown("".join(f'<span class="chip">{b}</span>' for b in badges), unsafe_allow_html=True)
    else:
        st.caption("Generate your first result to earn a badge.")

    st.divider()
    st.markdown("**Save or restore your progress**")
    export = json.dumps({"history": st.session_state["history"], "log": st.session_state["log"]}, indent=2)
    st.download_button("💾 Export progress", export, file_name="studybuddy_progress.json")
    imp = st.file_uploader("Import saved progress (.json)", type="json", key="imp")
    if imp:
        sig = f"{imp.name}-{imp.size}"
        if st.session_state.get("imported") != sig:
            try:
                data = json.loads(imp.read().decode("utf-8"))
                hist_in, log_in = data.get("history", []), data.get("log", [])
                if isinstance(hist_in, list) and isinstance(log_in, list):
                    st.session_state["history"] = hist_in[:MAX_HISTORY]
                    st.session_state["log"] = log_in
                    st.session_state["imported"] = sig
                    st.toast("Progress restored ✅")
                    st.rerun()
                else:
                    st.error("That file is not a Study Buddy progress file.")
            except Exception:
                st.error("Could not read that file.")

# ---------- History ----------
with tab_hist:
    hist = st.session_state["history"]
    if not hist:
        st.info("No history yet. Generate something and it will appear here.")
    else:
        search = st.text_input("🔍 Search history", placeholder="Type a word...")
        st.caption(f"{len(hist)} saved results, newest first")
        for i, h in enumerate(hist):
            text_blob = f"{h.get('title', '')} {h.get('answer', '')} {h.get('mode', '')}".lower()
            if search.lower() not in text_blob:
                continue
            with st.expander(f"{h.get('mode', '')} · {h.get('title', '')} · {h.get('time', '')}"):
                st.markdown(h.get("answer", ""))
                st.download_button("⬇️ Download", h.get("answer", ""),
                                   file_name=f"studybuddy_{i + 1}.txt", key=f"dl{i}")
        if st.button("🗑️ Clear history"):
            st.session_state["history"] = []
            st.rerun()
