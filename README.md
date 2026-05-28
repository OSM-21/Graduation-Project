# 🎓 Jazan University Smart Chatbot
### AI-Powered Academic Assistant for Arabic-Speaking Students

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square&logo=python)
![Flask](https://img.shields.io/badge/Flask-2.x-black?style=flat-square&logo=flask)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)
![Arabic NLP](https://img.shields.io/badge/Arabic-NLP-orange?style=flat-square)
![RAG](https://img.shields.io/badge/Architecture-RAG-purple?style=flat-square)

**An intelligent Arabic-first chatbot that helps university students get instant answers about academic schedules, regulations, and administrative procedures.**

</div>

---

## 🌟 The Problem

Students at Jazan University's CS department constantly face the same challenge — finding accurate information about courses, registration deadlines, exam schedules, and administrative procedures requires navigating multiple offices and websites. **We built the solution.**

---

## 🧠 What It Does

| Feature | Description |
|---|---|
| 🗣️ **Arabic-First NLP** | Understands colloquial and formal Arabic queries |
| 🎯 **Intent Classification** | Identifies what the student is asking with ~90% accuracy |
| 🔍 **Semantic Search** | Finds the most relevant answer even with imperfect phrasing |
| 🤖 **LLM Response Formatting** | Generates clean, professional responses via Groq API |
| 📊 **Admin Dashboard** | Tracks usage patterns and unknown queries for continuous improvement |
| 🔐 **User Authentication** | Secure login with conversation history |

---

## ⚙️ System Architecture

```
User Query (Arabic/English)
        │
        ▼
┌─────────────────────┐
│  Intent Classifier  │  ← Sentence-Transformers
│  (What does user    │    trained on 302 hand-crafted
│   want to know?)    │    university-specific samples
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Semantic Search    │  ← FAISS Vector Store
│  (Find the best     │    dense retrieval over
│   matching answer)  │    internal knowledge base
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Response Generator │  ← Groq API (LLM)
│  (Format a clean,   │    grounded strictly in
│   helpful reply)    │    verified university data
└────────┬────────────┘
         │
         ▼
    Final Answer
```

---

## 🛠️ Tech Stack

**AI / NLP**
- `sentence-transformers` — multilingual embeddings for semantic understanding
- `FAISS` — fast similarity search over the knowledge base
- `Groq API` — LLM for response generation and formatting
- `SQLAlchemy` — ORM for structured data management

**Backend**
- `Flask` — lightweight Python web framework
- `SQLite` — embedded database for users and conversation history

**Key Design Decision: RAG Architecture**
> Instead of a generic chatbot that can hallucinate, we built a **Retrieval-Augmented Generation** system — every answer is grounded in verified university data. The LLM formats the response; it never invents facts.

---

## 📁 Project Structure

```
Graduation-Project/
│
├── app.py                  # Main Flask application
├── chatbot/
│   ├── intent_classifier.py    # Sentence-Transformers intent model
│   ├── semantic_search.py      # FAISS retrieval engine
│   └── response_generator.py   # Groq API integration
│
├── data/
│   ├── training_data.json      # 302 hand-crafted Q&A samples
│   └── knowledge_base/         # Verified university information
│
├── models/
│   └── intent_model/           # Saved Sentence-Transformers model
│
├── templates/              # Flask HTML templates
│   ├── chat.html
│   ├── login.html
│   └── admin_dashboard.html
│
├── static/                 # CSS, JS assets
├── requirements.txt
└── README.md
```

---

## 🚀 Getting Started

### Prerequisites
```bash
Python 3.10+
pip
```

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/OSM-21/Graduation-Project.git
cd Graduation-Project

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up environment variables
cp .env.example .env
# Add your GROQ_API_KEY to .env

# 4. Initialize the database
python init_db.py

# 5. Run the application
python app.py
```

The app will be available at `http://localhost:5000`

---

## 📊 Performance

| Metric | Result |
|---|---|
| Intent Classification Accuracy | ~90% |
| Training Samples | 302 hand-crafted examples |
| Supported Languages | Arabic 🇸🇦 + English 🇬🇧 |
| Response Time | < 3 seconds |
| Knowledge Base Coverage | CS Department — Jazan University |

---

## 💡 Key Challenges & Solutions

**Challenge 1: Arabic Language Processing**
> Arabic has complex morphology, dialects, and script variations. We used `sentence-transformers` with multilingual models that handle Arabic natively, combined with text normalization (hamza unification, diacritic removal).

**Challenge 2: Zero Real-World Data**
> No existing dataset matched our specific domain. Solution: we manually crafted 302 training samples by thinking like actual students — real questions, real scenarios, real phrasing.

**Challenge 3: Preventing Hallucination**
> LLMs can generate confident but wrong answers. Solution: RAG architecture ensures the LLM only formats and presents information retrieved from our verified knowledge base — never invents.

---

## 🔮 Future Improvements

- [ ] Voice input support (Speech-to-Text in Arabic)
- [ ] Expand knowledge base to all university departments
- [ ] Mobile application (React Native)
- [ ] Active learning — use unknown queries to improve the model automatically
- [ ] Multi-turn conversation memory

---

## 👨‍💻 Author

**Osama Ali Mahnashi**
AI Engineer | NLP & Large Language Models

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-blue?style=flat-square&logo=linkedin)](https://linkedin.com/in/osama-ali-mahnashi-647b5b2a2)
[![GitHub](https://img.shields.io/badge/GitHub-Follow-black?style=flat-square&logo=github)](https://github.com/OSM-21)

---

## 📄 License

This project is licensed under the MIT License — feel free to use it as inspiration for your own university chatbot!

---

<div align="center">
Built with ❤️ for Arabic-speaking students at Jazan University
</div>
