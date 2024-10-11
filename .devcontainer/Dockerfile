# syntax=docker/dockerfile:1.2
ARG VARIANT="3.10"
ARG arch="amd64"

FROM --platform=linux/${arch} mcr.microsoft.com/vscode/devcontainers/python:0-${VARIANT} AS final-stage

WORKDIR /app

# Use root user to copy files and set permissions
USER root

# Copy requirements.txt from .devcontainer
COPY .devcontainer/requirements.txt ./ 

# Set file permissions on the copied requirements.txt file
RUN chmod 644 requirements.txt

# Install dependencies 
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir redis quart celery

# Copy the application files
COPY . /app

# Set correct permissions for the vscode user on the /app directory
RUN chown -R vscode:vscode /app

# Set PYTHONPATH to include the /app directory
ENV PYTHONPATH="${PYTHONPATH}:/app"

# Switch back to the vscode user after setting permissions
USER vscode

# Default command if no service-specific command is provided
CMD ["quart", "run", "--host", "0.0.0.0", "--port", "5000"]
