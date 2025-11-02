# i Assistant - Intelligent AI Life Assistant

A next-generation **Agentic AI Life Assistant** designed to act as your **conscious digital twin**, continuously learning, guiding, and optimizing real-world actions in real time.

## 🚀 Quick Start

Get the entire system running in 5 minutes:

```bash
# Clone the repository
git clone <repository-url>
cd i-assistant

# Run the setup script
./scripts/setup.sh

# Access the application
open http://localhost:3000
```

## 📁 Project Structure

```
i-assistant/
├── backend/           # FastAPI backend services
├── frontend/          # Next.js frontend application  
├── ai/               # AI services and models
├── auth/             # Authentication services
├── infra/            # Infrastructure configuration
├── scripts/          # Deployment and utility scripts
├── docs/             # Documentation
├── ops/              # Operations and monitoring
├── docker-compose.yml # Multi-service orchestration
└── .env.example      # Environment configuration template
```

## 🏗️ Architecture

- **Frontend**: Next.js 14 with TypeScript, Tailwind CSS, and 3D avatar
- **Backend**: FastAPI with SQLAlchemy, Celery, and Redis
- **AI Services**: Whisper STT, Coqui/ElevenLabs TTS, LangChain orchestration
- **Database**: PostgreSQL with federated learning support
- **Storage**: MinIO for object storage
- **Proxy**: Nginx with SSL termination and load balancing

## 🔧 Services

| Service | Port | Description |
|---------|------|-------------|
| Frontend | 3000 | Next.js web application |
| Backend | 8000 | FastAPI REST API |
| PostgreSQL | 5432 | Primary database |
| Redis | 6379 | Cache and message broker |
| MinIO | 9000/9001 | Object storage |
| Nginx | 80/443 | Reverse proxy |

## 🛠️ Development

### Running Services with Docker

```bash
# Start infrastructure services (PostgreSQL, Redis, MinIO, Frontend, Nginx)
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services  
docker-compose down

# Rebuild images
docker-compose build --no-cache
```

### Running Backend Locally (Recommended for Development)

برای سرعت بیشتر در توسعه، بک‌اند در لوکال اجرا می‌شود و نیازی به بیلد داکر ندارد:

```bash
# راه‌اندازی بک‌اند در لوکال
./scripts/run-backend-local.sh
```

یا به صورت دستی:

```bash
cd backend

# ایجاد محیط مجازی (فقط بار اول)
python3 -m venv venv
source venv/bin/activate

# نصب وابستگی‌ها
pip install -r requirements.txt

# تنظیم متغیرهای محیطی
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=i_DB
export POSTGRES_USER=esan
export POSTGRES_PASSWORD=Admin_1234_1234
export REDIS_URL=redis://localhost:6379/0
export MINIO_ENDPOINT=localhost:9000
export MINIO_ACCESS_KEY=esan
export MINIO_SECRET_KEY=Admin_1234_1234
export PYTHONPATH=$(pwd)

# اجرای migrations
alembic upgrade head

# راه‌اندازی سرور
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**نکات مهم:**
- سرویس‌های Docker (PostgreSQL, Redis, MinIO) باید قبل از اجرای بک‌اند در حال اجرا باشند
- بک‌اند در لوکال به پورت‌های localhost متصل می‌شود که توسط Docker در دسترس هستند
- Nginx در کانتینر به `host.docker.internal:8000` متصل می‌شود تا به بک‌اند لوکال دسترسی داشته باشد

## 📋 Requirements

- Docker & Docker Compose
- Node.js 18+ (for local development)
- Python 3.11+ (for local development)

## 🔐 Environment Configuration

Copy `.env.example` to `.env` and configure:

- Database credentials
- API keys (OpenAI, ElevenLabs, Google, WhatsApp)
- JWT secrets
- Service ports

## 📚 Documentation

- [API Documentation](docs/api.md)
- [Deployment Guide](docs/deployment.md)
- [Development Setup](docs/development.md)
- [Privacy & Security](docs/privacy.md)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `npm test`
5. Submit a pull request

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.