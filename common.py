import tiktoken
import hashlib
import secrets
from graphviz import Digraph
import random
from PIL import ImageFilter, ImageEnhance


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


def preprocess_image(img):
    """对图片进行预处理"""
    img = img.convert('L')
    # 图像锐化
    img = img.filter(ImageFilter.SHARPEN)
    # 调整对比度
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(2)
    # 二值化
    img = img.point(lambda x: 0 if x < 128 else 255, '1')
    return img


def optimize_text_by_openai(content):
    """通过LLM 修正优化文本"""
    from openai import OpenAI
    client = OpenAI()
    response = client.chat.completions.create(
        model="gpt-4-1106-preview",
        messages=[
            {"role": "system", "content":
                "请你充当一个文本修复专家， 我会提供给你一段 OCR 识别的可能存在识别错误文本,你需要提供给我修正后的结果，优化策略如下："
                "- 这些文本可能会有一些识别错误，你需要分析并纠正这些错误\n"
                "- 识别的文本可能会有排版错误，尽量纠正这些错误\n"
                "- 删除掉一些无意义的内容\n\n"
             },
            {"role": "user", "content": content},
        ]
    )
    return response.choices[0].message.content


def generate_light_color(pcolor: str):
    """生成比给定颜色浅一半的颜色"""
    r, g, b = int(pcolor[1:3], 16), int(pcolor[3:5], 16), int(pcolor[5:7], 16)
    r = int(r + (255 - r) / 2)
    g = int(g + (255 - g) / 2)
    b = int(b + (255 - b) / 2)
    return '#%02x%02x%02x' % (r, g, b)


def generate_random_dark_color():
    """
    生成随机深色的函数。
    通过确保RGB值不会太高，从而生成深色调。
    """
    r = random.randint(0, 100)
    g = random.randint(0, 100)
    b = random.randint(0, 100)
    return f'#{r:02x}{g:02x}{b:02x}'


# 改进的思维导图构建函数
def build_mind_map(graph, node, parent, structure, level=0, parent_color=None):
    # 根据层级设置样式
    if level == 0:  # 根节点
        node_color = generate_random_dark_color()
        graph.node(node, style='filled', color=node_color, fontsize="21", fontname='WenQuanYi Micro Hei', fontcolor='white',
                   shape='tripleoctagon',peripheries="2", label=node)
    elif level == 1:  # 第二层节点
        node_color = generate_random_dark_color()
        graph.node(node, style='filled', color=node_color, fontsize="18", fontname='WenQuanYi Micro Hei', fontcolor='white',
                   shape='hexagon',peripheries="2", label=node)
    elif level == 2:  # 第三层节点
        node_color = generate_light_color(parent_color)
        graph.node(node, style='filled', color=node_color, fontsize="16", shape='note', fontname='WenQuanYi Micro Hei', label=node)
    else:  # 其他层级
        node_color = generate_light_color(parent_color)
        graph.node(node, style='solid', color=node_color,fontsize="14", shape='egg', fontname='WenQuanYi Micro Hei', label=node)

    # 连接节点
    if parent:
        graph.edge(parent, node,  penwidth='2.0', color=parent_color if level == 1 else node_color)

    # 递归构建子节点
    for child in structure.get(node, []):
        build_mind_map(graph, child, node, structure, level=level + 1,
                       parent_color=node_color if level == 1 else parent_color)
