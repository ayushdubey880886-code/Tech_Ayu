FROM python:3.11-slim

WORKDIR /app

# Required system dependencies for psycopg2
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose the port Render expects (default 10000)
EXPOSE 10000

# Command to run the app
CMD ["gunicorn", "app:app"]