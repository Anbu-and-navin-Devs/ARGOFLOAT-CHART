FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY ARGO_CHATBOT/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


COPY ARGO_CHATBOT/ .


EXPOSE 7860

# Run with gunicorn - use sync worker to avoid sendfile issues
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:7860", "--workers", "2", "--timeout", "120", "--worker-class", "sync"]
