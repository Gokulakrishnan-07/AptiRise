# AptiRise 🚀 — Next-Gen Aptitude Practice Game

> **Master Aptitude. One Level at a Time.**  
> An interactive, Apple-inspired aptitude learning game powered by FastAPI, SQLAlchemy, Web Audio API sound synthesis, and Hugging Face AI assistance.

---

## 🌟 Overview & Core Philosophy

**AptiRise** reimagines traditional, static quantitative and logical quiz platforms as a dynamic **game progression system**. Rather than confronting users with overwhelming question lists, AptiRise structures aptitude practice across progressive tiers (**Level 1 Beginner → Level 2 Easy → Level 3 Intermediate → Level 4 Advanced → Level 5 Expert**).

### Key Highlights
- **Apple-Inspired Luxury Interface**: Subtle glassmorphism, fluid micro-interactions, dark/light theme persistence, typography tuned for readability, and zero clutter.
- **Card-Driven Game Arena**: Single-card question flow with animated card transitions, countdown timers, instant answer evaluation, step-by-step explanations, and mathematical formula shortcuts.
- **Robust Gamification Engine**:
  - Base correct answer: **+100 XP**
  - Speed bonuses: **+50 XP** (<50% time) and **+100 XP** (<25% time)
  - Perfect level bonus: **+250 XP**
  - Daily challenge blitz: **+500 XP** and streak preservation
  - Global user leveling curve and 8 unlockable achievements.
- **Integrated Web Audio Sound Engine**: High-fidelity synthesized sound effects (chimes, clicks, level-up fanfares) generated dynamically via the Web Audio API with zero external audio asset dependencies. Includes a global Sound ON/OFF switch.
- **Automated PDF Question Import Pipeline**: Drag-and-drop aptitude exam papers and question PDFs. Automatically extracts questions, options (A-D), answers, explanations, shortcuts, performs AI topic classification and difficulty estimation, and detects duplicate questions for admin review before publishing.
- **Offline-Resilient AI**: Integrates Hugging Face zero-shot classification using `HF_TOKEN`, with an instant fallback rule-based semantic heuristic engine when offline or if no token is provided.

---

## 🛠 Tech Stack

- **Backend**: Python 3.10+ / 3.14+, [FastAPI](https://fastapi.tiangolo.com/), Starlette, Uvicorn (ASGI)
- **Database & ORM**: [SQLAlchemy 2.0](https://www.sqlalchemy.org/) with connection pooling (SQLite default for local development, PostgreSQL ready for production)
- **Templating**: Jinja2 with modern modular templates
- **Frontend**: Vanilla CSS3 custom design tokens, modern ES6+ JavaScript, Web Audio API synthesizer
- **PDF Extraction**: `pypdf` multi-pattern regex engine
- **Authentication**: JWT tokens (HTTP-only cookies + Bearer headers), bcrypt password hashing, and Google OAuth2
- **Testing**: `pytest` comprehensive test suite (21 unit and integration tests)

---

## 📁 Project Structure

```
AptiRise/
├── app/
│   ├── main.py                  # FastAPI application, lifespan & startup hooks
│   ├── config.py                # Pydantic Settings reading from .env
│   ├── database.py              # SQLAlchemy engine & session factory
│   ├── templates.py             # Centralized modern template response helper
│   ├── models/                  # SQLAlchemy Database Models
│   │   ├── user.py              # User & OAuthAccount models
│   │   ├── game.py              # Category, Collection, Level, Question, Attempts, Achievements
│   │   └── admin.py             # PdfImport, PdfImportQuestion, Setting, AuditLog
│   ├── schemas/                 # Pydantic Request/Response Models
│   │   ├── user.py              # Auth schemas
│   │   ├── game.py              # Game mechanics & answer submission schemas
│   │   └── admin.py             # Question CRUD & PDF approval schemas
│   ├── services/
│   │   ├── auth.py              # Bcrypt hashing, JWT encoding/decoding, admin bootstrap
│   │   ├── gamification.py      # XP calculation, level progression curve, streak tracking
│   │   ├── ai.py                # Hugging Face API client & local heuristic fallback
│   │   ├── pdf_parser.py        # PDF question extraction & duplicate detection
│   │   └── audit.py             # Admin security & operational audit logging
│   └── routers/
│       ├── auth.py              # Login, Register, Google OAuth, Profile endpoints
│       ├── game.py              # Dashboard, Collections, Levels, Question Arena, Mistakes
│       ├── daily.py             # Daily Blitz challenge
│       ├── achievements.py      # Badges & rewards showcase
│       ├── profile.py           # User stats & preference configuration
│       └── admin.py             # Admin Dashboard, Question CRUD, PDF review, Settings, Audit
├── static/
│   ├── css/app.css              # Apple-inspired CSS design system & dark/light mode
│   └── js/
│       ├── sound.js             # Web Audio API sound synthesizer
│       ├── game.js              # Interactive question card player & timer
│       └── app.js               # Theme toggling & preference management
├── templates/                   # Jinja2 HTML templates
│   ├── base.html                # Base layout & navbar
│   ├── index.html               # Landing page
│   ├── dashboard.html           # User dashboard & progress overview
│   ├── collection.html          # Level progression list (Levels 1-5)
│   ├── play.html                # Game question arena
│   ├── daily.html               # Daily Blitz arena
│   ├── review.html              # Mistake review & formula revision
│   ├── achievements.html        # Badges showcase
│   ├── profile.html             # Profile & preferences
│   ├── login.html               # Sign in
│   ├── register.html            # Sign up
│   ├── error.html               # Custom 404/500 error display
│   └── admin/
│       ├── base.html            # Admin base layout
│       ├── dashboard.html       # Analytics & topic charts
│       ├── questions.html       # Question Bank CRUD
│       ├── pdf_import.html      # PDF drag-and-drop uploader
│       ├── pdf_review.html      # AI review & duplicate detection table
│       ├── settings.html        # Engine parameters configuration
│       └── audit_logs.html      # Immutable audit trail
├── scripts/
│   └── seed.py                  # Database seeder with sample topics, levels, and questions
├── tests/                       # Complete automated test suite
├── .env.example                 # Template environment variables
├── requirements.txt             # Production dependencies
└── README.md
```

---

## ⚡ Quick Start & Installation

### 1. Clone the repository
```bash
git clone https://github.com/your-username/AptiRise.git
cd AptiRise
```

### 2. Set up virtual environment
```bash
# Windows
python -m venv .venv
.\.venv\Scripts\activate

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Key configuration settings in `.env`:
```env
# Application
APP_NAME=AptiRise
APP_ENV=development
SECRET_KEY=your-super-secret-key-32-characters-minimum

# Database (SQLite default for local, or PostgreSQL)
DATABASE_URL=sqlite:///./aptirise.db
# DATABASE_URL=postgresql://user:password@localhost:5432/aptirise

# Hugging Face AI (Optional: works offline without token)
HF_TOKEN=your_hugging_face_token_here

# Google OAuth (Optional: required for Google Sign-In)
GOOGLE_CLIENT_ID=your_google_client_id_here
GOOGLE_CLIENT_SECRET=your_google_client_secret_here
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback

# Initial Administrator Credentials (Bootstrapped automatically on first run)
ADMIN_USERNAME=admin
ADMIN_EMAIL=admin@aptirise.internal
ADMIN_PASSWORD=AdminSecurePass123!
```

### 5. Seed initial aptitude topics & questions
```bash
python scripts/seed.py
```
This initializes:
- Initial administrator account
- 5 comprehensive collections (**Percentage, Profit & Loss, Time & Work, Time Speed & Distance, Number System**)
- 5 progression levels per collection (Beginner to Expert) with verified questions, explanations, and shortcuts
- 8 system achievements and default game settings.

### 6. Run the application
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
Open **http://127.0.0.1:8000** in your browser!

---

## 🔐 Credentials & Role Separation

### Default Administrator
- **URL**: `http://127.0.0.1:8000/admin`
- **Email**: `admin@aptirise.internal`
- **Password**: `AdminSecurePass123!`

*Security Note: All admin endpoints enforce server-side role checks (`get_current_admin`). Modifying frontend state or client tokens will never bypass administrative protection.*

---

## 🧪 Running Automated Tests

Run the complete test suite:
```bash
pytest
```
Test results verify:
- Password hashing and JWT generation
- Question XP and speed bonus calculations
- Level progression curve and achievement awards
- AI topic classification and confidence scoring
- PDF text extraction and regex question parsing
- Duplicate similarity scoring
- API integration endpoints and admin authorization boundaries.

---

## 🚀 Production Deployment

### Using Gunicorn + Uvicorn Workers
```bash
pip install gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Reverse Proxy (Nginx sample snippet)
```nginx
server {
    server_name aptirise.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## 📄 License
MIT License. Crafted with precision for high-yield aptitude preparation.
