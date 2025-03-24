FROM python:3.9-slim

# Install Poetry
RUN pip install poetry==1.5.1

# Configure Poetry to not create a virtual environment inside the container
RUN poetry config virtualenvs.create false

# Set working directory
WORKDIR /app

# Copy Poetry configuration files
COPY pyproject.toml poetry.lock* ./

# Install dependencies
RUN poetry install --no-dev --no-interaction --no-ansi

# Copy application code
COPY . .

# Expose the port
EXPOSE 8080

# Run the application
CMD ["python", "-m", "time_service.main", "--host", "0.0.0.0"]