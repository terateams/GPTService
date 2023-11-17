
    8""""8 8""""8 ""8"" 8""""8 8"""" 8"""8  88   8 8  8""""8 8"""" 
    8    " 8    8   8   8      8     8   8  88   8 8  8    " 8     
    8e     8eeee8   8e  8eeeee 8eeee 8eee8e 88  e8 8e 8e     8eeee 
    88  ee 88       88      88 88    88   8 "8  8  88 88     88    
    88   8 88       88  e   88 88    88   8  8  8  88 88   e 88    
    88eee8 88       88  8eee88 88eee 88   8  8ee8  88 88eee8 88eee 
                                                               

# GPTService

## Introduction of GPTService

GPTService is an advanced API project designed for custom GPT models. It follows the OpenAPI specification and provides efficient and flexible vector knowledge base retrieval and vector database management capabilities.

<img width="789" alt="image" src="https://github.com/terateams/GPTService/assets/377938/12756a21-dc4a-49e6-99ab-0359162cd405">

## Features

- Vector Knowledge Base Retrieval: Efficiently retrieve knowledge related to custom GPT models.
- Vector Database Management: Flexible database management tool for users to manage and update data.
- OpenAPI Compliance: Ensures compatibility with existing systems and tools.
- Easy Integration: Suitable for a wide range of programming environments and frameworks.

## Vector database

Qdrant is currently supported, and more vector database types will be considered in the future.

## Quick Start

### docker-compose

> Use the .env environment variable file or configure docker-compose.yml

```yaml
version: "3"
services:
  gptservice:
    container_name: "gptservice"
    image: talkincode/gptservice:latest
    logging:
      driver: "json-file"
      options:
        max-size: "50m"
    environment:
        - API_SECRET=${API_KEY}
        - OPENAI_API_TYPE=${OPENAI_API_TYPE}
        - AZURE_OPENAI_API_VERSION=${AZURE_OPENAI_API_VERSION}
        - AZURE_OPENAI_API_BASE=${AZURE_OPENAI_API_BASE}
        - AZURE_OPENAI_API_KEY=${AZURE_OPENAI_API_KEY}
        - OPENAI_API_KEY=${OPENAI_API_KEY}
        - QDRANT_URL=${QDRANT_URL}
        - DATA_DIR=/data
    volumes:
      - gptservice-volume:/data
    ports:
      - "8888:8700"
    command: ["uvicorn", "--host","0.0.0.0","main:app"]
    networks:
      gptservice_network:

networks:
  gptservice_network:

volumes:
  gptservice-volume:

```

- Generate Apikey

> This is a simple apikey generator function that can be enhanced to meet your needs when used in a production environment.

```python
import hashlib
import secrets

def generate_api_key(api_secret: str):
    salt = secrets.token_hex(8)
    hash_object = hashlib.sha256(salt.encode('utf-8') + api_secret.encode('utf-8'))
    return salt + hash_object.hexdigest()

generate_api_key("your api secret")
```


## Contribute

We welcome contributions of any kind, including but not limited to issues, pull requests, documentation, examples, etc.
