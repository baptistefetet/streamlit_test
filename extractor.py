#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, re, csv, logging
from pypdf import PdfReader
from pdf2image import convert_from_path
import pytesseract
from PIL import Image

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
PDF_FOLDER  = "test/pdfs"
CSV_OUTPUT  = "test/adherents.csv"

POPPLER_PATH  = r"C:\poppler\Library\bin"
TESSERACT_CMD = r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

HEADERS = ["NOM", "PRÉNOM", "NOUVEAU", "TEL", "MAIL"]

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
	images = convert_from_path(pdf_path, dpi=300, poppler_path=POPPLER_PATH)
	return "\n".join(pytesseract.image_to_string(img, lang="fra") for img in images)

# --------------------------------------------------------------------------- #
# OCR parsing
# --------------------------------------------------------------------------- #
def parse_text(text):
	"""Extract required fields out of raw OCR text."""
	# Normalise exotic whitespaces
	text = re.sub(r"[\u00A0\u2007\u202F]", " ", text)
	text = re.sub(r"[ \t]{2,}", " ", text)
	text = re.sub(r"\s+\n\s+", "\n", text)

	data = {}

	def grab(label, pattern, post=lambda v: v):
		m = re.search(pattern, text, re.IGNORECASE | re.UNICODE | re.DOTALL)
		data[label] = post(m.group(1).strip()) if m else ""

	# Names
	grab("NOM",    r"Nom\s*:\s*([^\n]+?)(?:\s+Pr[ée]nom|$)")
	grab("PRÉNOM", r"Pr[ée]nom\s*:\s*([^\n]+)")

	# Checkbox Nouvel adhérent
	cb = r"[xX✓✔☑☒✗✘❌■]"
	pat_cb = rf"(?:{cb}\s*Nouvel\s+adh[ée]rent)|(?:Nouvel\s+adh[ée]rent[^\n]{{0,30}}{cb})"
	data["NOUVEAU"] = "N" if re.search(pat_cb, text, re.IGNORECASE) else "R"

	# Phone
	grab("TEL",
	     r"T[ée]l[ée]phone\s*:\s*([0-9 \.\-\(\)]{7,})",
	     lambda v: re.sub(r"\D", "", v))

	# E-mail
	grab("MAIL", r"[Ee]mail\s*:\s*([^\s\n]+)")

	return data

# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #
def extract_pdf(pdf_path):
	data = {h: "" for h in HEADERS}
	acro = extract_with_acroform(pdf_path)
	if acro:
		for h in HEADERS:
			if h.lower() in acro:
				data[h] = acro[h.lower()]
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
