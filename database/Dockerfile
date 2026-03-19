FROM python:3.12-slim

WORKDIR /database

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY database/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# vendor code needed only for metadata imports (no runtime app)
COPY backend ./vendor/backend
COPY auth ./vendor/auth

# migrations runner + alembic configs
COPY database/alembic.backend.ini ./alembic.backend.ini
COPY database/alembic.auth.ini ./alembic.auth.ini
COPY database/migrate.sh ./migrate.sh
RUN chmod +x ./migrate.sh

# migration envs
COPY database/migrations ./migrations
COPY database/src ./src

# default command: run migrations then exit
CMD ["./migrate.sh"]

