#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Dynamic PDF extractor – comments in English

import os, re, csv, logging, json, sys
from types import ModuleType
from pypdf import PdfReader
from pdf2image import convert_from_path
import pytesseract
from PIL import Image

# ───────────────────────────────────────────────
#  Dynamic configuration
# ───────────────────────────────────────────────
CONFIG_PATH	= os.path.join(os.path.dirname(__file__), "config.json")

def _load_default_config():
	try:
		with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
			return json.load(fh)
	except FileNotFoundError:
		return []

FIELDS	= []	# list of field dicts
HEADERS	= []	# cached list of field names

def set_config(cfg):
	"""Replace in-memory field rules at runtime."""
	global FIELDS, HEADERS
	FIELDS	= cfg or []
	HEADERS	= [f["name"] for f in FIELDS]

# Load initial config
set_config(_load_default_config())

# Allow extractor.CONFIG = cfg sugar
class _ConfigModule(ModuleType):
	@property
	def CONFIG(self):
		return FIELDS
	@CONFIG.setter
	def CONFIG(self, value):
		set_config(value)

sys.modules[__name__].__class__ = _ConfigModule

# ───────────────────────────────────────────────
#  Environment-specific tools
# ───────────────────────────────────────────────
PDF_FOLDER	= "test/pdfs"
CSV_OUTPUT	= "test/adherents.csv"

if os.name == "nt":								# Windows
	POPPLER_PATH	= r"C:\poppler\Library\bin"
	TESSERACT_CMD	= r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
else:											# Linux / cloud
	POPPLER_PATH	= None						# poppler in PATH
	TESSERACT_CMD	= "tesseract"				# tesseract in PATH

pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

# ───────────────────────────────────────────────
#  PDF helpers
# ───────────────────────────────────────────────
def extract_with_acroform(pdf_path):
	try:
		reader	= PdfReader(pdf_path)
		form	= reader.get_fields()
		if not form:
			return None
		return {k.lower(): str(v.get('/V', '')) for k, v in form.items()}
	except Exception as e:
		logging.debug(f"AcroForm extraction failed on {pdf_path}: {e}")
		return None

def pdf_to_text(pdf_path):
	kwargs = {}
	if POPPLER_PATH:
		kwargs["poppler_path"] = POPPLER_PATH
	images = convert_from_path(pdf_path, dpi=300, **kwargs)
	return "\n".join(pytesseract.image_to_string(img, lang="fra") for img in images)

# ───────────────────────────────────────────────
#  OCR parsing
# ───────────────────────────────────────────────
def parse_text(text):
	"""Extract configured fields from raw OCR text."""
	text = re.sub(r"[\u00A0\u2007\u202F]", " ", text)
	text = re.sub(r"[ \t]{2,}", " ", text)
	text = re.sub(r"\s+\n\s+", "\n", text)

	data = {}
	for field in FIELDS:
		name	= field["name"]
		pattern	= field.get("pattern") or rf"{re.escape(name)}\s*:\s*(.+)"
		ftype	= field.get("type", "text")

		m = re.search(pattern, text, re.IGNORECASE | re.UNICODE | re.DOTALL)

		if ftype == "checkbox":
			checked		= bool(m)
			data[name]	= field.get("checked_value", "1") if checked else field.get("unchecked_value", "0")
		else:
			value = m.group(1).strip() if m else ""
			if ftype == "number":
				value = re.sub(r"\D", "", value)
			data[name] = value

	return data

# ───────────────────────────────────────────────
#  Orchestration
# ───────────────────────────────────────────────
def extract_pdf(pdf_path):
	"""Return a dict of extracted values for one PDF."""
	row = {h: "" for h in HEADERS}

	acro = extract_with_acroform(pdf_path)
	if acro:
		for field in FIELDS:
			key = field.get("acro_key", field["name"]).lower()
			if key in acro:
				row[field["name"]] = acro[key]
	else:
		text = pdf_to_text(pdf_path)
		row.update(parse_text(text))
	return row

def process_folder(folder=PDF_FOLDER, csv_out=CSV_OUTPUT):
	"""CLI helper: extract every PDF in *folder* to a single CSV."""
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

# ───────────────────────────────────────────────
#  Entrypoint
# ───────────────────────────────────────────────
if __name__ == "__main__":
	process_folder()
