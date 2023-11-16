FROM condaforge/mambaforge:latest

# Set up a working directory
WORKDIR /

# Copy the project files to the working directory
COPY ./main.py /main.py
COPY ./common.py /common.py
COPY ./qdrant_index.py /qdrant_index.py
COPY ./requirements.txt /requirements.txt

# Install project dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port
EXPOSE 8700

# Set the launch command
CMD ["uvicorn","main:app"]
