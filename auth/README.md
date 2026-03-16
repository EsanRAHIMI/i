# I App Auth Service

Authentication microservice for I App.

## Features

- User registration and authentication
- JWT token management (RS256)
- Password reset via email
- Avatar upload and management
- User settings management
- Rate limiting and security headers
- Structured logging and monitoring

## Development Setup

### Prerequisites

- Python 3.11+
- PostgreSQL (or SQLite for testing)
- Redis (optional)

### Installation

1. Clone the repository
2. Install shared library:
```bash
cd shared
pip install -e .
```

3. Install auth service:
```bash
cd ../auth-service
pip install -e .
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Run the service:
```bash
uvicorn auth_service.main:app --host 0.0.0.0 --port 8001 --reload
```

The API will be available at `http://localhost:8001`

### API Documentation

- Swagger UI: `http://localhost:8001/v1/docs`
- ReDoc: `http://localhost:8001/v1/redoc`

## Docker Deployment

```bash
# Build
docker build -t i-app-auth-service .

# Run
docker run -p 8001:8001 --env-file .env i-app-auth-service
```

## Environment Variables

See `.env.example` for all available configuration options.

### Important Variables

- `JWT_PRIVATE_KEY` / `JWT_PUBLIC_KEY`: RSA keys for JWT tokens
- `DATABASE_URL`: PostgreSQL connection string
- `AUTH_PUBLIC_BASE_URL`: Base URL for generating absolute URLs (e.g., avatar URLs)
- `SMTP_*`: Email configuration for password reset

## API Endpoints

### Authentication
- `POST /v1/register` - User registration
- `POST /v1/login` - User login
- `POST /v1/refresh` - Refresh access token
- `POST /v1/logout` - User logout

### User Management
- `GET /v1/me` - Get current user profile
- `PATCH /v1/me` - Update user profile
- `GET /v1/settings` - Get user settings
- `PATCH /v1/settings` - Update user settings
- `PUT /v1/password` - Change password

### Password Reset
- `POST /v1/forgot-password` - Request password reset
- `POST /v1/reset-password` - Reset password with token

### Avatar Management
- `POST /v1/avatar/upload` - Upload avatar image
- `GET /v1/avatar/{filename}` - Get avatar image

## Monitoring

- Health check: `GET /health`
- Metrics: `GET /metrics` (if enabled)

## Security Features

- JWT token validation (RS256)
- Rate limiting
- CORS protection
- Request logging with correlation IDs
- Input validation and sanitization
