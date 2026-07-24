import subprocess
from pathlib import Path
import re
from typing import List, Tuple
from funasr import AutoModel

from tools.common import (
    get_media_duration,
    delete_file,
    clear_folder,
    get_lists_by_txt,
)

def speed_video(in_path, out_path, speed=1.3):
    cmd = [
        "ffmpeg",
        "-y",
        "-loglevel", "warning",
        "-i", in_path,
        "-fps_mode", "vfr",
        "-vf", f"setpts=PTS/{speed}",
        "-filter:a", f"atempo={speed}",
        "-c:v", "libx264", 
        "-preset", "medium", 
        "-crf", "18",
        out_path
    ]
    subprocess.run(cmd, check=True)

def img_audio_2_video(txt_file, img, audio_path, output_path):
    subs = get_lists_by_txt(txt_file)
    for index,item in enumerate(subs):
        cmd = [
            "ffmpeg",
            "-loop", "1",
            "-framerate", "1",
            "-i", img,
            "-i", f"{audio_path}audio_{index + 1}.wav",
            "-c:v", "libx264",
            "-c:a", "aac",
            "-pix_fmt", "yuv420p",
            "-shortest",
            "-y",  # 自动覆盖
            f"{output_path}video_{index + 1}.mp4"
        ]
        subprocess.run(cmd, capture_output=True)

def get_silence_segments(video_path: str, silence_duration: float = 1.0, silence_db: str = "-50dB") -> List[Tuple[float, float]]:
    """
    检测视频中的静音片段
    :param video_path: 原视频路径
    :param silence_duration: 判定为有效静音的最小时长(秒)
    :param silence_db: 静音音量阈值
    :return: 静音区间列表 [(start, end), ...]
    """
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel", "info",
        "-i", video_path,
        "-filter:a", f"silencedetect=n={silence_db}:d={silence_duration}",
        "-f", "null", "-"
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    output = result.stderr

    silence_starts = []
    silence_ends = []

    # 正则匹配静音开始/结束时间
    start_pat = re.compile(r"silence_start: (\d+\.?\d*)")
    end_pat = re.compile(r"silence_end: (\d+\.?\d*)")

    for line in output.splitlines():
        s_start = start_pat.search(line)
        s_end = end_pat.search(line)
        if s_start:
            silence_starts.append(float(s_start.group(1)))
        if s_end:
            silence_ends.append(float(s_end.group(1)))

    # 配对静音区间
    segments = []
    for s, e in zip(silence_starts, silence_ends):
        if e - s >= silence_duration:
            segments.append((s, e))
    return segments

def cut_silence_for_video(video_in: str, video_out: str, min_silence: float = 1.0):
    """
    删除大于指定时长的静音片段，拼接剩余视频
    :param video_in: 原视频
    :param video_out: 输出视频
    :param min_silence: 静音超过该秒数则删除
    """
    # 1. 获取所有静音区间
    silence_segs = get_silence_segments(video_in, min_silence)
    if not silence_segs:
        print("未检测到大于 1 秒的静音，直接复制原视频")
        cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", video_in, "-c", "copy", video_out]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return

    # 2. 构造需要保留的非静音片段
    keep_segs: List[Tuple[float, float]] = []
    prev = 0.0
    for s, e in silence_segs:
        if s > prev:
            keep_segs.append((prev, s))
        prev = e

    # 最后一段：视频末尾到结尾
    # 先获取视频总时长
    dur_cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", video_in
    ]
    total_dur = float(subprocess.run(dur_cmd, capture_output=True, text=True).stdout.strip())
    if prev < total_dur:
        keep_segs.append((prev, total_dur))

    if not keep_segs:
        print("无有效画面保留")
        return

    # 3. 生成 ffmpeg concat 切割命令
    filter_parts = []
    for idx, (start, end) in enumerate(keep_segs):
        filter_parts.append(
            f"[0:v]trim=start={start}:end={end},setpts=PTS-STARTPTS[v{idx}];"
            f"[0:a]atrim=start={start}:end={end},asetpts=PTS-STARTPTS[a{idx}]"
        )

    v_join = "".join(f"[v{i}]" for i in range(len(keep_segs))) + f"concat=n={len(keep_segs)}:v=1:a=0[outv]"
    a_join = "".join(f"[a{i}]" for i in range(len(keep_segs))) + f"concat=n={len(keep_segs)}:v=0:a=1[outa]"

    full_filter = ";".join(filter_parts) + ";" + v_join + ";" + a_join

    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel", "warning",
        "-i", video_in,
        "-filter_complex", full_filter,
        "-map", "[outv]",
        "-map", "[outa]",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "18",
        "-c:a", "aac",
        "-ac", "2",
        "-ar", "44100",
        "-b:a", "128k",
        video_out
    ]

    print(f"开始裁剪，共保留 {len(keep_segs)} 个片段...")
    subprocess.run(cmd, check=True)
    print(f"完成：{video_out}")

def normalize_video(video_in, video_out):
    """统一视频参数"""
    cmd = [
        "ffmpeg",
        "-i", video_in,
        "-vf", "scale=1920:1080,fps=30",
        "-c:v", "libx264",
        "-c:a", "aac",       # 统一音频编码为aac
        "-ar", "44100",      # 统一音频采样率
        "-ac", "2",          # 统一双声道
        "-y",  # 覆盖已有文件
        video_out
    ]
    subprocess.run(cmd, check=True)
    
def concat_video(video_path_arr, merged_video: str):
    concat_temp_dir = "temp/output/concat/"
    video_index_txt = f"{concat_temp_dir}video_index.txt"
    with open(video_index_txt, "w", encoding="utf-8") as f:
        for index,path in enumerate(video_path_arr):
            video_out = f"{concat_temp_dir}{index + 1}.mp4"
            normalize_video(path, video_out)
            f.write(f"file '{index + 1}.mp4'\n")
    cmd = [
        "ffmpeg",
        "-f", "concat",
        "-safe", "0",
        "-i", video_index_txt,
        "-c:v", "copy",   # 视频流拷贝
        "-c:a", "copy",   # 音频流拷贝
        merged_video
    ]

    # 执行命令
    subprocess.run(cmd, check=True)
    clear_folder(concat_temp_dir)
