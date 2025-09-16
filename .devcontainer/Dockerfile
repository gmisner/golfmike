# syntax=docker/dockerfile:1.2
ARG VARIANT="3.10"
ARG arch="amd64"

FROM --platform=linux/${arch} mcr.microsoft.com/vscode/devcontainers/python:0-${VARIANT} AS final-stage

WORKDIR /workspace

# Use root user to copy files and set permissions
USER root

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements.txt from .devcontainer
COPY .devcontainer/requirements.txt ./ 

# Set file permissions on the copied requirements.txt file
RUN chmod 644 requirements.txt

# Install dependencies 
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy the application files
COPY . /workspace

# Set correct permissions for the vscode user on the /workspace directory
RUN chown -R vscode:vscode /workspace

# Set PYTHONPATH to include the /workspace directory
ENV PYTHONPATH="${PYTHONPATH}:/workspace"

# Switch back to the vscode user after setting permissions
USER vscode

# Default command if no service-specific command is provided
CMD ["python", "app.py"]
