from pydub import AudioSegment


def convert_audio(src_path: str, dst_path: str, target_format: str):
    audio = AudioSegment.from_file(src_path)
    audio.export(dst_path, format=target_format.lower())
