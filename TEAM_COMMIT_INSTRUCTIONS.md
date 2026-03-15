# Team Commit Instructions — Module M45

> **Branch:** `module/M45-reference-range`  
> **Repo:** `https://github.com/DINESHYDK/medical-copilot-frontend.git`

---

## Step 1: Setup

1. Accept the GitHub collaboration invite from your email.
2. Clone and switch to the branch:
   ```bash
   git clone https://github.com/DINESHYDK/medical-copilot-frontend.git
   cd medical-copilot-frontend
   git checkout module/M45-reference-range
   ```

## Step 2: Make a Safe Edit (pick ONE)

**Option A — Backend Docstrings:**  
Open `backend/main.py`, find an endpoint function, and add a docstring:
```python
"""Fetches all patient records from the database for the UI dropdown."""
```

**Option B — Database Comment:**  
Open `database/procedures.sql` and add at the top:
```sql
-- Note: This procedure was optimized for Neon PostgreSQL
```

**Option C — Documentation:**  
Open `Progress.md` and add your Name + GitHub ID under "Team Members".

## Step 3: Commit & Push

```bash
git add .
git commit -m "docs: add function docstrings to FastAPI endpoints"
git push origin module/M45-reference-range
```

> **Important:** Only edit docs/comments. Do NOT modify any logic or imports!

Let Dinesh know once your commit appears on GitHub.
