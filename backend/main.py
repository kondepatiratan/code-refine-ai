from fastapi import FastAPI, Header, Depends, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import sqlite3, json, time, os, jwt, bcrypt
from dotenv import load_dotenv
from pathlib import Path
from typing import Optional

load_dotenv()

import google.genai as genai
from mistralai.client import Mistral

GEMINI_API_KEY  = os.getenv("GEMINI_API_KEY", "")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
JWT_SECRET      = os.getenv("JWT_SECRET", "secret123")
DATABASE_PATH   = os.getenv("DATABASE_PATH", "db.sqlite")

# Initialise AI clients (guard against empty keys)
gemini_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
mistral_client = Mistral(api_key=MISTRAL_API_KEY) if MISTRAL_API_KEY else None

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ---- DB ----
conn   = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
cursor = conn.cursor()
conn.execute("PRAGMA foreign_keys = ON")

cursor.executescript("""
CREATE TABLE IF NOT EXISTS users(
  id INTEGER PRIMARY KEY, email TEXT UNIQUE, password TEXT);
CREATE TABLE IF NOT EXISTS sessions(
  id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, title TEXT, language TEXT,
  updatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS refinements(
  id INTEGER PRIMARY KEY, session_id INTEGER,
  original_code TEXT, refined_code TEXT,
  explanation TEXT, language TEXT, score INTEGER,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE);
""")
conn.commit()

# ---- Models ----
class AuthBody(BaseModel):
    email: str
    password: str

class SessionBody(BaseModel):
    title: str
    language: str

class RefineBody(BaseModel):
    code: str
    language: str

# ---- Auth ----
def verify_token(authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(401, "Missing authorization header")
    parts = authorization.split()
    if len(parts) != 2 or parts[0] != "Bearer":
        raise HTTPException(401, "Invalid authorization format")
    try:
        payload = jwt.decode(parts[1], JWT_SECRET, algorithms=["HS256"])
        return payload["userId"]
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")

@app.post("/api/auth/register")
def register(data: AuthBody):
    try:
        hashed = bcrypt.hashpw(data.password.encode(), bcrypt.gensalt())
        cursor.execute("INSERT INTO users(email,password) VALUES (?,?)", (data.email, hashed))
        conn.commit()
        return {"msg": "registered", "email": data.email}
    except sqlite3.IntegrityError:
        raise HTTPException(400, "Email already exists")

@app.post("/api/auth/login")
def login(data: AuthBody):
    cursor.execute("SELECT id, password FROM users WHERE email=?", (data.email,))
    user = cursor.fetchone()
    if not user or not bcrypt.checkpw(data.password.encode(), user[1]):
        raise HTTPException(401, "Invalid credentials")
    token = jwt.encode({"userId": user[0]}, JWT_SECRET, algorithm="HS256")
    return {"token": token, "userId": user[0]}

# ---- Scoring ----
def calc_score(code: str) -> int:
    score = 100
    if "any" in code: score -= 10
    if len(code) < 20: score -= 20
    return max(score, 0)

# ---- Common error detection (multi-language) ----
def detect_common_errors(code: str, language: str):
    errors = []
    lang = language.lower()

    if lang == "python":
        if "/ 0" in code or "/0" in code:
            fixed = code.replace("/0", "/ 1").replace("/ 0", "/ 1")
            errors.append({"error": "Division by Zero", "before": "/0", "after": "/ 1",
                           "reason": "Division by zero raises ZeroDivisionError at runtime."})
        if "except:" in code:
            errors.append({"error": "Bare except clause", "before": "except:", "after": "except Exception as e:",
                           "reason": "Bare except catches SystemExit and KeyboardInterrupt. Use specific exceptions."})
        if "print " in code and "print(" not in code:
            errors.append({"error": "Python 2 print statement", "before": "print ...", "after": "print(...)",
                           "reason": "Python 3 requires print as a function call."})

    elif lang in ("javascript", "typescript"):
        if "==" in code and "===" not in code:
            errors.append({"error": "Loose equality (==)", "before": "==", "after": "===",
                           "reason": "Use strict equality (===) to avoid unexpected type coercion."})
        if "var " in code:
            errors.append({"error": "Use of var", "before": "var", "after": "const / let",
                           "reason": "var has function scope and hoisting issues; prefer const or let."})

    elif lang == "java":
        if "== null" in code or "null ==" in code:
            errors.append({"error": "Null comparison with ==", "before": "obj == null", "after": "Objects.isNull(obj)",
                           "reason": "Use Objects.isNull() or Optional for safer null checks."})
        if "catch (Exception e) {}" in code or "catch(Exception e){}" in code:
            errors.append({"error": "Empty catch block", "before": "catch (Exception e) {}",
                           "after": "catch (Exception e) { e.printStackTrace(); }",
                           "reason": "Empty catch blocks silently swallow exceptions."})

    elif lang in ("c++", "c#"):
        if "using namespace std;" in code:
            errors.append({"error": "Using namespace std", "before": "using namespace std;",
                           "after": "std::cout / std::string (explicit)",
                           "reason": "Pollutes the global namespace and can cause name conflicts."})

    elif lang == "sql":
        if "SELECT *" in code.upper():
            errors.append({"error": "SELECT *", "before": "SELECT *", "after": "SELECT col1, col2, ...",
                           "reason": "SELECT * fetches unnecessary columns, hurting performance."})

    return errors

# ---- JSON extraction helper (handles markdown code fences) ----
def extract_json(text: str) -> dict:
    # Strip markdown fences like ```json ... ```
    t = text.strip()
    if "```" in t:
        start = t.find("```")
        t = t[start:]
        t = t[t.find("\n")+1:]          # skip the ``` line
        end = t.rfind("```")
        if end != -1:
            t = t[:end]
    # Find outermost JSON object
    start = t.find("{")
    end   = t.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError("No JSON object found")
    return json.loads(t[start:end])

# ---- AI refine ----
def ai_refine(code: str, language: str):
    # Quick local check first
    common_errors = detect_common_errors(code, language)
    if common_errors:
        return {
            "refinedCode": code,
            "explanation": f"Found {len(common_errors)} common issue(s) in your {language} code.",
            "errorChanges": common_errors
        }, "detector"

    prompt = f"""You are an expert {language} code reviewer.
Return ONLY valid JSON — no markdown, no text outside the JSON.
Use this exact structure:
{{
  "refinedCode": "full corrected code here",
  "explanation": "brief summary of what was fixed",
  "errorChanges": [
    {{"error": "error name", "before": "bad snippet", "after": "fixed snippet", "reason": "why"}}
  ]
}}

Language: {language}
Code:
{code}"""

    # ---- Gemini ----
    if gemini_client:
        try:
            response = gemini_client.models.generate_content(
                model="gemini-2.5-flash", contents=prompt)
            result = extract_json(response.text)
            result.setdefault("errorChanges", [])
            return result, "gemini"
        except json.JSONDecodeError as e:
            print(f"Gemini JSON parse failed: {e}")
        except Exception as e:
            print(f"Gemini failed: {type(e).__name__}: {str(e)[:200]}")
    else:
        print("Gemini skipped: no API key")

    # ---- Mistral fallback ----
    if mistral_client:
        try:
            res  = mistral_client.chat.complete(
                model="mistral-large-latest",
                messages=[{"role": "user", "content": prompt}])
            result = extract_json(res.choices[0].message.content)
            result.setdefault("errorChanges", [])
            return result, "mistral"
        except json.JSONDecodeError as e:
            print(f"Mistral JSON parse failed: {e}")
        except Exception as e:
            print(f"Mistral failed: {type(e).__name__}: {str(e)[:200]}")
    else:
        print("Mistral skipped: no API key")

    # ---- Hard fallback: return original code with clear message ----
    return {
        "refinedCode": code,
        "explanation": "AI service is temporarily unavailable. Your original code is shown unchanged. Please check your API keys or try again later.",
        "errorChanges": []
    }, "fallback"

# ---- Session APIs ----
@app.get("/api/refine/sessions")
def get_sessions(user_id: int = Depends(verify_token)):
    cursor.execute("SELECT id, title, language, updatedAt FROM sessions WHERE user_id=? ORDER BY updatedAt DESC", (user_id,))
    return [{"id": r[0], "title": r[1], "language": r[2], "updatedAt": r[3]} for r in cursor.fetchall()]

@app.post("/api/refine/sessions")
def create_session(data: SessionBody, user_id: int = Depends(verify_token)):
    cursor.execute("INSERT INTO sessions(user_id, title, language) VALUES (?, ?, ?)", (user_id, data.title, data.language))
    conn.commit()
    sid = cursor.lastrowid
    cursor.execute("SELECT updatedAt FROM sessions WHERE id=?", (sid,))
    row = cursor.fetchone()
    return {"id": sid, "title": data.title, "language": data.language, "updatedAt": row[0] if row else None}

@app.get("/api/refine/sessions/{sid}")
def get_session(sid: int, user_id: int = Depends(verify_token)):
    cursor.execute("SELECT id, title, language, updatedAt FROM sessions WHERE id=? AND user_id=?", (sid, user_id))
    s = cursor.fetchone()
    if not s:
        raise HTTPException(404, "Session not found")
    cursor.execute(
        "SELECT id, refined_code, explanation, language, score, created_at FROM refinements WHERE session_id=? ORDER BY created_at DESC",
        (sid,))
    return {
        "id": s[0], "title": s[1], "language": s[2], "updatedAt": s[3],
        "refinements": [
            {"id": r[0], "refinedCode": r[1], "explanation": r[2],
             "language": r[3], "score": r[4], "createdAt": r[5]}
            for r in cursor.fetchall()
        ]
    }

@app.delete("/api/refine/sessions/{sid}")
def delete_session(sid: int, user_id: int = Depends(verify_token)):
    cursor.execute("SELECT id FROM sessions WHERE id=? AND user_id=?", (sid, user_id))
    if not cursor.fetchone():
        raise HTTPException(404, "Session not found")
    cursor.execute("DELETE FROM sessions WHERE id=?", (sid,))
    cursor.execute("DELETE FROM refinements WHERE session_id=?", (sid,))
    conn.commit()
    return {"ok": True}

# ---- Stream API ----
@app.post("/api/refine/sessions/{sid}/refine")
def refine(sid: int, body: RefineBody, user_id: int = Depends(verify_token)):
    cursor.execute("SELECT id FROM sessions WHERE id=? AND user_id=?", (sid, user_id))
    if not cursor.fetchone():
        raise HTTPException(404, "Session not found")

    def generator():
        try:
            for ch in "Analyzing...\nFixing...\nOptimizing...\n":
                yield f"data: {json.dumps({'chunk': ch})}\n\n"
                time.sleep(0.003)

            ai_result, model_used = ai_refine(body.code, body.language)
            refined     = ai_result.get("refinedCode", body.code)
            explanation = ai_result.get("explanation", "")
            score       = calc_score(refined)

            cursor.execute(
                "INSERT INTO refinements(session_id,original_code,refined_code,explanation,language,score) VALUES (?,?,?,?,?,?)",
                (sid, body.code, refined, explanation, body.language, score))
            cursor.execute("UPDATE sessions SET updatedAt=CURRENT_TIMESTAMP WHERE id=?", (sid,))
            conn.commit()

            yield f"data: {json.dumps({'done': True, 'refinedCode': refined, 'explanation': explanation, 'errorChanges': ai_result.get('errorChanges', []), 'score': score, 'model': model_used})}\n\n"

        except Exception as e:
            print(f"Generator error: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(generator(), media_type="text/event-stream")

# ---- Static / frontend ----
frontend_path = Path(__file__).parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

@app.get("/")
async def root():
    html = frontend_path / "index.html"
    if html.exists():
        return FileResponse(html)
    return {"message": "Frontend not found"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app",
                host=os.getenv("HOST", "0.0.0.0"),
                port=int(os.getenv("PORT", 8000)),
                reload=os.getenv("RELOAD", "true").lower() == "true",
                log_level="info")
