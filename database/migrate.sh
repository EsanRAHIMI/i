#!/usr/bin/env sh
set -eu

echo "== database: running backend migrations =="
alembic -c /database/alembic.backend.ini upgrade head

echo "== database: running auth migrations =="
alembic -c /database/alembic.auth.ini upgrade head

echo "== database: done =="

