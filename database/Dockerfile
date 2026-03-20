FROM python:3.12-slim

WORKDIR /database

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install requirements
# Try copying and installing from root context first, fallback to current dir
COPY database/requirements.txt* ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy Model code (needed for SQLAlchemy metadata)
# These MUST exist in the build context (Root of the repo)
COPY backend /vendor/backend
COPY auth /vendor/auth

# Copy Configs and Scripts
COPY database/alembic.backend.ini* database/alembic.auth.ini* database/migrate.sh* ./
RUN chmod +x ./migrate.sh

# Copy Migrations data
COPY database/migrations /database/migrations
COPY database/src /database/src

# Default command
CMD ["./migrate.sh"]
