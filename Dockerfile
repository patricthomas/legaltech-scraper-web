FROM python:3.12-slim

WORKDIR /app

# Install dependencies first (cached layer)
COPY requirements_web.txt .
RUN pip install --no-cache-dir -r requirements_web.txt

# Copy app files
COPY generate_blast.py sites_config.py web_app.py ./
COPY templates/ templates/

EXPOSE 5050

ENV DOCKER_ENV=1

CMD ["python", "web_app.py"]
