import subprocess
from pathlib import Path
from funasr import AutoModel
import pysubs2
from pysubs2 import Color, SSAStyle
import re
import srt

# 提取音频
def _extract_audio(video, output):

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        video,
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        output
    ]

    subprocess.run(
        cmd,
        check=True
    )

# srt 相关
def _format_srt_time(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    msec = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{msec:03d}"

def _generate_srt(audio_path: str, out_srt: str, model: AutoModel):
    # 语音识别 + 时间戳
    res = model.generate(input=audio_path)
    if not res:
        print("未识别到语音内容！")
        return

    full_text = res[0]["text"]
    timestamps = res[0]["timestamp"]  # [[start_ms, end_ms], ...]

    # 先按句号、问号、感叹号、换行分割句子，超过 20 字符的再按逗号处截断
    MAX_CHARS = 20
    spans = _split_text(full_text, MAX_CHARS)

    # 如果没有分割出句子，直接整段
    if not spans and full_text.strip():
        content = full_text.strip()
        content_abs_start = full_text.find(content)
        spans = _split_into_lines(content, content_abs_start, MAX_CHARS)

    srt_lines = []
    idx = 1
    prev_end = 0.0
    for sentence, start_char, end_char in spans:
        if not timestamps:
            continue
        # 将字符位置映射到 timestamp 索引（有些标点无对应 timestamp）
        ts_len = len(timestamps)
        start_ts = min(start_char, ts_len - 1)
        end_ts = min(end_char, ts_len - 1)

        start_time = max(timestamps[start_ts][0] / 1000, prev_end)
        end_time = max(timestamps[end_ts][1] / 1000, start_time + 0.1)
        prev_end = end_time

        # SRT 格式：序号、时间轴、文本、空行
        srt_lines.append(f"{idx}")
        srt_lines.append(f"{_format_srt_time(start_time)} --> {_format_srt_time(end_time)}")
        srt_lines.append(sentence)
        srt_lines.append("")
        idx += 1

    # 写入 SRT 文件
    with open(out_srt, "w", encoding="utf-8") as f:
        f.write("\n".join(srt_lines))

def _split_text(full_text, max_chars):
    """按句号、问号、感叹号分割句子，超过 max_chars 的再递归截断。返回 [(text, start, end), ...]"""
    spans = []
    i = 0
    n = len(full_text)

    while i < n:
        # 跳过空白
        if full_text[i].strip() == '' and full_text[i] != '\n':
            i += 1
            continue

        # 找句子结束标点（。！？\n）
        j = i
        while j < n and full_text[j] not in '。！？\n':
            j += 1

        if j < n and full_text[j] in '。！？\n':
            content_end = j
            seg_end = j + 1
        else:
            content_end = n
            seg_end = n

        content = full_text[i:content_end].strip()
        if not content:
            i = seg_end
            continue

        # content 在 full_text 中的绝对起始位置
        content_abs_start = full_text.find(content, i)
        if content_abs_start < 0:
            content_abs_start = i

        spans.extend(_split_into_lines(content, content_abs_start, max_chars))
        i = seg_end

    return spans

def _split_into_lines(content, abs_start, max_chars):
    """将一段文本按 max_chars 截断，逗号处优先。返回 [(text, abs_start, abs_end), ...]
    每行末尾不保留分隔符（。！？，、；：）"""
    if len(content) <= max_chars:
        trimmed = content.rstrip('，、；：').strip()
        if not trimmed:
            return []
        start = content.find(trimmed)
        return [(trimmed, abs_start + start, abs_start + start + len(trimmed) - 1)]

    result = []
    remaining = content
    offset = 0  # remaining 在 content 中的偏移量

    while remaining:
        if len(remaining) <= max_chars:
            trimmed = remaining.rstrip('，、；：').strip()
            if trimmed:
                trim_start = remaining.find(trimmed)
                result.append((
                    trimmed,
                    abs_start + offset + trim_start,
                    abs_start + offset + trim_start + len(trimmed) - 1,
                ))
            break

        # 在 max_chars 范围内优先找逗号截断
        cut = -1
        for sep in '，、；：':
            p = remaining.rfind(sep, 0, max_chars)
            if p > cut:
                cut = p

        if cut > 0:
            line_raw = remaining[:cut]
            remaining = remaining[cut + 1:]
            consumed = cut + 1
        else:
            # 没有逗号时，扫描前 20 字找到最后的"好断点"再截断
            # 这些虚词/助词/介词在中文里天然是短语边界，在其后截断不会
            # 拆散词语
            break_chars = set('的着了是在有和就也都还到对把被从给让对'
                              '吧吗呢啊呀嘛啦哈去来上中下里出过起开')
            fallback = 0
            for k in range(max_chars - 1, 1, -1):
                if remaining[k - 1] in break_chars:
                    fallback = k
                    break
            if fallback == 0:
                fallback = max_chars
            line_raw = remaining[:fallback]
            remaining = remaining[fallback:]
            consumed = fallback

        line = line_raw.rstrip('，、；：').strip()
        if line:
            line_start_in_raw = line_raw.find(line)
            line_abs = abs_start + offset + line_start_in_raw
            result.append((line, line_abs, line_abs + len(line) - 1))

        offset += consumed

    return result

def _srt_to_ass(
        srt_file,
        ass_file
):
    subs = pysubs2.load(
        srt_file,
        encoding="utf-8"
    )
    # 字幕样式
    style = pysubs2.SSAStyle(
        fontname="PingFang SC",
        fontsize=20,
        primarycolor=Color(255, 255, 255, 0),   # 纯白色字体
        secondarycolor=Color(255, 255, 255, 0),
        outlinecolor=Color(0, 0, 0, 0),         # 黑色轮廓
        backcolor=Color(0, 0, 0, 0),            # 黑色背景
        borderstyle=4,              # 1 = 带背景的矩形框（关键）
        outline=0,                # 轮廓宽度（越大背景越厚实）
        shadow=0,                 # 阴影关闭，保持干净
        # 底部居中
        alignment=2,
        # 字幕距离底部
        marginv=23
    )

    subs.styles["Default"] = style

    for line in subs.events:
        line.text = r"{\xbord 3}" + line.text + r"{\xbord 3}"

    subs.save(
        ass_file
    )

def clear_folder(dir):
    folder = Path(dir)
    """清空指定文件夹，保留文件夹本身"""
    if not folder.exists() or not folder.is_dir():
        return

    # 遍历目录下所有内容
    for item in folder.iterdir():
        try:
            if item.is_file():
                item.unlink()        # 删除文件
            elif item.is_dir():
                # 递归删除子目录及内部所有内容
                import shutil
                shutil.rmtree(item)
        except Exception as e:
            print(f"删除失败: {item}, 错误: {e}")

def _delete_file(f_path):
    file_path = Path(f_path)
    # 先判断文件是否存在，避免报错
    if file_path.is_file():
        file_path.unlink()  # 删除文件
        
# 加载 srt 文件
def load_srt(path):

    with open(
        path,
        encoding="utf-8"
    ) as f:

        content=f.read()


    subs=list(
        srt.parse(content)
    )


    result=[]


    for item in subs:

        result.append(
            {
                "start":
                item.start.total_seconds(),

                "end":
                item.end.total_seconds(),

                "text":
                item.content
            }
        )


    return result

def burn_subtitle(
        video_in,
        srt_file,
        video_out
):
    ass_file = srt_file.replace(
        ".srt",
        ".ass"
    )
    _srt_to_ass(
        srt_file,
        ass_file
    )

    cmd=[
        "ffmpeg",
        "-y",
        "-i", video_in,
        "-vf", f"ass={ass_file}",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "18",
        "-c:a", "copy",
        video_out
    ]

    subprocess.run(
        cmd,
        check=True
    )
    _delete_file(ass_file)

def extract_audio_srt(original_video, original_audio, output_srt):
    # 初始化区域
    MODEL_NAME = "paraformer-zh"
    model = AutoModel(
        model=MODEL_NAME,
        vad_model="fsmn-vad",
        punc_model="ct-punc",
        spk_model="cam++"
    )
    _extract_audio(original_video, original_audio)
    _generate_srt(original_audio, output_srt, model=model)

def get_duration_ffprobe(video_path):
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        video_path
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return float(result.stdout.decode().strip())
