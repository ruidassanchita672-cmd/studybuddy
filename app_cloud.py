import base64, json, re, time
from datetime import datetime, timedelta, timezone
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from groq import Groq
from pypdf import PdfReader

TEXT_MODEL = "openai/gpt-oss-20b"
VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"  # reads photos
STT_MODEL = "whisper-large-v3-turbo"                        # mic to text
client = Groq(api_key=st.secrets["GROQ_API_KEY"])
IST = timezone(timedelta(hours=5, minutes=30))
CH, MAXC, STEPS = 6000, 8, [1, 3, 7, 14, 30]

st.set_page_config(page_title="Study Buddy", page_icon="📚", layout="wide")
S = st.session_state
for k, v in {"history": [], "log": [], "chat": [], "extra": "", "rev": [], "scores": [],
             "quiz": None, "qid": 0, "cards": None, "ci": 0, "show": False, "seen": ""}.items():
    S.setdefault(k, v)

def today(): return datetime.now(IST).date()
def ds(d): return d.strftime("%Y-%m-%d")
def log(kind): S["log"].append({"date": ds(today()), "kind": kind})

def llm(msgs, model=TEXT_MODEL):
    for a in range(2):
        try:
            r = client.chat.completions.create(model=model, messages=msgs)
            return (r.choices[0].message.content or "").strip()
        except Exception:
            if a: raise
            time.sleep(3)

def ask(p): return llm([{"role": "user", "content": p}])

def ask_json(p):
    for _ in range(2):
        m = re.search(r"(\[.*\]|\{.*\})", ask(p + "\n\nReply with ONLY valid JSON, no other text."), re.S)
        try: return json.loads(m.group(1))
        except Exception: pass

def ocr(files):
    out = []
    for f in files:
        b = base64.b64encode(f.getvalue()).decode()
        out.append(llm([{"role": "user", "content": [
            {"type": "text", "text": "Transcribe all text in this image. If it is a diagram, describe it as study notes. Output only the text."},
            {"type": "image_url", "image_url": {"url": f"data:{f.type or 'image/jpeg'};base64,{b}"}}]}], VISION_MODEL))
    return "\n\n".join(out)

def stt(a):
    return client.audio.transcriptions.create(file=("rec.wav", a.getvalue()), model=STT_MODEL).text

def read_pdf(f):
    r = PdfReader(f)
    if r.is_encrypted and r.decrypt("") == 0: return "", 0, "locked"
    t = []
    for p in r.pages:
        try: t.append(p.extract_text() or "")
        except Exception: t.append("")
    return "\n".join(t), len(r.pages), "ok"

def prepare(text, prog):
    if len(text) <= CH: return text, None
    ch = [text[i:i + CH] for i in range(0, len(text), CH)]
    note = None
    if len(ch) > MAXC:
        note = f"Large file: used {MAXC} of {len(ch)} sections."
        ch = [ch[round(i * (len(ch) - 1) / (MAXC - 1))] for i in range(MAXC)]
    pts = []
    for i, c in enumerate(ch):
        prog.progress((i + 1) / len(ch), text=f"Reading section {i + 1} of {len(ch)}...")
        pts.append(ask("Extract key points, definitions and facts as short bullets:\n\n" + c))
    prog.empty()
    return "\n\n".join(pts), note

def streak():
    days = {e["date"] for e in S["log"]}
    d = today()
    if ds(d) not in days: d -= timedelta(days=1)
    n = 0
    while ds(d) in days: n += 1; d -= timedelta(days=1)
    return n

def speak(text):
    t = re.sub(r"\s+", " ", re.sub(r"[*_`#>|]", "", text or "")).strip()
    if not t: return
    h = '''<div style="display:flex;gap:8px"><button onclick="go()">🔊 Listen</button><button onclick="speechSynthesis.cancel()">⏹️ Stop</button></div>
<style>button{background:linear-gradient(90deg,#6C63FF,#3EC6E0);color:#fff;border:0;border-radius:10px;padding:8px 14px;font-weight:700;cursor:pointer}</style>
<script>const T=__T__;function go(){speechSynthesis.cancel();(T.match(/[^.!?]+[.!?]*/g)||[T]).forEach(s=>{const u=new SpeechSynthesisUtterance(s);u.lang="en-IN";speechSynthesis.speak(u)})}</script>'''
    components.html(h.replace("__T__", json.dumps(t).replace("</", "<\\/")), height=55)

st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;800&display=swap');
html,body,[class*="css"]{font-family:'Poppins',sans-serif}
.stApp{background:radial-gradient(circle at top left,#2b1a6b 0%,#0f0c29 45%,#090716 100%)}
#MainMenu,footer{visibility:hidden}
.stApp p,.stApp label,.stApp span,.stApp li,.stApp h1,.stApp h2,.stApp h3{color:#eeeeff}
.block-container{max-width:1100px;padding-top:1.5rem}
.hero{background:linear-gradient(120deg,#6C63FF,#3EC6E0,#ff6ec4,#6C63FF);background-size:300% 300%;animation:g 8s ease infinite;
padding:2rem 1rem;border-radius:22px;text-align:center;margin-bottom:1rem;box-shadow:0 12px 40px rgba(108,99,255,.45)}
.hero h1{margin:0;font-size:2.8rem;font-weight:800;color:#fff!important}.hero p{margin:.4rem 0 0;color:#fff!important}
@keyframes g{0%{background-position:0% 50%}50%{background-position:100% 50%}100%{background-position:0% 50%}}
.stTextArea textarea,.stTextInput input{background:rgba(255,255,255,.08)!important;color:#fff!important;border-radius:14px!important}
.stButton>button,.stDownloadButton>button{background:linear-gradient(90deg,#6C63FF,#3EC6E0);color:#fff;border:0;border-radius:14px;font-weight:700}
.stButton>button:hover{transform:scale(1.03);box-shadow:0 0 22px rgba(108,99,255,.8);color:#fff}
.result{background:rgba(255,255,255,.08);border-left:6px solid #3EC6E0;border-radius:16px;padding:1rem 1.3rem;margin:.5rem 0}
.chip{display:inline-block;padding:.3rem .9rem;border-radius:99px;background:rgba(108,99,255,.35);margin:.2rem .3rem .2rem 0}
[data-testid="stMetric"]{background:rgba(255,255,255,.07);border-radius:16px;padding:.7rem 1rem}
</style>""", unsafe_allow_html=True)

with st.sidebar:
    st.header("📚 Study Buddy")
    st.slider("🎯 Daily goal (sessions)", 1, 10, 3, key="goal")
    ex = st.date_input("📆 Exam date", value=None)
    if ex: st.metric("Days to exam", max((ex - today()).days, 0))
    st.info("☁️ Cloud version · open-weights AI")
    st.warning("Notes, photos and voice are sent to Groq for processing. Use the offline version for private notes.")
    st.caption("Progress lives in this browser session. Use Export in the Progress tab to keep it.")
    st.caption("Team: Sanchita, Sachi, Sakshi, Sanjana · HackoberFest 2026")

st.markdown('<div class="hero"><h1>📚 Study Buddy</h1><p>Notes, photos or voice in. Summaries, quizzes, flashcards and revision plans out.</p></div>', unsafe_allow_html=True)

st.markdown("### 1️⃣ Add your material")
i1, i2, i3, i4 = st.tabs(["✍️ Paste", "📄 PDF / TXT", "📷 Photo", "🎤 Voice"])
SAMPLE = ("Extended Slicing: variable[start:end:step]. The step decides the increment between indexes. "
          "A negative step moves backwards, so variable[::-1] reverses a string. A step of 0 is not allowed.")
with i1:
    typed = st.text_area("Paste notes", height=170, key="typed", placeholder="Paste your class notes here...")
    st.button("✨ Try sample notes", on_click=lambda: S.__setitem__("typed", SAMPLE))
file_text = ""
with i2:
    up = st.file_uploader("Drop a PDF or TXT", type=["pdf", "txt"])
    if up:
        try:
            if up.name.lower().endswith(".pdf"):
                file_text, pg, stt_ = read_pdf(up)
                if stt_ == "locked": st.error("🔒 Password-protected PDF.")
                elif not file_text.strip(): st.warning("No text found (scanned PDF?). Use the 📷 Photo tab instead.")
                else: st.success(f"✅ {pg} pages loaded")
            else:
                file_text = up.read().decode("utf-8", errors="ignore"); st.success("✅ Text loaded")
        except Exception: st.error("Could not read this file.")
with i3:
    imgs = st.file_uploader("Photos of notes or textbook pages", type=["png", "jpg", "jpeg", "webp"], accept_multiple_files=True)
    if imgs and st.button("🔍 Read text from photos"):
        try:
            with st.spinner("Reading photos..."):
                S["extra"] += "\n" + ocr(imgs)
            st.success("✅ Added to your notes")
        except Exception as e: st.error(f"Could not read photos (keep each under 4 MB). {e}")
with i4:
    aud = st.audio_input("🎤 Tap to record, tap again to stop")
    if aud:
        sig = str(len(aud.getvalue()))
        if S["seen"] != sig:
            try:
                with st.spinner("Listening..."):
                    S["extra"] += "\n" + stt(aud)
                S["seen"] = sig; st.success("✅ Voice added to your notes")
            except Exception as e: st.error(f"Could not transcribe. {e}")

notes = ((file_text if file_text.strip() else typed) + "\n" + S["extra"]).strip()
if S["extra"].strip():
    with st.expander("📎 Added from photos / voice"):
        st.write(S["extra"])
        st.button("🗑️ Remove", on_click=lambda: S.__setitem__("extra", ""))
if notes: st.markdown(f'<span class="chip">📝 {len(notes.split())} words ready</span>', unsafe_allow_html=True)

st.markdown("### 2️⃣ Study")
t_tools, t_quiz, t_cards, t_chat, t_rev, t_prog, t_focus = st.tabs(
    ["🛠️ Tools", "📝 Quiz", "🃏 Flashcards", "💬 Chat", "📅 Revision", "🎯 Progress", "⏱️ Focus"])

MODES = {"📝 Summarize": "Summarize in 5 short bullet points, each on a new line starting with '- ':",
         "🧒 Explain like I'm 5": "Explain in very simple words:",
         "🔑 Key terms": "List the 8 most important key terms as '- **term**: one-line definition':",
         "📄 Cheat sheet": "Make a one-page exam cheat sheet with headings and short bullets:",
         "❓ Exam questions": "Write 8 likely exam questions (short and long) with brief model answers:"}

with t_tools:
    mode = st.radio("What do you want?", list(MODES), horizontal=True)
    if st.button("🚀 Generate", use_container_width=True):
        if not notes: st.warning("Add notes, a photo, a file or voice first.")
        else:
            try:
                pr = st.progress(0.0, text="Starting...")
                prep, note = prepare(notes, pr)
                with st.spinner("🤔 Thinking..."):
                    ans = ask(MODES[mode] + "\n\n" + prep).replace("•", "\n- ")
                S["answer"], S["amode"], S["anote"] = ans, mode, note
                S["history"].insert(0, {"time": datetime.now(IST).strftime("%d %b, %I:%M %p"), "mode": mode,
                                        "title": notes[:45].replace("\n", " "), "answer": ans})
                del S["history"][30:]; log(mode); st.toast("Saved to History 🎉")
            except Exception as e: st.error(f"Could not get a response. Wait a minute and retry. ({e})")
    if S.get("answer"):
        st.markdown(f"### ✅ {S['amode']}")
        if S.get("anote"): st.caption(S["anote"])
        st.markdown('<div class="result">', unsafe_allow_html=True); st.markdown(S["answer"]); st.markdown('</div>', unsafe_allow_html=True)
        speak(S["answer"])
        st.download_button("⬇️ Download", S["answer"], file_name="studybuddy_answer.txt")

with t_quiz:
    c1, c2, c3 = st.columns([3, 1, 1])
    topic = c1.text_input("Quiz topic (empty = use my notes)", key="qtopic", placeholder="e.g. Photosynthesis")
    n = c2.selectbox("Questions", [5, 10, 15]); lvl = c3.selectbox("Level", ["Easy", "Medium", "Hard"], index=1)
    if st.button("🎲 Generate quiz", use_container_width=True):
        if not topic.strip() and not notes: st.warning("Type a topic or add notes first.")
        else:
            src = f"the topic: {topic}" if topic.strip() else "these notes:\n" + notes[:8000]
            with st.spinner("Writing questions..."):
                qs = ask_json(f'Create {n} {lvl} multiple-choice questions on {src}\nReturn a JSON list; each item has "q", "options" (exactly 4 strings), "answer" (index 0-3) and "why" (one short line).')
            ok = isinstance(qs, list) and qs and all(isinstance(x, dict) and {"q", "options", "answer"} <= x.keys() and len(x["options"]) == 4 for x in qs)
            if ok: S["qid"] += 1; S["quiz"] = {"qs": qs, "res": None, "topic": topic or notes[:30]}
            else: st.error("Could not build the quiz. Please try again.")
    Q = S["quiz"]
    if Q:
        with st.form("quizform"):
            for i, q in enumerate(Q["qs"]):
                st.radio(f"{i + 1}. {q['q']}", q["options"], index=None, key=f"q{S['qid']}_{i}")
            sub = st.form_submit_button("✅ Submit answers")
        if sub:
            right = [S.get(f"q{S['qid']}_{i}") == q["options"][int(q["answer"])] for i, q in enumerate(Q["qs"])]
            Q["res"] = right
            S["scores"].append({"date": ds(today()), "pct": round(100 * sum(right) / len(right)), "topic": Q["topic"]}); log("📝 Quiz")
        if Q["res"]:
            st.success(f"🏆 Score: {sum(Q['res'])} / {len(Q['res'])}")
            for i, q in enumerate(Q["qs"]):
                st.markdown(f"{'✅' if Q['res'][i] else '❌'} **{q['q']}** → {q['options'][int(q['answer'])]}  \n_{q.get('why', '')}_")

with t_cards:
    if st.button("🃏 Make flashcards from topic or notes", use_container_width=True):
        src = f"the topic: {topic}" if topic.strip() else "these notes:\n" + notes[:8000]
        if not topic.strip() and not notes: st.warning("Add notes, or type a topic in the Quiz tab.")
        else:
            with st.spinner("Making cards..."):
                cs = ask_json(f'Create 10 flashcards on {src}\nReturn a JSON list of objects with keys "q" and "a".')
            if isinstance(cs, list) and cs and all(isinstance(c, dict) and "q" in c and "a" in c for c in cs):
                S["cards"], S["ci"], S["show"] = cs, 0, False; log("🃏 Cards")
            else: st.error("Could not make cards. Try again.")
    cs = S["cards"]
    if cs:
        i = S["ci"]
        if i >= len(cs): st.success("🎉 Deck complete!")
        else:
            st.progress(i / len(cs), text=f"Card {i + 1} of {len(cs)}")
            st.markdown(f'<div class="result"><h3>❓ {cs[i]["q"]}</h3></div>', unsafe_allow_html=True)
            if S["show"]: st.markdown(f'<div class="result"><b>💡 {cs[i]["a"]}</b></div>', unsafe_allow_html=True)
            a, b, c = st.columns(3)
            if a.button("👀 Show answer"): S["show"] = True; st.rerun()
            if b.button("✅ Got it"): S["ci"] += 1; S["show"] = False; st.rerun()
            if c.button("🔁 Again"): cs.append(cs[i]); S["ci"] += 1; S["show"] = False; st.rerun()

with t_chat:
    st.caption("Ask questions about your notes, like ChatGPT.")
    for m in S["chat"]:
        with st.chat_message(m["role"]): st.markdown(m["content"])
    q = st.chat_input("Ask about your notes...")
    if q:
        if not notes: st.warning("Add notes first.")
        else:
            S["chat"].append({"role": "user", "content": q})
            with st.chat_message("user"): st.markdown(q)
            with st.chat_message("assistant"):
                try:
                    sysm = "You are Study Buddy, a friendly tutor. Answer from the student's notes; if missing, say so, then explain briefly.\n\nNOTES:\n" + notes[:20000]
                    r = llm([{"role": "system", "content": sysm}] + S["chat"][-10:]) or "Please rephrase."
                except Exception: r = "Sorry, try again in a minute."
                st.markdown(r)
            S["chat"].append({"role": "assistant", "content": r}); log("💬 Chat")
    if S["chat"] and st.button("🧹 Clear chat"): S["chat"] = []; st.rerun()

with t_rev:
    st.caption("Spaced revision: each topic comes back after 1, 3, 7, 14 and 30 days.")
    c1, c2 = st.columns([4, 1])
    nt = c1.text_input("Topic to revise", key="newtopic", placeholder="e.g. Extended Slicing")
    if c2.button("➕ Add") and nt.strip():
        S["rev"].append({"topic": nt.strip(), "step": 0, "next": ds(today() + timedelta(days=STEPS[0]))}); st.rerun()
    if notes and st.button("➕ Add my current notes as a topic"):
        S["rev"].append({"topic": notes[:40].replace("\n", " "), "step": 0, "next": ds(today() + timedelta(days=STEPS[0]))}); st.rerun()
    due = [(k, r) for k, r in enumerate(S["rev"]) if r["next"] <= ds(today())]
    st.markdown(f"**📌 Due today: {len(due)}**")
    for k, r in due:
        a, b = st.columns([5, 1])
        a.markdown(f"📖 **{r['topic']}** (round {r['step'] + 1} of {len(STEPS)})")
        if b.button("✅ Done", key=f"rv{k}"):
            r["step"] += 1; log("📅 Revised")
            if r["step"] >= len(STEPS): S["rev"].pop(k)
            else: r["next"] = ds(today() + timedelta(days=STEPS[r["step"]]))
            st.rerun()
    up_ = [r for r in S["rev"] if r["next"] > ds(today())]
    if up_: st.dataframe(pd.DataFrame(up_)[["topic", "next"]].rename(columns={"topic": "Topic", "next": "Next revision"}), use_container_width=True)
    if not S["rev"]: st.info("No topics yet. Add one above.")

with t_prog:
    L, goal = S["log"], S.get("goal", 3)
    tc = sum(1 for e in L if e["date"] == ds(today())); sk = streak()
    m = st.columns(4)
    m[0].metric("Today", f"{tc} / {goal}"); m[1].metric("🔥 Streak", f"{sk} day(s)"); m[2].metric("Sessions", len(L))
    m[3].metric("Quiz average", f"{round(sum(x['pct'] for x in S['scores']) / len(S['scores']))}%" if S["scores"] else "-")
    st.progress(min(tc / goal, 1.0), text=f"Daily goal: {tc} of {goal}")
    if tc >= goal: st.success("🎉 Daily goal reached!")
    days = [today() - timedelta(days=i) for i in range(6, -1, -1)]
    st.bar_chart(pd.DataFrame({"Sessions": [sum(1 for e in L if e["date"] == ds(d)) for d in days]}, index=[d.strftime("%m-%d") for d in days]))
    bd = [b for ok, b in [(len(L) >= 1, "🥉 First step"), (len(L) >= 10, "🥈 10 sessions"), (len(L) >= 30, "🥇 30 sessions"),
                          (sk >= 3, "🔥 3-day streak"), (sk >= 7, "🏆 7-day streak"),
                          (any(x["pct"] == 100 for x in S["scores"]), "💯 Perfect quiz")] if ok]
    st.markdown("".join(f'<span class="chip">{b}</span>' for b in bd) or "Study once to earn your first badge.", unsafe_allow_html=True)
    st.divider()
    with st.expander("🕘 History"):
        for h in S["history"][:15]:
            st.markdown(f"**{h['mode']}** · {h['title']} · _{h['time']}_"); st.markdown(h["answer"]); st.markdown("---")
    st.download_button("💾 Export progress", json.dumps({k: S[k] for k in ["history", "log", "rev", "scores"]}, indent=2), file_name="studybuddy_progress.json")
    imp = st.file_uploader("Import saved progress (.json)", type="json", key="imp")
    if imp and S.get("imp_sig") != f"{imp.name}{imp.size}":
        try:
            d = json.loads(imp.read().decode("utf-8"))
            for k in ["history", "log", "rev", "scores"]:
                if isinstance(d.get(k), list): S[k] = d[k]
            S["imp_sig"] = f"{imp.name}{imp.size}"; st.rerun()
        except Exception: st.error("Could not read that file.")

with t_focus:
    st.caption("Pomodoro: 25 minutes of focus, then a 5-minute break.")
    components.html('''<div style="font-family:sans-serif;text-align:center;color:#fff"><h1 id="t" style="font-size:64px;margin:8px">25:00</h1>
<div id="m">Ready</div><br><button onclick="go(1500,'Focus time')">▶ Focus 25</button> <button onclick="go(300,'Break time')">☕ Break 5</button>
<button onclick="clearInterval(iv);document.getElementById('t').textContent='25:00'">⟲ Reset</button></div>
<style>button{background:linear-gradient(90deg,#6C63FF,#3EC6E0);color:#fff;border:0;border-radius:10px;padding:10px 16px;font-weight:700;cursor:pointer}</style>
<script>let iv;function go(s,l){clearInterval(iv);document.getElementById('m').textContent=l;iv=setInterval(()=>{s--;
document.getElementById('t').textContent=String(Math.floor(s/60)).padStart(2,'0')+':'+String(s%60).padStart(2,'0');
if(s<=0){clearInterval(iv);alert('Time is up!')}},1000)}</script>''', height=250)
