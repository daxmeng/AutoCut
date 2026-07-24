import sys
from pathlib import Path
from tools.video import (
    speed_video
)
from tools.audio import (
    clone_merge_audio_by_srt
)
from tools.common import (
    add_text_for_video,
    merge_audio_2_video,
    extract_audio_srt,
    burn_subtitle_2_video,
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
VIDEO_SPEED = f"{output_dir}/{p.stem}_6_speed.mp4"
VIDEO_FINAL = f"{output_dir}/final_merged_normal.mp4"
VIDEO_CTA = f"{output_dir}/{p.stem}_7_cta.mp4"

if len(sys.argv) > 1:
    flow_num = int(sys.argv[1])
else:
    flow_num = 0

# 1. 提取音频和字幕 -> 优化字幕
if flow_num == 1:
    extract_audio_srt(ORI_VIDEO, ORI_AUDIO, OUTPUT_SRT)
elif flow_num == 2:
    # 2. 声音克隆和时间匹配
    clone_merge_audio_by_srt(
        temp_audio_dir=TMP_AUDIO_PREFIX,
        original_video=ORI_VIDEO,
        output_audio=AUDIO_CLONE,
        ref_srt=OUTPUT_SRT,
        ref_audio=REF_AUDIO
    )

    # 3. 把克隆的声音和原视频合并
    merge_audio_2_video(
        ORI_VIDEO,
        AUDIO_CLONE,
        VIDEO_AUDIO
    )

    # 4. 字幕转换 & 烧录字幕
    burn_subtitle_2_video(
        VIDEO_AUDIO,
        OUTPUT_SRT,
        VIDEO_AUDIO_SRT
    )
elif flow_num == 3:
    # 5. 加速
    speed_video(VIDEO_FINAL, VIDEO_SPEED)
else:
    add_text_for_video(VIDEO_SPEED, VIDEO_CTA)
