# Use an updated, more secure version of the Python base image
FROM python:3.11-slim-bookworm

# Create a non-root user for running the application
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set the working directory in the container
WORKDIR /app

# Copy just the bot directory into the container
# This keeps the container clean and only includes what's necessary for the bot
COPY --chown=appuser:appuser ./bot /app

# Update system packages and install security updates + curl for health checks
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies from the bot's requirements file
# Use --no-cache-dir to reduce image size and security footprint
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Switch to non-root user
USER appuser

# Expose the port the app runs on for Hugging Face's health checks
EXPOSE 8080

# Add health check (your Flask app serves health status at root)
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8080/ || exit 1

# The command to run your application when the container starts
CMD ["python", "main.py"]