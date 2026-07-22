# 自动剪辑视频

```Mermaid
flowchart TD
    A[视频.mp4] --> B[FFmpeg 提取音频]
    B --> C[并行处理]
    C --> D[Whisper VAD 检测<br/>识别静音时间段]
    C --> E[语音转字幕<br/>生成 SRT 字幕]
    D & E --> F[FFmpeg 裁剪]
    F --> G[自动剪辑视频]
```