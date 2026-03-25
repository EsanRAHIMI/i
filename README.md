# 🌟 Ai Department - Intelligent AI Life Assistant

A next-generation **Ai Department** designed to act as your **conscious digital twin**, continuously learning, guiding, and optimizing real-world actions in real time.

---

## ⚡ Quick Start (macOS Recommended)

Get the entire local development environment running in just seconds!

```bash
# 1. Clone the repository
git clone https://github.com/EsanRAHIMI/i.git
cd app

# 2. Configure Environment
# Make sure your .env and frontend/.env.local are properly configured with your keys.

# 3. Start everything automatically!
./START.sh
```

**`START.sh`** is an automated script that:
1. Boots up the infrastructure databases (PostgreSQL, Redis, MinIO) via Docker.
2. Opens three new native Terminal tabs automatically for `Auth`, `Backend`, and `Frontend`.
3. Sets up Python virtual environments and installs all dependencies on the fly.

---

## 🏗️ Architecture & Development Strategy

This project uses a **hybrid Local + Docker** development strategy for maximum speed and hot-reloading:

- 🧱 **Infrastructure (Docker)**: `PostgreSQL`, `Redis`, and `MinIO` run effortlessly in isolated containers.
- ⚙️ **Application Layers (Local)**: `Frontend`, `Backend`, and `Auth` run completely locally on your host machine to allow lightning-fast development, hot-reloading (Next.js/Uvicorn), and easy debugging.

### 📁 Project Structure

```text
app/
├── backend/           # Main FastAPI backend (Business logic, AI routing)
├── auth/              # FastAPI Auth Microservice (JWT, OAuth)
├── frontend/          # Next.js 16 web app with Tailwind & 3D Avatar
├── database/          # Centralized Database Migration Service (Alembic)
├── docs/              # System Documentation & Reports
├── docker-compose.yml # Infrastructure definition (DBs, Cache, Storage)
└── START.sh           # Master automated startup script
```

---

## 💻 Tech Stack

- **Frontend**: Next.js 16, React 19, Tailwind CSS 4
- **Backend & Auth**: FastAPI, SQLAlchemy, Pydantic 
- **AI Integration**: LangChain, Whisper (STT), Coqui/ElevenLabs (TTS)
- **Data & Storage**: PostgreSQL (Relational), Redis (Cache/Tasks), MinIO (S3 Object Storage)

---

## 🔧 Service Endpoints

| Service | Port | Technology | Purpose |
|---------|------|------------|---------|
| **Frontend** | `3000` | Next.js | User Interface & Dashboard |
| **Backend API** | `8000` | FastAPI | Core business logic and AI integration |
| **Auth API** | `8001` | FastAPI | User Authentication and Security |
| **PostgreSQL**| `5432` | Postgres | Primary Relational Database |
| **Redis** | `6379` | Redis | Caching and task broker |
| **MinIO** | `9000` | S3-based | Object storage (Avatars, Voices, etc) |

---

## 🗄️ Database Migrations

Database tables and schemas for both `backend` and `auth` are centrally managed via the `database` service. 

To apply the latest migrations:
```bash
# Build the migration container and run it connected to your local docker Postgres
docker build -f database/Dockerfile -t database-migration .
docker run --rm --network app_app-network -e POSTGRES_DB=i_DB -e POSTGRES_USER=esan -e POSTGRES_PASSWORD=Admin_1234_1234 -e POSTGRES_HOST=i-postgres database-migration
```

---

## 🖥️ Manual Startup (Alternative to START.sh)

If you're not on macOS or prefer to run services manually, run `docker-compose up -d` to start the databases, and then follow these steps in 3 separate terminal windows:

**Terminal 1: Auth Service**
```bash
cd auth
python3 -m venv .venv-auth
source .venv-auth/bin/activate
pip install -r requirements.txt
export PYTHONPATH=src:$PYTHONPATH
python -m uvicorn auth_service.main:app --host 0.0.0.0 --port 8001 --reload
```

**Terminal 2: Backend Service**
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export PYTHONPATH=.:$PYTHONPATH
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 3: Frontend Web App**
```bash
cd frontend
npm install
npm run dev
```

---

## 📚 Documentation
Please check out the `docs/` folder for more detailed instructions and past reports:
- [Backend Local Setup Guide](docs/BACKEND_LOCAL_SETUP.md)
- [System Check / Technical Status](docs/TEST_REPORT_FA.md)

---

## 🤝 Contributing
1. Fork the repository
2. Create a feature branch
3. Implement and test your changes
4. Submit a Pull Request

## 📄 License
MIT License - see [LICENSE](LICENSE) file for details.