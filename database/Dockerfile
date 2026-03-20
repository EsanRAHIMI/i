FROM python:3.12-slim

WORKDIR /database

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install requirements
# Assumes build context is the 'database' directory
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# migrations runner + alembic configs
COPY alembic.backend.ini ./alembic.backend.ini
COPY alembic.auth.ini ./alembic.auth.ini
COPY migrate.sh ./migrate.sh
RUN chmod +x ./migrate.sh

# migration envs and logic
COPY migrations ./migrations
COPY src ./src

# Defualt command
CMD ["./migrate.sh"]
