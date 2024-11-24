from datetime import timedelta
from typing import List
import uuid
from pydub import AudioSegment
from openai import AzureOpenAI, AsyncAzureOpenAI
from pydub import AudioSegment
from common.utils import get_global_datadir
import azure.cognitiveservices.speech as speechsdk
from xml.etree import ElementTree
from multiprocessing import Pool
import srt
import os


azure_voices = [
    # en-US
    "en-US-AndrewMultilingualNeural",
    "en-US-AvaMultilingualNeural",
    "en-US-BrianMultilingualNeural",
    "en-US-EmmaMultilingualNeural",
    "en-US-JennyMultilingualNeural",
    # zh-CN
    "wuu-CN-XiaotongNeural",
    "wuu-CN-YunzheNeural",
    # "yue-CN-XiaoMinNeural",
    # "yue-CN-YunSongNeural",
    "zh-CN-YunxiNeural",
    "zh-CN-YunjianNeural",
    "zh-CN-YunyangNeural",
    "zh-CN-YunfengNeural",
    "zh-CN-YunhaoNeural",
    "zh-CN-YunxiaNeural",
    "zh-CN-YunyeNeural",
    "zh-CN-YunzeNeural",
    "zh-CN-XiaoyiNeural",
    "zh-CN-XiaochenNeural",
    "zh-CN-XiaohanNeural",
    "zh-CN-XiaoxiaoNeural",
    "zh-CN-XiaomengNeural",
    "zh-CN-XiaomoNeural",
    "zh-CN-XiaoqiuNeural",
    "zh-CN-XiaoruiNeural",
    "zh-CN-XiaoshuangNeural",
    "zh-CN-XiaoxuanNeural",
    "zh-CN-XiaoyanNeural",
    "zh-CN-XiaoyouNeural",
    "zh-CN-XiaozhenNeural",
    # "zh-CN-XiaochenMultilingualNeural",
    # "zh-CN-XiaorouNeural",
    # "zh-CN-XiaoxiaoDialectsNeural",
    # "zh-CN-YunjieNeural",
    # "zh-CN-YunyiMultilingualNeural",
    # "zh-CN-guangxi-YunqiNeural",
    # "zh-CN-henan-YundengNeural",
    "zh-CN-liaoning-XiaobeiNeural",
    # "zh-CN-liaoning-YunbiaoNeural",
    "zh-CN-shaanxi-XiaoniNeural",
    "zh-CN-shandong-YunxiangNeural",
    "zh-CN-sichuan-YunxiNeural",
    "zh-HK-HiuMaanNeural",
    "zh-HK-WanLungNeural",
    "zh-HK-HiuGaaiNeural",
    "zh-TW-HsiaoChenNeural",
    "zh-TW-YunJheNeural",
    "zh-TW-HsiaoYuNeural",
]


def is_ssml(text):
    try:
        # 尝试解析文本为 XML
        ElementTree.fromstring(text)
        # 如果没有抛出异常，那么这是有效的 XML，可能是 SSML
        # 这里可以添加更多的检查，例如检查根元素是否是 <speak>
        return True
    except ElementTree.ParseError:
        # 如果解析 XML 时抛出异常，那么这不是有效的 SSML
        return False


def create_silence_audio_segment(duration_milliseconds) -> AudioSegment:
    """
    生成指定时长的静音音频

    Args:
        duration_milliseconds (int): 静音音频的时长（毫秒）

    Returns:
        pydub.AudioSegment: 生成的静音音频段
    """
    silence = AudioSegment.silent(duration=duration_milliseconds)
    return silence


def generate_openai_speech_segment(
    text, voice: str = "onyx", speed=1.0
) -> AudioSegment:
    """
    生成 OpenAI 语音片段。

    参数:
    text (str): 要转换为语音的文本。
    voice (str): 语音，默认为 "onyx"。

    返回:
    AudioSegment: 生成的语音片段。
    """
    client = AzureOpenAI(
        api_key=os.getenv("TTS_AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("TTS_AZURE_OPENAI_API_VERSION"),
        azure_endpoint=os.getenv("TTS_AZURE_OPENAI_ENDPOINT"),
    )
    with client.audio.speech.with_streaming_response.create(
        model="tts-1", voice=voice, input=text, speed=speed
    ) as response:
        # 保存到临时文件并读取为 AudioSegment
        filename = os.path.join(
            get_global_datadir("temp_speech"), uuid.uuid4().hex + ".mp3"
        )
        response.stream_to_file(filename)
    return AudioSegment.from_mp3(filename)


async def agenerate_openai_speech_file(text, voice: str = "onyx", speed=1.0) -> str:
    """
    生成 OpenAI 语音片段。

    参数:
    text (str): 要转换为语音的文本。
    voice (str): 语音，默认为 "onyx"。

    返回:
    str: 生成的语音文件。
    """
    client = AsyncAzureOpenAI(
        api_key=os.getenv("TTS_AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("TTS_AZURE_OPENAI_API_VERSION"),
        azure_endpoint=os.getenv("TTS_AZURE_OPENAI_ENDPOINT"),
    )
    filename = os.path.join(
        get_global_datadir("temp_speech"), uuid.uuid4().hex + ".mp3"
    )
    with await client.audio.speech.with_streaming_response.create(
        model="tts-1", voice=voice, input=text, speed=speed
    ) as response:
        response.stream_to_file(filename)
    return filename


async def agenerate_openai_speech_segment(
    text, voice: str = "onyx", speed=1.0
) -> AudioSegment:
    """
    生成 OpenAI 语音片段。

    参数:
    text (str): 要转换为语音的文本。
    voice (str): 语音，默认为 "onyx"。

    返回:
    AudioSegment: 生成的语音片段。
    """
    filename = await agenerate_openai_speech_file(text, voice, speed)
    return AudioSegment.from_mp3(filename)


def merge_speech_segments(segments) -> AudioSegment:
    """
    将一系列语音片段合并为一个音频片段。

    参数:
        segments (list): 表示语音片段的AudioSegment对象列表。

    Returns:
        AudioSegment: The combined audio segment.
    """
    combined = AudioSegment.empty()
    for segment in segments:
        combined += segment
    return combined


def generate_azure_speech_segment(
    text,
    language: str = "zh-CN",
    voice: str = "zh-CN-YunyangNeural",
    target_file: str = None,
) -> AudioSegment | None:
    """
    生成 Azure 语音片段。

    参数:
    text (str): 要转换为语音的文本。
    voice (str): 语音，默认为 "zh-CN-YunyangNeural"。

    返回:
    AudioSegment: 生成的语音片段。
    """
    speech_key = os.environ.get("AZURE_SPEECH_KEY")
    service_region = os.environ.get("AZURE_SPEECH_REGION")
    endpoint = os.environ.get("AZURE_SPEECH_ENDPOINT")
    speech_config = speechsdk.SpeechConfig(
        subscription=speech_key,
        region=service_region,
        speech_recognition_language=language,
    )
    speech_config.speech_synthesis_voice_name = voice
    speech_config.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Audio48Khz192KBitRateMonoMp3
    )

    file_name = os.path.join(
        get_global_datadir("temp_speech"), uuid.uuid4().hex + ".mp3"
    )

    if target_file:
        file_name = target_file

    file_config = speechsdk.audio.AudioOutputConfig(filename=file_name)
    speech_synthesizer = speechsdk.SpeechSynthesizer(
        speech_config=speech_config, audio_config=file_config
    )
    if is_ssml(text):
        result = speech_synthesizer.speak_ssml_async(text).get()
    else:
        result = speech_synthesizer.speak_text_async(text).get()

    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        print(
            "Speech synthesized for text [{}], and the audio was saved to [{}]".format(
                text, file_name
            )
        )
        return AudioSegment.from_mp3(file_name)
    elif result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = result.cancellation_details
        print("Speech synthesis canceled: {}".format(cancellation_details.reason))
        if cancellation_details.reason == speechsdk.CancellationReason.Error:
            print("Error details: {}".format(cancellation_details.error_details))
    return None


def generate_azure_speech_from_srt(
    srt_content, speech_generate_func, progress_callback: callable = None, mpool=None
) -> List[AudioSegment]:
    """
    从SRT文件内容生成OpenAI语音段列表。

    Args:
        srt_content (str): SRT文件内容。
        progress_callback (callable, optional): 进度回调函数。默认为None。

    Returns:
        List[AudioSegment]: 生成的语音段列表。
    """
    segments = []
    previous_end_time = timedelta(0)

    progress = 0
    data = [s for s in srt.parse(srt_content)]
    for subtitle in data:
        if not subtitle.content.strip():
            segments.append(
                create_silence_audio_segment(
                    (subtitle.end - subtitle.start).total_seconds() * 1000
                )
            )
            continue
        # 处理字幕间的空白时间
        silence_duration_ms = int(
            (subtitle.start - previous_end_time).total_seconds() * 1000
        )
        if silence_duration_ms > 0:
            segments.append(create_silence_audio_segment(silence_duration_ms))

        # 生成语音段
        if mpool:
            asyncResult = mpool.apply_async(
                speech_generate_func, args=(subtitle.content,)
            )
            segments.append(asyncResult)
        else:
            speech_segment = speech_generate_func(subtitle.content)
            segments.append(speech_segment)

        # 更新前一个字幕的结束时间
        previous_end_time = subtitle.end
        progress += round(1 / len(data), 1)
        if progress_callback:
            progress_callback(progress)

    return segments


def audio_segment_split(audio_segment_src: AudioSegment, split_second: int):
    """
    将音频片段分割成指定时长的小片段。

    Args:
        audio_segment_src (AudioSegment): 要分割的音频片段。
        split_second (int): 每个分割片段的时长，以秒为单位。

    Returns:
        list: 分割后的音频片段列表。
    """

    split_list = []
    duration = len(audio_segment_src)
    start_time = 0
    end_time = split_second * 1000

    while end_time <= duration:
        split_list.append(audio_segment_src[start_time:end_time])
        start_time = end_time
        end_time += split_second * 1000

    if start_time < duration:
        split_list.append(audio_segment_src[start_time:])

    return split_list


# _transcribe_prompts = {
# "srt": "Please pay attention to pauses between sentences, \
#         use punctuation, correctly divide the generated SRT subtitles into time periods, \
#             maintain indexing continuity, and preserve silence time.",
# "text": "Please note the pauses between sentences, and correct some common mistakes.",
# }

_transcribe_prompts = {
    "srt": "Note the use of punctuation between statements",
    "text": "Note the use of punctuation between statements",
}


def generate_openai_transcribe(
    filename: str, language: str = "en", format: str = "text"
):
    """
    使用OpenAI API生成音频文件的转录文本。

    参数：
    - filename：音频文件的路径。

    返回值：
    - transcript：生成的转录文本。

    """
    client = AzureOpenAI(
        api_key=os.getenv("WHISPER_AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("WHISPER_AZURE_OPENAI_API_VERSION"),
        azure_endpoint=os.getenv("WHISPER_AZURE_OPENAI_ENDPOINT"),
    )
    transcript = client.audio.transcriptions.create(
        model="whisper",
        language=language,
        prompt=_transcribe_prompts.get(format),
        response_format=format,
        file=open(filename, "rb"),
    )
    return transcript


async def agenerate_openai_transcribe(
    filename: str, language: str = "en", format: str = "text", prompt_text=None
):
    """
    使用OpenAI API生成音频的转录文本。

    参数：
    - filename：音频文件的路径。

    返回：
    - transcript：生成的转录文本。

    异步函数。
    """
    client = AsyncAzureOpenAI(
        api_key=os.getenv("WHISPER_AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("WHISPER_AZURE_OPENAI_API_VERSION"),
        azure_endpoint=os.getenv("WHISPER_AZURE_OPENAI_ENDPOINT"),
    )
    prompt = _transcribe_prompts.get(format)
    if prompt_text:
        prompt = f"{prompt}, {prompt_text}"
    transcript = await client.audio.transcriptions.create(
        model="whisper",
        language=language,
        prompt=prompt,
        response_format=format,
        file=open(filename, "rb"),
    )
    return transcript


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv("../../.env")
    result = generate_azure_speech_segment(
        "神经网络声音在公共预览版中提供。 公共预览版语音和风格只在美国东部、西欧和东南亚这三个服务区域提供。"
    )
    split_result = audio_segment_split(result, 10)  # Split every 10 seconds
    for segment in split_result:
        segment.export("demo.mp3", "mp3")
