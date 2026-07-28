import subprocess


def convert_video(src_path: str, dst_path: str, target_format: str):
    target_format = target_format.lower()

    if target_format == "gif":
        cmd = [
            "ffmpeg", "-y", "-i", src_path,
            "-vf", "fps=10,scale=480:-1:flags=lanczos",
            dst_path,
        ]
    elif target_format == "mp3":
        cmd = ["ffmpeg", "-y", "-i", src_path, "-vn", "-acodec", "libmp3lame", dst_path]
    else:
        cmd = ["ffmpeg", "-y", "-i", src_path, dst_path]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {result.stderr[-500:]}")
