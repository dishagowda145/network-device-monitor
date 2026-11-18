FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY . .
ENV BLOCK_PRIVATE_HOSTS=1
ENV PORT=5001
EXPOSE 5001
# Create a non-root user so the app does not run as root
RUN useradd -m appuser && chown -R appuser /app
USER appuser
CMD gunicorn --chdir backend --workers 1 --threads 4 --bind 0.0.0.0:$PORT wsgi:app
