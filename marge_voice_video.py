import subprocess
from pathlib import Path
import shutil

def merge_audio_video(video_path: str, audio_path: str, output_path: str = None) -> str:
    """合并音视频文件，支持中文路径，自动检测 ffmpeg"""
    video_file = Path(video_path).resolve()
    audio_file = Path(audio_path).resolve()

    if not video_file.exists():
        raise FileNotFoundError(f"视频文件不存在: {video_file}")
    if not audio_file.exists():
        raise FileNotFoundError(f"音频文件不存在: {audio_file}")

    output_file = Path(output_path) if output_path else video_file.parent / "merged_output.mp4"

    # 自动检测 ffmpeg 路径
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path is None:
        raise EnvironmentError("未找到 ffmpeg，请安装并添加到系统 PATH")

    cmd = [
        ffmpeg_path,
        '-y',
        '-i', str(video_file),
        '-i', str(audio_file),
        '-c:v', 'copy',
        '-c:a', 'aac',
        str(output_file)
    ]

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"FFmpeg 执行失败: {e}")

    return str(output_file)

if __name__ == "__main__":
    base_dir = Path(__file__).parent
    bv_dir = base_dir / "BV1ieNXzBEZC"

    # 修正视频和音频文件名
    video_file = bv_dir / "video.mp4"
    audio_file = bv_dir / "audio.mp4"

    print(f"视频文件路径: {video_file}\n音频文件路径: {audio_file}")

    if not video_file.exists() or not audio_file.exists():
        raise FileNotFoundError("视频或音频文件不存在，请检查路径和文件名")

    output_file = bv_dir / "merged_output.mp4"
    merged = merge_audio_video(str(video_file), str(audio_file), str(output_file))

    print(f"✅ 合并完成，输出文件: {merged}")
