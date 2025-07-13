#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, re, csv, logging, json
import sys
from pypdf import PdfReader
from pdf2image import convert_from_path
import pytesseract
from PIL import Image

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
PDF_FOLDER  = "test/pdfs"
CSV_OUTPUT  = "test/adherents.csv"

# Detect OS and set Poppler/Tesseract paths accordingly
if os.name == "nt":  # Windows
    POPPLER_PATH  = r"C:\poppler\Library\bin"
    TESSERACT_CMD = r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
else:  # Linux (e.g. Streamlit Cloud)
    POPPLER_PATH  = None  # Assume poppler is in PATH
    TESSERACT_CMD = "tesseract"  # Assume tesseract is in PATH

pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

# Load field extraction rules from JSON configuration
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
    FIELDS = json.load(fh)

HEADERS = [f["name"] for f in FIELDS]

# --------------------------------------------------------------------------- #
# PDF helpers
# --------------------------------------------------------------------------- #
def extract_with_acroform(pdf_path):
	try:
		reader = PdfReader(pdf_path)
		form = reader.get_fields()
		if not form:
			return None
		return {k.lower(): str(v.get('/V', '')) for k, v in form.items()}
	except Exception as e:
		logging.debug(f"AcroForm extraction failed on {pdf_path}: {e}")
		return None


def pdf_to_text(pdf_path):
    # Pass poppler_path only if set (Windows)
    kwargs = {}
    if POPPLER_PATH:
        kwargs["poppler_path"] = POPPLER_PATH
    images = convert_from_path(pdf_path, dpi=300, **kwargs)
    return "\n".join(pytesseract.image_to_string(img, lang="fra") for img in images)

# --------------------------------------------------------------------------- #
# OCR parsing
# --------------------------------------------------------------------------- #
def parse_text(text):
    """Extract required fields out of raw OCR text using JSON rules."""

    # Normalise exotic whitespaces
    text = re.sub(r"[\u00A0\u2007\u202F]", " ", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\s+\n\s+", "\n", text)

    data = {}

    for field in FIELDS:
        name = field["name"]
        pattern = field.get("pattern")
        ftype = field.get("type", "text")

        if not pattern:
            # generic pattern "Label: value" if no explicit regex provided
            pattern = rf"{re.escape(name)}\s*:\s*(.+)"

        m = re.search(pattern, text, re.IGNORECASE | re.UNICODE | re.DOTALL)

        if ftype == "checkbox":
            checked = bool(m)
            data[name] = field.get("checked_value", "1") if checked else field.get("unchecked_value", "0")
        else:
            value = m.group(1).strip() if m else ""
            if ftype == "number":
                value = re.sub(r"\D", "", value)
            data[name] = value

    return data

# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #
def extract_pdf(pdf_path):
    data = {h: "" for h in HEADERS}
    acro = extract_with_acroform(pdf_path)
    if acro:
        for field in FIELDS:
            key = field.get("acro_key", field["name"]).lower()
            if key in acro:
                data[field["name"]] = acro[key]
    else:
        text = pdf_to_text(pdf_path)
        data.update(parse_text(text))
    return data


def process_folder(folder, csv_out):
	logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
	pdfs = [f for f in os.listdir(folder) if f.lower().endswith(".pdf")]
	if not pdfs:
		logging.warning("No PDF files found in %s", folder)
		return

	with open(csv_out, "w", newline="", encoding="utf-8") as fh:
		writer = csv.DictWriter(fh, fieldnames=HEADERS)
		writer.writeheader()
		for pdf in pdfs:
			logging.info("Processing %s", pdf)
			row = extract_pdf(os.path.join(folder, pdf))
			writer.writerow(row)

# --------------------------------------------------------------------------- #
# Entrypoint
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
	process_folder(PDF_FOLDER, CSV_OUTPUT)
