# Use an updated, more secure version of the Python base image
FROM python:3.11-slim-bookworm

# Create a non-root user for running the application
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set the working directory in the container
WORKDIR /app

# Copy just the bot directory into the container
# This keeps the container clean and only includes what's necessary for the bot
COPY --chown=appuser:appuser ./bot /app

# Update system packages and install security updates + curl for health checks + dnsutils for debugging
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends curl dnsutils && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Configure DNS settings to fix hostname resolution issues
RUN echo "nameserver 8.8.8.8" > /etc/resolv.conf && \
    echo "nameserver 8.8.4.4" >> /etc/resolv.conf && \
    echo "nameserver 1.1.1.1" >> /etc/resolv.conf && \
    echo "options timeout:2 attempts:3 rotate single-request-reopen" >> /etc/resolv.conf

# Install Python dependencies from the bot's requirements file
# Use --no-cache-dir to reduce image size and security footprint
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Switch to non-root user
USER appuser

# Set environment variables for better network handling
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV TELEGRAM_API_TIMEOUT=30
ENV HTTPX_TIMEOUT=30

# Expose the port the app runs on for Hugging Face's health checks
EXPOSE 8080

# Add health check (your Flask app serves health status at root)
HEALTHCHECK --interval=30s --timeout=15s --start-period=45s --retries=5 \
    CMD curl -f http://localhost:8080/ || exit 1

# The command to run your application when the container starts
CMD ["python", "main.py"]