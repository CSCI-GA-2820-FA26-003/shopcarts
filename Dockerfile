FROM python:3.12-slim

WORKDIR /app

# Install Python dependencies
RUN pip install --no-cache-dir pipenv

COPY Pipfile Pipfile.lock ./

RUN pipenv install --system --deploy

# Copy application source
COPY service/ ./service/
COPY wsgi.py ./

# Run the application as a non-root user
RUN useradd --create-home appuser
USER appuser

ENV PORT=8080

EXPOSE 8080

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--log-level=info", "wsgi:app"]
