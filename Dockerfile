# Consigliere AI - Dockerfile para Railway
FROM python:3.11-slim

WORKDIR /app

# Copy backend
COPY backend/requirements.txt ./backend/requirements.txt

# Install dependencies
RUN pip install --no-cache-dir -r ./backend/requirements.txt

# Copy app
COPY backend/app/ ./app/

# Expose port
ENV PORT=8000
EXPOSE 8000

# Run
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]