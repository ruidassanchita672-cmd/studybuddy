# Study Buddy 📚

An offline AI study assistant. Paste your notes or upload a PDF to get summaries, quizzes, and simple explanations.

## Features
- Summarize notes in 5 bullet points
- Generate quiz questions with answers
- Explain notes in simple words
- PDF upload support
- Runs 100% locally: no internet needed, no data leaves your laptop, no API costs

## Tech Stack
- Python
- Streamlit (web interface)
- Ollama + Llama 3.2 3B (open-weights AI model)
- pypdf (PDF reading)

## How to Run
1. Install [Ollama](https://ollama.com) and Python
2. Download the model: `ollama pull llama3.2:3b`
3. Install libraries: `pip install -r requirements.txt`
4. Start the app: `python -m streamlit run app.py`

## Team
Sanchita Sachi Sakshi Sanjana