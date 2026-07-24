import sys
from pathlib import Path

from tools.common import (
    generate_precise_srt,
    batch_burn_subtitle,
)
from tools.video import (
    img_audio_2_video,
)
from tools.audio import (
    clone_audio_by_txt,
)

REF_AUDIO = "temp/input/reference.wav"
ORI_TXT = "temp/input/c.txt"
ORI_IMG = "temp/input/c.png"
p = Path(ORI_TXT)
output_dir = str(p.parent).replace(
    "input",
    "output"
)
OUT_SINGLE_PREFIX = f"{output_dir}/single/"

# 1. 克隆单个声音
clone_audio_by_txt(
    ORI_TXT,
    OUT_SINGLE_PREFIX,
    REF_AUDIO
)

# 2. 根据声音和txt生成精确字幕
generate_precise_srt(
    ORI_TXT,
    OUT_SINGLE_PREFIX,
    OUT_SINGLE_PREFIX
)

# 3. 根据图片和声音，形成视频
img_audio_2_video(
    ORI_TXT,
    ORI_IMG,
    OUT_SINGLE_PREFIX,
    OUT_SINGLE_PREFIX,
)

# 4. 烧录字幕
batch_burn_subtitle(ORI_TXT, OUT_SINGLE_PREFIX)
