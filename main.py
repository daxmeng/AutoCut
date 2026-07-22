import sys
from pathlib import Path
from tools.extract import (
    extract_audio_srt,
    burn_subtitle
)
from tools.audio import (
    make_clone_audio, 
    merge_video_audio
)

# 公共变量
REF_AUDIO = "temp/input/reference.wav"
ORI_VIDEO = "temp/input/demo.mp4"
TMP_AUDIO_PREFIX = "temp/audio_tmp/"
p = Path(ORI_VIDEO)
output_dir = str(p.parent).replace(
    "input",
    "output"
)
ORI_AUDIO = f"{output_dir}/{p.stem}_1_ori.wav"
OUTPUT_SRT = f"{output_dir}/{p.stem}_2.srt"
AUDIO_CLONE = f"{output_dir}/{p.stem}_3_clone.wav"
VIDEO_AUDIO = f"{output_dir}/{p.stem}_4_audio.mp4"
VIDEO_AUDIO_SRT = f"{output_dir}/{p.stem}_5_audio_srt.mp4"

"""
# 1. 提取音频和字幕 -> 优化字幕
extract_audio_srt(ORI_VIDEO, ORI_AUDIO, OUTPUT_SRT)
"""
# 2. 声音克隆和时间匹配
make_clone_audio(
    temp_audio_dir=AUDIO_TMP_PREFIX,
    original_video=ORI_VIDEO,
    output_audio=AUDIO_CLONE,
    ref_srt=OUTPUT_SRT,
    ref_audio=REF_AUDIO
)

sys.exit(0)

# 3. 把克隆的声音和原视频合并
merge_video_audio(
    ORI_VIDEO,
    AUDIO_CLONE,
    VIDEO_AUDIO
)

# 4. 字幕转换 & 烧录字幕
burn_subtitle(
    VIDEO_AUDIO,
    OUTPUT_SRT,
    VIDEO_AUDIO_SRT
)
