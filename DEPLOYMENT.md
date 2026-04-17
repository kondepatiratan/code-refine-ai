# Code Refine AI - Deployment Guide

## 📋 Prerequisites
- Python 3.8+
- Pip package manager
- Valid API keys (Gemini & Mistral)
- GitHub account (for deployment to Vercel/Heroku)

---

## 🚀 Local Deployment

### Step 1: Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### Step 2: Configure Environment
Create `.env` file in `backend/`:
```
GEMINI_API_KEY=your_gemini_key
MISTRAL_API_KEY=your_mistral_key
JWT_SECRET=your_secret_key_here
HOST=0.0.0.0
PORT=8000
DATABASE_PATH=db.sqlite
```

### Step 3: Run Server
```bash
python main.py
```

**Expected Output:**
```
INFO:     Will watch for changes in these directories: [...]
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Step 4: Access Application
- **Frontend:** http://localhost:8000
- **API:** http://localhost:8000/api/refine/sessions

---

## 🐳 Docker Deployment

### Step 1: Create Dockerfile
```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/main.py .
COPY frontend/ /app/frontend/

ENV HOST=0.0.0.0
ENV PORT=8000

CMD ["python", "main.py"]
```

### Step 2: Build & Run
```bash
docker build -t code-refine-ai .
docker run -p 8000:8000 --env-file .env code-refine-ai
```

---

## ☁️ Deploy to Heroku

### Step 1: Create Heroku App
```bash
heroku create your-app-name
```

### Step 2: Add Environment Variables
```bash
heroku config:set GEMINI_API_KEY=your_key --app your-app-name
heroku config:set MISTRAL_API_KEY=your_key --app your-app-name
heroku config:set JWT_SECRET=your_secret --app your-app-name
```

### Step 3: Create Procfile
```
web: cd backend && python main.py
```

### Step 4: Deploy
```bash
git push heroku main
```

---

## ☁️ Deploy to Render (Recommended)

### Step 1: Prepare Repository
Ensure your project is pushed to GitHub. Render deploys directly from GitHub repositories.

```bash
git add .
git commit -m "Prepare for Render deployment"
git push origin main
```

### Step 2: Connect GitHub to Render

1. Go to [render.com](https://render.com)
2. Sign up or log in with your GitHub account
3. Click **"New +"** → **"Web Service"**
4. Select your GitHub repository
5. Choose the appropriate branch (usually `main`)

### Step 3: Configure Service Settings

Fill in the following values:

- **Name:** `code-refine-ai` (or your preferred name)
- **Environment:** `Python 3`
- **Region:** Choose the region closest to your users
- **Branch:** `main` (or your default branch)
- **Build Command:** 
  ```bash
  pip install -r backend/requirements.txt
  ```
- **Start Command:** 
  ```bash
  cd backend && python main.py
  ```

### Step 4: Add Environment Variables

In the Render dashboard, scroll to the **"Environment"** section and add these variables:

```
GEMINI_API_KEY=your_gemini_api_key
MISTRAL_API_KEY=your_mistral_api_key
JWT_SECRET=your_secure_random_secret
HOST=0.0.0.0
PORT=8000
DATABASE_PATH=/tmp/db.sqlite
RELOAD=false
```

**⚠️ Important Notes:**
- Use `/tmp/db.sqlite` for the database path (Render's `/app` directory is ephemeral)
- Set `RELOAD=false` for production
- Generate a strong JWT_SECRET (use a password generator)

### Step 5: Deploy

Click the **"Deploy"** button. Monitor the logs in the Render dashboard.

Once deployed, you'll get a URL like: `https://code-refine-ai.onrender.com`

### Step 6: Verify Deployment

Test your deployment:

```bash
# Check frontend
curl https://code-refine-ai.onrender.com/

# Test API
curl https://code-refine-ai.onrender.com/api/refine/sessions
```

### Step 7: Production Setup - Add PostgreSQL

For persistent storage, create a PostgreSQL database:

1. In Render dashboard, click **"New +"** → **"PostgreSQL"**
2. Configure and note the connection string
3. Add `DATABASE_URL` to Web Service environment variables
4. Update code to use PostgreSQL (see PostgreSQL Integration section below)

---

## 🐘 PostgreSQL Integration (Production)

SQLite data is lost when Render restarts. Use PostgreSQL for persistence:

### Update backend/main.py

```python
import os
import psycopg2

DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL and DATABASE_URL.startswith("postgresql"):
    # Use PostgreSQL
    conn = psycopg2.connect(DATABASE_URL)
else:
    # Use SQLite for development
    DATABASE_PATH = os.getenv("DATABASE_PATH", "db.sqlite")
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
```

### Add psycopg2 to requirements.txt

```bash
echo "psycopg2-binary==2.9.9" >> backend/requirements.txt
```

---

## 📋 Deployment Checklist

- [ ] Repository pushed to GitHub
- [ ] `render.yaml` file exists in root directory
- [ ] `backend/.env.example` is up to date
- [ ] `backend/main.py` reads environment variables for HOST, PORT, DATABASE_PATH
- [ ] API keys obtained and verified
- [ ] DATABASE_PATH set to `/tmp/db.sqlite` for Render
- [ ] RELOAD set to `false` for production
- [ ] Service deployed and tested successfully

---

## 🔧 Troubleshooting Render Deployment

| Issue | Solution |
|-------|----------|
| **Port binding error** | Ensure `HOST=0.0.0.0` and PORT read from env |
| **"Module not found"** | Check all dependencies in `backend/requirements.txt` |
| **Build failure** | Verify Build Command: `pip install -r backend/requirements.txt` |
| **API not responding** | Check Start Command path is correct |
| **Database lost after restart** | SQLite is ephemeral; add PostgreSQL database |
| **Cold starts (30s)** | Normal for free tier; upgrade for faster performance |
| **Environment variables not set** | Verify in Render dashboard, not in `.env` file |

---

## 📚 Additional Resources

- [Render Documentation](https://docs.render.com/)
- [FastAPI Deployment Guide](https://fastapi.tiangolo.com/deployment/)
- [Gemini API Documentation](https://ai.google.dev/docs/)
- [Mistral AI Documentation](https://docs.mistral.ai/)

---

## ☁️ Deploy to Railway

### Step 1: Install Railway CLI
```bash
npm install -g @railway/cli
```

### Step 2: Login & Init
```bash
railway login
railway init
```

### Step 3: Configure
```bash
railway link
railway variables set GEMINI_API_KEY=your_key
railway variables set MISTRAL_API_KEY=your_key
railway variables set JWT_SECRET=your_secret
```

### Step 4: Deploy
```bash
railway up
```

---

## ☁️ Deploy to AWS Lambda + API Gateway

### Step 1: Install Serverless Framework
```bash
npm install -g serverless
```

### Step 2: Configure Serverless
```bash
serverless config credentials --provider aws --key YOUR_KEY --secret YOUR_SECRET
```

### Step 3: Create serverless.yml
```yaml
service: code-refine-ai

provider:
  name: aws
  runtime: python3.10
  region: us-east-1
  environment:
    GEMINI_API_KEY: ${env:GEMINI_API_KEY}
    MISTRAL_API_KEY: ${env:MISTRAL_API_KEY}

functions:
  api:
    handler: backend/main.app
    events:
      - http:
          path: /{proxy+}
          method: ANY
          cors: true
```

### Step 4: Deploy
```bash
serverless deploy
```

---

## 📊 Production Optimization

### 1. Enable Caching
```python
# In main.py
import hashlib
cache = {}

def get_cache_key(code, language):
    return hashlib.md5(f"{code}_{language}".encode()).hexdigest()
```

### 2. Rate Limiting
```bash
pip install slowapi
```

### 3. Use PostgreSQL (instead of SQLite)
```bash
pip install psycopg2-binary
```

### 4. Enable CORS Only for Your Domain
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourapp.com"],
    allow_credentials=True,
)
```

### 5. Add HTTPS/SSL
- Heroku: Automatic (with custom domain)
- Docker: Use Nginx reverse proxy
- AWS: Use CloudFront + ACM

---

## 🔒 Security Checklist

- ✅ Never commit `.env` files
- ✅ Use strong JWT_SECRET (min 32 chars)
- ✅ Enable HTTPS/SSL in production
- ✅ Set database file permissions (chmod 600)
- ✅ Use environment variables for all secrets
- ✅ Enable request rate limiting
- ✅ Add CORS restrictions
- ✅ Keep dependencies updated

---

## 📟 Monitor & Maintain

### View Logs
```bash
# Heroku
heroku logs --tail

# Render
render logs

# Railway
railway logs

# Local
# Check terminal output
```

### Database Backup
```bash
# SQLite backup
cp db.sqlite db.sqlite.backup
```

### Update Dependencies
```bash
pip install --upgrade -r backend/requirements.txt
```

---

## 🆘 Troubleshooting

| Issue | Solution |
|-------|----------|
| Port already in use | `lsof -i :8000` then kill process |
| API key rejected | Check `.env` file exists and keys are correct |
| CORS errors | Verify `allow_origins` in FastAPI CORS config |
| Database locked | Restart server, ensure no other instances running |
| Out of API quota | Implement caching, reduce request frequency |

---

## 📞 Support

- **GitHub Issues:** Report bugs
- **API Docs:** http://localhost:8000/docs (Swagger UI)
- **API Status:** Check Gemini/Mistral status pages
