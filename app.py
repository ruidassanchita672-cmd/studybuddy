import json
import random
import re
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="StudyBuddy", page_icon="📚", layout="wide")

DATA_DIR = Path("user_data")
DATA_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------- question bank
# (question, [options], index_of_correct_option)
BANK = {
    "Python": [
        ("What does range(2, 6) produce?", ["2,3,4,5", "2,3,4,5,6", "3,4,5,6", "2,4,6"], 0),
        ("Which keyword exits a loop immediately?", ["continue", "pass", "break", "exit"], 2),
        ("What is len([1, 2, 3])?", ["2", "3", "4", "Error"], 1),
        ("Which of these is immutable?", ["list", "dict", "set", "tuple"], 3),
        ("What does // do?", ["Float division", "Floor division", "Modulus", "Power"], 1),
        ("Which block runs when a loop ends without break?", ["finally", "else", "except", "pass"], 1),
    ],
    "Science": [
        ("Powerhouse of the cell?", ["Nucleus", "Ribosome", "Mitochondria", "Golgi body"], 2),
        ("Chemical symbol for sodium?", ["S", "So", "Na", "N"], 2),
        ("Gas absorbed by plants for photosynthesis?", ["Oxygen", "Carbon dioxide", "Nitrogen", "Hydrogen"], 1),
        ("SI unit of force?", ["Joule", "Watt", "Newton", "Pascal"], 2),
        ("Approximate speed of light?", ["3x10^8 m/s", "3x10^6 m/s", "3x10^5 m/s", "3x10^10 m/s"], 0),
        ("pH of a neutral solution?", ["0", "7", "14", "1"], 1),
    ],
    "Maths": [
        ("What is 12 x 12?", ["124", "144", "148", "132"], 1),
        ("Square root of 169?", ["12", "13", "14", "15"], 1),
        ("Sum of angles in a triangle?", ["90", "180", "270", "360"], 1),
        ("What is 15% of 200?", ["20", "25", "30", "35"], 2),
        ("Derivative of x^2?", ["x", "2x", "x^2", "2"], 1),
        ("Approximate value of pi?", ["3.14", "2.71", "1.61", "3.41"], 0),
    ],
    "Computer Basics": [
        ("CPU stands for?", ["Central Processing Unit", "Computer Personal Unit", "Central Program Utility", "Core Processing Unit"], 0),
        ("Binary of decimal 5?", ["100", "101", "110", "111"], 1),
        ("Which of these is a database?", ["MySQL", "Linux", "Chrome", "Python"], 0),
        ("HTTP stands for?", ["HyperText Transfer Protocol", "High Text Transfer Program", "Hyper Tool Transfer Protocol", "HyperText Test Protocol"], 0),
        ("Which data structure is LIFO?", ["Queue", "Stack", "Array", "Tree"], 1),
        ("How many bits in a byte?", ["4", "8", "16", "32"], 1),
    ],
}
ALL_Q = [(t, *q) for t, qs in BANK.items() for q in qs]  # (topic, q, opts, ans)

TIPS = [
    "Study in short bursts: 25 minutes focus, 5 minutes break.",
    "Testing yourself beats re-reading. Use the quiz and flashcards.",
    "Sleep helps memory. Do not skip it before exams.",
    "Explain a topic out loud as if teaching a friend.",
    "Start with the hardest subject while your energy is high.",
]

# ---------------------------------------------------------------- storage
def clean(name):
    return re.sub(r"[^a-z0-9_]", "", name.lower().strip().replace(" ", "_"))[:30]


def default_data():
    return {"streak": 0, "last_quiz": None, "xp": 0, "history": [],
            "cards": [], "notes": [], "tasks": [], "focus": []}


def load(user):
    f = DATA_DIR / f"{user}.json"
    if f.exists():
        try:
            return {**default_data(), **json.loads(f.read_text())}
        except Exception:
            pass
    return default_data()


def save():
    f = DATA_DIR / f"{st.session_state.user}.json"
    f.write_text(json.dumps(st.session_state.data))


# ---------------------------------------------------------------- login
st.sidebar.title("📚 StudyBuddy")
name = st.sidebar.text_input("Your username", placeholder="e.g. riya_21")
user = clean(name)
if not user:
    st.title("📚 Welcome to StudyBuddy")
    st.write("Your daily study companion: **daily quiz, flashcards, notes, tasks, focus timer and progress tracking.**")
    st.info("Enter a username in the sidebar to start. Your data is saved under that name.")
    st.stop()

if st.session_state.get("user") != user:
    st.session_state.user = user
    st.session_state.data = load(user)
d = st.session_state.data
today = date.today().isoformat()

page = st.sidebar.radio("Go to", ["🏠 Dashboard", "🎯 Daily Quiz", "📝 Practice Quiz",
                                  "🃏 Flashcards", "🗒️ Notes", "✅ Tasks",
                                  "⏱️ Focus Timer", "📈 Progress"])
st.sidebar.caption(f"🔥 Streak: {d['streak']} days  |  ⭐ XP: {d['xp']}")


# ---------------------------------------------------------------- quiz helper
def quiz_form(key, qs):
    """Render a quiz. Returns (score, answers) on submit, else None."""
    with st.form(key):
        answers = [st.radio(f"{i + 1}. {q[0]}", q[1], index=None, key=f"{key}_{i}")
                   for i, q in enumerate(qs)]
        if st.form_submit_button("Submit answers"):
            score = sum(a == q[1][q[2]] for a, q in zip(answers, qs))
            return score, answers
    return None


def review(qs, answers):
    for i, (q, a) in enumerate(zip(qs, answers)):
        right = q[1][q[2]]
        if a == right:
            st.success(f"{i + 1}. {q[0]}  ✅ {right}")
        else:
            st.error(f"{i + 1}. {q[0]}  ❌ You: {a or 'no answer'} | Correct: {right}")


def record(kind, topic, score, total):
    d["history"].append({"date": today, "type": kind, "topic": topic, "score": score, "total": total})
    d["xp"] += score * 10
    save()


# ---------------------------------------------------------------- pages
if page == "🏠 Dashboard":
    st.title(f"Hi {name.strip().title()} 👋")
    done = any(h["date"] == today and h["type"] == "daily" for h in d["history"])
    pending = sum(not t["done"] for t in d["tasks"])
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🔥 Streak", f"{d['streak']} days")
    c2.metric("⭐ XP", d["xp"])
    c3.metric("Pending tasks", pending)
    c4.metric("Flashcards to learn", sum(not c["known"] for c in d["cards"]))
    st.divider()
    if done:
        st.success("Daily quiz completed today. Come back tomorrow to keep your streak!")
    else:
        st.warning("Your daily quiz is waiting. Open **🎯 Daily Quiz** to keep your streak alive.")
    st.info("💡 " + random.Random(today).choice(TIPS))

elif page == "🎯 Daily Quiz":
    st.title("🎯 Daily Quiz")
    st.caption("5 new questions every day. Finish it daily to build a streak.")
    qs = random.Random(today + user).sample(ALL_Q, 5)
    qs = [(q[1], q[2], q[3]) for q in qs]
    todays = [h for h in d["history"] if h["date"] == today and h["type"] == "daily"]
    if todays:
        st.success(f"Done for today! You scored {todays[-1]['score']}/{todays[-1]['total']}.")
        st.write("Come back tomorrow for new questions. Try **Practice Quiz** for more.")
    else:
        res = quiz_form("daily", qs)
        if res:
            score, answers = res
            last = d["last_quiz"]
            if last == (date.today() - timedelta(days=1)).isoformat():
                d["streak"] += 1
            else:
                d["streak"] = 1
            d["last_quiz"] = today
            record("daily", "Mixed", score, 5)
            st.balloons() if score >= 4 else None
            st.subheader(f"Score: {score}/5  (+{score * 10} XP, streak {d['streak']} 🔥)")
            review(qs, answers)

elif page == "📝 Practice Quiz":
    st.title("📝 Practice Quiz")
    topic = st.selectbox("Topic", list(BANK))
    n = st.slider("Questions", 3, len(BANK[topic]), 5)
    if st.button("Start new quiz"):
        st.session_state.pq = random.sample(BANK[topic], n)
        st.session_state.pq_topic = topic
        st.session_state.pq_id = st.session_state.get("pq_id", 0) + 1
    if "pq" in st.session_state:
        qs = st.session_state.pq
        res = quiz_form(f"practice{st.session_state.pq_id}", qs)
        if res:
            score, answers = res
            record("practice", st.session_state.pq_topic, score, len(qs))
            st.subheader(f"Score: {score}/{len(qs)}")
            review(qs, answers)

elif page == "🃏 Flashcards":
    st.title("🃏 Flashcards")
    tab1, tab2, tab3 = st.tabs(["Review", "Add", "Manage"])
    with tab2:
        with st.form("addcard", clear_on_submit=True):
            q = st.text_input("Question / term")
            a = st.text_area("Answer / definition")
            if st.form_submit_button("Add card") and q and a:
                d["cards"].append({"q": q, "a": a, "known": False})
                save()
                st.success("Card added!")
    with tab1:
        todo = [c for c in d["cards"] if not c["known"]]
        if not d["cards"]:
            st.info("No cards yet. Add some in the Add tab.")
        elif not todo:
            st.success("You know all your cards! 🎉")
        else:
            i = st.session_state.get("fc_i", 0) % len(todo)
            card = todo[i]
            st.markdown(f"### {card['q']}")
            if st.session_state.get("fc_show"):
                st.info(card["a"])
            b1, b2, b3 = st.columns(3)
            if b1.button("Show / hide answer"):
                st.session_state.fc_show = not st.session_state.get("fc_show", False)
                st.rerun()
            if b2.button("✅ I know this"):
                card["known"] = True
                d["xp"] += 5
                save()
                st.session_state.fc_show = False
                st.rerun()
            if b3.button("➡️ Next"):
                st.session_state.fc_i = i + 1
                st.session_state.fc_show = False
                st.rerun()
            st.caption(f"{len(todo)} card(s) left to learn")
    with tab3:
        for idx, c in enumerate(d["cards"]):
            col1, col2, col3 = st.columns([6, 2, 1])
            col1.write(f"**{c['q']}**  \n{c['a']}")
            col2.write("✅ Known" if c["known"] else "📖 Learning")
            if col3.button("🗑️", key=f"delc{idx}"):
                d["cards"].pop(idx)
                save()
                st.rerun()
        if d["cards"] and st.button("Reset all to 'learning'"):
            for c in d["cards"]:
                c["known"] = False
            save()
            st.rerun()

elif page == "🗒️ Notes":
    st.title("🗒️ Notes")
    with st.form("addnote", clear_on_submit=True):
        title = st.text_input("Title")
        body = st.text_area("Note", height=150)
        if st.form_submit_button("Save note") and title:
            d["notes"].append({"title": title, "body": body, "created": today})
            save()
            st.success("Saved!")
    search = st.text_input("🔍 Search notes").lower()
    for idx, n in enumerate(d["notes"]):
        if search in (n["title"] + n["body"]).lower():
            with st.expander(f"{n['title']}  ({n['created']})"):
                st.write(n["body"])
                if st.button("Delete", key=f"deln{idx}"):
                    d["notes"].pop(idx)
                    save()
                    st.rerun()
    if d["notes"]:
        export = "\n\n".join(f"# {n['title']} ({n['created']})\n{n['body']}" for n in d["notes"])
        st.download_button("⬇️ Download all notes", export, "my_notes.txt")

elif page == "✅ Tasks":
    st.title("✅ Study Tasks")
    with st.form("addtask", clear_on_submit=True):
        t = st.text_input("New task")
        if st.form_submit_button("Add") and t:
            d["tasks"].append({"text": t, "done": False})
            save()
            st.rerun()
    for idx, t in enumerate(d["tasks"]):
        new = st.checkbox(t["text"], value=t["done"], key=f"task{idx}")
        if new != t["done"]:
            t["done"] = new
            if new:
                d["xp"] += 5
            save()
            st.rerun()
    if any(t["done"] for t in d["tasks"]) and st.button("Clear completed"):
        d["tasks"] = [t for t in d["tasks"] if not t["done"]]
        save()
        st.rerun()

elif page == "⏱️ Focus Timer":
    st.title("⏱️ Focus Timer (Pomodoro)")
    mins = st.number_input("Minutes", 1, 120, 25)
    components.html(f"""
    <div style="text-align:center;font-family:sans-serif">
      <h1 id="t" style="font-size:64px;margin:10px">{mins:02d}:00</h1>
      <button onclick="start()" style="font-size:18px;padding:8px 20px">Start</button>
      <button onclick="stop()" style="font-size:18px;padding:8px 20px">Reset</button>
    </div>
    <script>
      let total={mins}*60, left=total, id=null;
      const el=document.getElementById('t');
      function show(){{el.textContent=String(Math.floor(left/60)).padStart(2,'0')+':'+String(left%60).padStart(2,'0');}}
      function start(){{ if(id) return; id=setInterval(()=>{{left--;show();
        if(left<=0){{clearInterval(id);id=null;el.textContent='Done! 🎉';}}}},1000);}}
      function stop(){{clearInterval(id);id=null;left=total;show();}}
    </script>""", height=200)
    st.caption("When the timer finishes, log your session to earn XP.")
    if st.button("✅ Log completed session"):
        d["focus"].append({"date": today, "minutes": int(mins)})
        d["xp"] += 20
        save()
        st.success("Session logged! +20 XP")

elif page == "📈 Progress":
    st.title("📈 Progress")
    h = pd.DataFrame(d["history"])
    if h.empty:
        st.info("Take a quiz to see your progress here.")
    else:
        h["percent"] = h["score"] / h["total"] * 100
        c1, c2, c3 = st.columns(3)
        c1.metric("Quizzes taken", len(h))
        c2.metric("Average score", f"{h['percent'].mean():.0f}%")
        c3.metric("Best streak so far", f"{d['streak']} days")
        st.subheader("Score over time")
        st.line_chart(h.groupby("date")["percent"].mean())
        st.subheader("Average by topic")
        st.bar_chart(h.groupby("topic")["percent"].mean())
        st.subheader("History")
        st.dataframe(h[["date", "type", "topic", "score", "total"]].iloc[::-1], use_container_width=True)
    f = pd.DataFrame(d["focus"])
    if not f.empty:
        st.subheader("Focus minutes per day")
        st.bar_chart(f.groupby("date")["minutes"].sum())
    st.divider()
    if st.button("⚠️ Reset all my data"):
        st.session_state.data = default_data()
        save()
        st.rerun()
