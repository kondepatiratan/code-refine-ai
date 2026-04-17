mtsral
# Code Refine AI

An AI-powered code refinement application that uses Gemini and Mistral APIs to analyze and improve your code.

## Project Structure

```
code-refine-ai/
├── backend/
│   ├── main.py              # FastAPI backend server
│   ├── requirements.txt      # Python dependencies
│   ├── .env                  # Environment configuration (API keys)
│   └── .env.example          # Template for .env file
└── frontend/
    └── index.html            # Web interface
```

## Setup & Installation

### 1. Install Backend Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy `.env.example` to `.env` and add your API keys:

```bash
# backend/.env
GEMINI_API_KEY=your_gemini_key_here
MISTRAL_API_KEY=your_mistral_key_here
JWT_SECRET=your_secret_key
HOST=0.0.0.0
PORT=8000
```

Get your API keys from:
- **Gemini**: https://aistudio.google.com/apikey
- **Mistral**: https://console.mistral.ai/api-keys/

### 3. Start the Backend Server

```bash
cd backend
python main.py
```

The server will start at: `http://localhost:8000`

## Features

- 🎯 **Code Analysis**: Analyze and refine code in multiple languages
- 🤖 **Dual AI Models**: Uses Gemini with Mistral as fallback
- 💾 **Session Management**: Save and manage code refinement sessions
- 📝 **History Tracking**: Keep track of all refinements
- 🔐 **Authentication**: JWT-based user authentication
- 🌐 **Web Interface**: Beautiful, responsive UI

## Technology Stack

### Backend
- **FastAPI**: Modern Python web framework
- **SQLite**: Lightweight database
- **PyJWT**: JWT authentication
- **bcrypt**: Password hashing
- **Google GenerativeAI**: Gemini API client
- **Mistral AI**: Mistral API client

### Frontend
- **HTML5 + CSS3**: Responsive design
- **JavaScript**: Modern ES6+ code
- **Server-Sent Events (SSE)**: Real-time streaming responses

## API Endpoints

### Sessions
- `GET /api/refine/sessions` - List all sessions
- `POST /api/refine/sessions` - Create new session
- `GET /api/refine/sessions/{id}` - Get session details
- `DELETE /api/refine/sessions/{id}` - Delete session

### Refinement
- `POST /api/refine/sessions/{id}/refine` - Submit code for refinement

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login user

## Database Schema

### Users
```sql
CREATE TABLE users(
  id INTEGER PRIMARY KEY,
  email TEXT,
  password TEXT
)
```

### Sessions
```sql
CREATE TABLE sessions(
  id INTEGER PRIMARY KEY,
  title TEXT,
  language TEXT,
  updatedAt TIMESTAMP
)
```

### Refinements
```sql
CREATE TABLE refinements(
  id INTEGER PRIMARY KEY,
  session_id INTEGER,
  original_code TEXT,
  refined_code TEXT,
  explanation TEXT,
  language TEXT,
  score INTEGER,
  created_at TIMESTAMP
)
```

## Supported Languages

- Python
- Java (Spring/Maven)
- JavaScript
- TypeScript
- Go
- Rust
- C++
- C#
- SQL
- Other

## Development

### Project Status
✅ Backend fully configured and running
✅ Frontend aligned with backend API
✅ Environment variables configured
✅ All dependencies installed

### Next Steps
- Add user registration/login UI
- Enhance code quality scoring algorithm
- Add more language support
- Implement code diff visualization
- Add export functionality

## Troubleshooting

### API Key Errors
Ensure your `.env` file has valid API keys from Google and Mistral.

### Port Already in Use
Change PORT in `.env` to an available port (e.g., 8001)

### Database Locked
Delete `db.sqlite` and restart the server to create a fresh database.

## License

MIT License - Feel free to use this project for any purpose.
