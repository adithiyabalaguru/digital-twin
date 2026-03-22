# Adithiya's Digital Twin (Simple Version)

A digital twin MVP built for the Viven AI take-home assessment.
**Phase 2 deep-dive: Twin Sharing.**

Two files. No build step. Easy to run.

---

## How to run

### 1. Install dependencies

```bash
pip install flask flask-cors openai
```

### 2. Set your OpenAI API key

```bash
export OPENAI_API_KEY=your-key-here
```

### 3. Start the server

```bash
python server.py
```

### 4. Open in browser

Go to **http://localhost:5000**

---

## How it works

### server.py (~130 lines)
- **Flask** handles HTTP requests
- **KNOWLEDGE dict** holds resume data split into 5 scopes: education, experience, projects, skills, interests
- **get_relevant_chunks()** scores each scope by keyword overlap with the question, returns the top 3
- Those chunks get injected into the OpenAI system prompt so the model answers as Adithiya
- **Share tokens** are stored in a Python dict in memory

### index.html (one file)
- Checks the URL: `/shared/<tokenId>` → guest view, anything else → owner view
- Owner can chat (full access), create share tokens, copy links, revoke tokens
- Guests see a limited twin that only answers within the allowed scopes

---

## Twin Sharing design

The owner creates a **share token** with:
- A label (e.g. "Recruiters")
- A subset of scopes (e.g. education + experience only)

This generates a URL like `http://localhost:5000/shared/<token-id>`.

When a guest visits that URL and asks a question, the server only retrieves chunks from the **allowed scopes** and passes those to OpenAI. The LLM has no information outside those scopes — so scope enforcement is at the data level, not just the prompt level.

---

## Tradeoffs & next steps

| Decision | Reason |
|----------|--------|
| In-memory token storage | Simple for MVP; tokens reset on restart. Would use a database in production. |
| Keyword overlap scoring | Fast, zero cost, sufficient for ~10 resume chunks. Would use vector embeddings for larger corpora. |
| Single HTML file | No build step, easy to understand and modify. Would split into components for a larger app. |
| No auth on owner routes | Fine for local MVP. Would add login/JWT for production. |
