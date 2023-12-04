from openai import OpenAI
import os


def openai_streaming(sysmsg, historys: list):
    """OpenAI Streaming API"""
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    messages = [
        {"role": "system", "content": sysmsg},
    ]
    for history in historys:
        messages.append(history)
    print(messages)
    completion = client.chat.completions.create(
        model="gpt-4-1106-preview",
        messages=messages,
        stream=True
    )
    for chunk in completion:
        yield chunk.choices[0].delta
