from PIL import Image


def convert_image(src_path: str, dst_path: str, target_format: str):
    img = Image.open(src_path)
    fmt = target_format.upper()

    if fmt in ("JPG", "JPEG"):
        fmt = "JPEG"
        img = img.convert("RGB")
    elif fmt == "PDF":
        img = img.convert("RGB")
    elif fmt == "BMP" and img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    img.save(dst_path, fmt)
