# Use a lightweight Python base image
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install system dependencies (if needed, e.g. for git or build tools)
# RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create a non-root user for security
RUN useradd -m botuser
USER botuser

# Command to run the bot
CMD ["python", "bot.py"]

LABEL org.opencontainers.image.source=https://github.com/the-bwc/onboarding-bot
LABEL org.opencontainers.image.authors="Patrick Pedersen <github-docker@patrickpedersen.tech> Black Widow Company <S-1@the-bwc.com>"