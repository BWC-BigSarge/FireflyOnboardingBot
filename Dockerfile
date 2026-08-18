# Use the same Python major/minor version tested successfully on SparkedHost
FROM python:3.12-slim

# Keep Python logs visible in Docker output and avoid writing .pyc files
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Set working directory
WORKDIR /app

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
