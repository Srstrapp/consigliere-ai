FROM python:3.11-slim

WORKDIR /app

# Copy requirements
COPY backend/requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend structure (so /app/backend/app/... exists)
COPY backend/ ./backend/

# Expose port
ENV PORT=8000
EXPOSE 8000

# Run with correct module path
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]