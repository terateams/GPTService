import tiktoken

import hashlib
import secrets


def generate_api_key(api_secret: str):
    """Generate API key using a shared secret key"""
    salt = secrets.token_hex(8)  # Generate a random salt
    hash_object = hashlib.sha256(salt.encode('utf-8') + api_secret.encode('utf-8'))
    return salt + hash_object.hexdigest()


def validate_api_key(api_key, api_secret: str) -> bool:
    """Validate API key"""
    salt = api_key[:16]  # Get the salt from the API key
    expected_key = api_key[16:]  # Get the expected hash from the API key
    hash_object = hashlib.sha256(salt.encode('utf-8') + api_secret.encode('utf-8'))

    return hash_object.hexdigest() == expected_key


def num_tokens_from_string(string: str, encoding_name: str) -> int:
    """Returns the number of tokens in a text string."""
    encoding = tiktoken.get_encoding(encoding_name)
    num_tokens = len(encoding.encode(string))
    return num_tokens


def document_spliter_len(string: str) -> int:
    """Returns the number of tokens in a text string."""
    encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(string))


