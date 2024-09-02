FROM python:3.12-slim

# Set the working directory for the application
WORKDIR /post_processor

# Copy package.json and package-lock.json
COPY requirements.txt .

# Install project dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files and folders to the current working directory
COPY . .

# Environment variables can be defined here or overridden at runtime
ENV PROCESSOR_ENV=prod
ENV PROCESSOR_LOG_LEVEL=INFO
ENV PROCESSOR_CRON_SCHEDULE="15 * * * *"
ENV PROCESSOR_RUN_NOW=true


# Command to run the application
CMD ["python", "main.py"]