FROM python:3.10-slim

# Copy the application code
COPY . /app

# Set the working directory
WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port 8000 for FastAPI
EXPOSE 8000

ENTRYPOINT ["uvicorn"]

ENV GOOGLE_API_KEY=<FMI>

# Command to run the FastAPI application
CMD ["fast-api:app", "--host", "0.0.0.0", "--port", "8000"]