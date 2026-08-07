FROM python:3.10-slim

WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files and documentation corpus
COPY . .

# Expose port 7860
EXPOSE 7860

# Run FastAPI app with Uvicorn on host 0.0.0.0 and port 7860
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]
