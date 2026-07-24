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
        ref_text = "是啊,我也超想去云南的,听说云南不仅有古城、雪山、花海、梯田,还有超级多美食,我已经开始期待了。",          # 你的参考文本
        nfe_step = 12, # 16
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
    clear_folder(temp_audio_dir)

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
