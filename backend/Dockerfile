# Prefer Python 3.14, fallback to 3.13, 3.12, or 3.11
FROM python:3.14-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Download and install talosctl (latest stable version)
# First try to get latest version from GitHub API, fallback to a known version
RUN TALOS_VERSION=$(curl -s https://api.github.com/repos/siderolabs/talos/releases/latest | grep -oP '"tag_name": "\K[^"]+' | head -1) && \
    if [ -z "$TALOS_VERSION" ]; then TALOS_VERSION="v1.7.0"; fi && \
    curl -L "https://github.com/siderolabs/talos/releases/download/${TALOS_VERSION}/talosctl-linux-amd64" -o /usr/local/bin/talosctl && \
    chmod +x /usr/local/bin/talosctl

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
