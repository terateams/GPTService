from datetime import datetime, timedelta
import srt
import re
import xml.etree.ElementTree as ET

def merge_overlapping_subtitles(subtitles_src):
    """
    合并重叠的字幕段落。

    Args:
        subtitles_src (str): 字幕内容。

    Returns:
        str: 合并后的字幕内容。
    """
    
    subtitles = [s for s in srt.parse(subtitles_src)]
    merged_subtitles = []
    buffer_sub = subtitles[0]

    for sub in subtitles[1:]:
        if sub.start != buffer_sub.end:
            # 合并字幕
            buffer_sub.content += sub.content
            # buffer_sub.end = max(buffer_sub.end, sub.end)
        else:
            # 保存并开始新的字幕段
            merged_subtitles.append(buffer_sub)
            buffer_sub = sub

    # 添加最后一个字幕段
    merged_subtitles.append(buffer_sub)
    return srt.compose(merged_subtitles)


def ttml_to_srt(ttml_content):
    """
    将TTML格式的字幕内容转换为SRT格式的字幕内容。

    Args:
        ttml_content (str): TTML格式的字幕内容。

    Returns:
        str: SRT格式的字幕内容。
    """
    
    # 解析 TTML 内容
    root = ET.fromstring(ttml_content)

    # 提取 <p> 元素，这些是字幕段
    subtitles = root.findall('.//{http://www.w3.org/ns/ttml}p')

    # SRT 格式的结果
    srt_result = ""

    for index, subtitle in enumerate(subtitles):
        # 提取开始和结束时间
        begin = subtitle.get('begin')
        end = subtitle.get('end')

        # 转换时间格式为 SRT 格式（HH:MM:SS,MMM）
        begin_srt = re.sub(r'(\d{2}):(\d{2}):(\d{2}).(\d{3})', r'\1:\2:\3,\4', begin)
        end_srt = re.sub(r'(\d{2}):(\d{2}):(\d{2}).(\d{3})', r'\1:\2:\3,\4', end)

        # 提取字幕文本
        text = ''.join(subtitle.itertext())

        # 组装 SRT 字幕段
        srt_result += f"{index + 1}\n{begin_srt} --> {end_srt}\n{text}\n\n"

    return srt_result


# 函数：转换 XML 字幕到 SRT 格式
def xml_to_srt(xml_content):
    """
    将XML格式的字幕转换为SRT格式。

    参数:
        xml_content (str): 字幕的XML内容。

    返回:
        str: 格式化为SRT的字幕。
    """
    
    root = ET.fromstring(xml_content)
    subtitles = []

    for p in root.findall('.//p'):
        # 获取开始时间和持续时间
        start_time = int(p.get('t', 0))
        duration = int(p.get('d', 0))
        end_time = start_time + duration

        # 创建 SRT 字幕段
        subtitle_segment = srt.Subtitle(
            index=len(subtitles) + 1,
            start=timedelta(milliseconds=start_time),
            end=timedelta(milliseconds=end_time),
            content=''.join(s.text for s in p.findall('.//s') if s.text)
        )
        subtitles.append(subtitle_segment)

    return srt.compose(subtitles)


def merge_subtitles_by_punctuation_srt(subtitles):
    merged_subtitles = []
    current_text = ""
    current_start = None

    for sub in subtitles:
        if not current_start:
            # 初始化开始时间
            current_start = sub.start

        current_text += sub.content + " "

        # 检查是否以标点结束
        if current_text.strip().endswith(('.', '?', '!', '。', '？', '！')):
            merged_subtitle = srt.Subtitle(
                index=len(merged_subtitles) + 1,
                start=current_start,
                end=sub.end,
                content=current_text.strip()
            )
            merged_subtitles.append(merged_subtitle)
            current_text = ""
            current_start = None

    # 添加最后一段字幕（如果有的话）
    if current_text:
        merged_subtitle = srt.Subtitle(
            index=len(merged_subtitles) + 1,
            start=current_start,
            end=sub.end,
            content=current_text.strip()
        )
        merged_subtitles.append(merged_subtitle)

    return merged_subtitles



