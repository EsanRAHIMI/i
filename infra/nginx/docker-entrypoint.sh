#!/bin/sh
set -e

# Install wget if not available (for healthcheck)
if ! command -v wget > /dev/null 2>&1; then
    echo "Installing wget for healthcheck..."
    apk add --no-cache wget
fi

# Wait for frontend to be resolvable
echo "Waiting for frontend to be resolvable..."
MAX_RETRIES=30
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    # Try to resolve hostname using nslookup (available in alpine)
    if nslookup i-frontend 127.0.0.11 > /dev/null 2>&1 || \
       getent hosts i-frontend > /dev/null 2>&1; then
        echo "Frontend hostname resolved successfully!"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo "Waiting for frontend hostname... ($RETRY_COUNT/$MAX_RETRIES)"
    sleep 2
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "Warning: Frontend hostname could not be resolved after $MAX_RETRIES attempts"
    echo "Nginx will start anyway and will retry when frontend is available"
fi

# Test nginx configuration
echo "Testing nginx configuration..."
nginx -t || {
    echo "Error: Nginx configuration test failed"
    exit 1
}

# Start nginx
echo "Starting nginx..."
exec nginx -g "daemon off;"

