# syntax=docker/dockerfile:1.2
ARG VARIANT="3.10"
ARG arch="amd64"

# Multi-stage build
FROM --platform=linux/${arch} mcr.microsoft.com/vscode/devcontainers/python:0-${VARIANT} AS build-stage

WORKDIR /app
COPY .devcontainer/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Final stage
FROM --platform=linux/${arch} mcr.microsoft.com/vscode/devcontainers/python:0-${VARIANT} AS final-stage

WORKDIR /app
COPY --from=build-stage /app /app