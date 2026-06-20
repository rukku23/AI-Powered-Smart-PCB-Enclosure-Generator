# EnclosureAI Backend — Production Docker Image
# Includes OpenSCAD CLI for CAD rendering

FROM python:3.11-slim

# Prevent interactive prompts during apt install
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies including OpenSCAD
RUN apt-get update && apt-get install -y --no-install-recommends \
    openscad \
    xvfb \
    libgl1-mesa-glx \
    libglu1-mesa \
    && rm -rf /var/lib/apt/lists/*

# Verify OpenSCAD CLI installation
RUN xvfb-run openscad --version || echo "OpenSCAD version check (may show on stderr)"

# Set working directory
WORKDIR /app

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directory for generated files
RUN mkdir -p /app/generated_files

# Set environment defaults
ENV OPENSCAD_CLI_PATH=/usr/bin/openscad
ENV GENERATED_FILES_DIR=/app/generated_files
ENV PYTHONUNBUFFERED=1

# Expose API port
EXPOSE 8000

# Run with uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
