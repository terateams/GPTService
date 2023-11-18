FROM condaforge/mambaforge:latest

# Set up a working directory
WORKDIR /

# Copy the project files to the working directory
COPY ./main.py /main.py
COPY ./common.py /common.py
COPY ./qdrant_index.py /qdrant_index.py
COPY ./requirements.txt /requirements.txt

# Install project dependencies
RUN pip install --no-cache-dir -r requirements.txt && \
    apt-get update && \
    apt-get install -y tesseract-ocr tesseract-ocr-chi-sim && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Expose the port
EXPOSE 8700

ENV PYTHONUNBUFFERED=1

# Set the launch command
CMD ["uvicorn","main:app"]
