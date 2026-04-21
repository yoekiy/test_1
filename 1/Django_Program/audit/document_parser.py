import os
from PIL import Image
import pytesseract
from pdf2image import convert_from_path

pytesseract.pytesseract.tesseract_cmd = r"F:\bishe\Tesseract-OCR\tesseract.exe"

def ocr_image(img):
    return pytesseract.image_to_string(img, lang="chi_sim")

def parse_document(path):
    ext = os.path.splitext(path)[1].lower()

    # 图片文件
    if ext in [".jpg", ".png", ".jpeg"]:
        img = Image.open(path)
        return ocr_image(img)

    # 扫描 PDF
    if ext == ".pdf":
        text = ""
        images = convert_from_path(path, dpi=300)
        for img in images:
            text += ocr_image(img)
        return text

    # 文本兜底
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except:
        return ""
