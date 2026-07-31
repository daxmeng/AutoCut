import os
import sys
import subprocess
from pathlib import Path
from pydub import AudioSegment
from f5_tts.api import F5TTS

from tools.common import (
    get_media_duration,
    clear_folder,
    load_srt,
    get_lists_by_txt
)

def _f5tts(
    f5_model,
    text,
    audio_file,
    ref_audio
):
    # 调用全局已加载好的模型
    wav, sr, spec = f5_model.infer(
        ref_file = ref_audio,  # 你的参考音频路径
        # ref_text = "是啊，我也超想去云南的，听说云南不仅有古城、雪山、花海、梯田，还有超级多美食，我已经开始期待了。",          # 你的参考文本
        ref_text = "在空闲的时候，我最喜欢做的事情就是阅读啦，我会看各种类型的书，希望自己变得更博学！",          # 你的参考文本
        nfe_step = 12, # 12 16
        gen_text = text,
        file_wave = audio_file,
        remove_silence = True,
        show_info = lambda *a, **k: None
    )

def _speed_up(
    input,
    output,
    speed
):
    cmd=[
        "ffmpeg",
        "-y",
        "-loglevel", "warning",
        "-i",
        input,
        "-filter:a",
        f"atempo={speed}",
        output
    ]

    subprocess.run(
        cmd,
        check=True
    )

def _add_silence(
    input,
    output,
    target
):
    audio=AudioSegment.from_file(
        input
    )
    current=len(audio)/1000
    need=target-current

    if need>0:
        silence=AudioSegment.silent(
            duration=need*1000
        )
        audio += silence

    audio.export(
        output,
        format="wav"
    )

def _fit_audio(
    input,
    target,
    output
):

    duration=get_media_duration(
        input
    )

    if duration > target:
        speed=duration/target
        _speed_up(
            input,
            output,
            speed
        )
    else:
        _add_silence(
            input,
            output,
            target
        )

def _merge_audio_by_timeline(
    items,
    total,
    output
):
    timeline=AudioSegment.silent(
        duration=total*1000
    )

    for item in items:
        audio=AudioSegment.from_file(
            item["audio"]
        )

        timeline=timeline.overlay(
            audio,
            position=
            int(item["start"]*1000)
        )
    timeline.export(
        output,
        format="wav"
    )

def clone_merge_audio_by_srt(
    original_video,
    temp_audio_dir,
    output_audio,
    ref_srt = "",
    ref_audio = "",
):
    processed = []
    f5_model = F5TTS(
        device = "mps"
    )
    # 1. 声音克隆和时间匹配
    subs = load_srt(
        ref_srt
    )
    for index,item in enumerate(subs):
        raw=f"{temp_audio_dir}ori_{index + 1}.wav"
        fixed=f"{temp_audio_dir}fit_{index + 1}.wav"

        # F5声音克隆
        _f5tts(
            f5_model,
            item["text"],
            raw,
            ref_audio
        )
        # 时间匹配
        _fit_audio(
            raw,
            item["end"]-item["start"],
            fixed
        )
        item["audio"] = fixed
        processed.append(item)
    # 2. 获取视频长度
    total = get_media_duration(original_video)

    # 3. 生成完整声音
    _merge_audio_by_timeline(
        processed,
        total,
        output_audio
    )
    # clear_folder(temp_audio_dir)

def clone_audio_by_srt_index(
    temp_audio_dir,
    ref_srt = "",
    ref_audio = "",
    srt_index = 1,
):
    processed = []
    f5_model = F5TTS(
        device = "mps"
    )
    # 1. 声音克隆和时间匹配
    subs = load_srt(
        ref_srt
    )
    for index,item in enumerate(subs):
        if index + 1 == srt_index:
            raw=f"{temp_audio_dir}ori_{index + 1}.wav"
            fixed=f"{temp_audio_dir}fit_{index + 1}.wav"

            # F5声音克隆
            _f5tts(
                f5_model,
                item["text"],
                raw,
                ref_audio
            )
            # 时间匹配
            _fit_audio(
                raw,
                item["end"]-item["start"],
                fixed
            )
            break


def clone_audio_by_txt(
    txt_file,
    temp_audio_dir,
    ref_audio = "",
):
    f5_model = F5TTS(
        device = "mps"
    )

    subs = get_lists_by_txt(txt_file)

    for index,item in enumerate(subs):
        raw=f"{temp_audio_dir}audio_{index + 1}.wav"
        # F5声音克隆
        _f5tts(
            f5_model,
            item,
            raw,
            ref_audio
        )

def merge_audio_by_srt(
    original_video,
    temp_audio_dir,
    output_audio,
    ref_srt = "",
):
    processed = []
    # 1. 声音克隆和时间匹配
    subs = load_srt(
        ref_srt
    )
    for index,item in enumerate(subs):
        fixed=f"{temp_audio_dir}fit_{index + 1}.wav"
        item["audio"] = fixed
        processed.append(item)
    # 2. 获取视频长度
    total = get_media_duration(original_video)

    # 3. 生成完整声音
    _merge_audio_by_timeline(
        processed,
        total,
        output_audio
    )

# FFmpeg参数：强制 44100Hz 16bit 单声道 pcm_s16le
def convert_single_mp3(input, output, flow=2):
    try:
        output_temp = output.replace(".", "_temp.")
        cmd1 = [
            "ffmpeg",
            "-y",                # 覆盖输出文件，不弹窗询问
            "-loglevel", "warning",
            "-i", input,
            "-acodec", "pcm_s16le",
            "-ar", "44100",      # 采样率
            "-ac", "1",          # 1=单声道
            output_temp
        ]
        cmd2 = [
            "ffmpeg",
            "-y",                # 覆盖输出，无需确认
            "-loglevel", "warning",
            "-fflags", "+bitexact",    # 关键：禁止写入encoder标记
            "-i", input,
            "-acodec", "adpcm_ima_wav",  # ADPCM编码
            "-ar", "16000",              # 采样率16000Hz
            "-ac", "1",                  # 单声道
            "-map_metadata", "-1",   # 删除所有元数据
            output_temp
        ]
        if flow == 2:
            cmd = cmd2
        else:
            cmd = cmd1
        subprocess.run(cmd, check=True, capture_output=True)
        subprocess.run(f"sox {output_temp} {output}", check=True, capture_output=True)
        print(f"✅ 完成：{os.path.basename(input)}")
    except subprocess.CalledProcessError as e:
        print(f"❌ 失败 {input}: {e.stderr.decode()}")

