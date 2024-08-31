FROM python:3.12-slim

# Set the working directory for the application
WORKDIR /post_processor

# Install necessary system packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    cron \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application source code to the container
COPY . .

# Perform setup operations and adjust permissions
RUN chmod +x main.py && \
    touch /var/log/cron.log

# Set up cron jobs by copying a crontab file into the correct directory and applying it
COPY crontab /etc/cron.d/post-processor-crontab
RUN chmod 0644 /etc/cron.d/post-processor-crontab && \
    crontab /etc/cron.d/post-processor-crontab

# Environment variables can be defined
ENV NAME GlobeNewsPostProcessor

# The container will run cron in the foreground to keep it alive
CMD ["sh", "-c", "cron && tail -f /var/log/cron.log"]