import os
import subprocess

from pypdf import PdfReader
from docx import Document


def _soffice_convert(src_path: str, out_dir: str, target_format: str) -> str:
    cmd = ["soffice", "--headless", "--convert-to", target_format, "--outdir", out_dir, src_path]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if result.returncode != 0:
        raise RuntimeError(f"LibreOffice failed: {result.stderr[-500:]}")

    base = os.path.splitext(os.path.basename(src_path))[0]
    produced = os.path.join(out_dir, f"{base}.{target_format}")
    if not os.path.exists(produced):
        raise RuntimeError("LibreOffice did not produce the expected output file")
    return produced


def convert_document(src_path: str, dst_path: str, target_format: str):
    target_format = target_format.lower()
    src_ext = os.path.splitext(src_path)[1].lower().lstrip(".")
    out_dir = os.path.dirname(dst_path)

    if src_ext == "pdf" and target_format == "docx":
        from pdf2docx import Converter
        cv = Converter(src_path)
        cv.convert(dst_path)
        cv.close()
        return

    if src_ext == "pdf" and target_format == "txt":
        reader = PdfReader(src_path)
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        with open(dst_path, "w", encoding="utf-8") as f:
            f.write(text)
        return

    if src_ext == "docx" and target_format == "txt":
        doc = Document(src_path)
        text = "\n".join(p.text for p in doc.paragraphs)
        with open(dst_path, "w", encoding="utf-8") as f:
            f.write(text)
        return

    # Everything else (docx->pdf, odt->pdf/docx, txt->pdf/docx, pptx->pdf, xlsx->pdf, rtf->*)
    produced = _soffice_convert(src_path, out_dir, target_format)
    if os.path.abspath(produced) != os.path.abspath(dst_path):
        os.replace(produced, dst_path)
