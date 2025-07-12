#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import csv
import logging
from pypdf import PdfReader
from pdf2image import convert_from_path
import pytesseract
from PIL import Image

# Configuration ---------------------------------------------------------------
PDF_FOLDER = "sample_docs"          # dossier contenant les formulaires
CSV_OUTPUT = "adherents.csv" # fichier de sortie
# Chemin Tesseract pour Windows (modifiez si besoin)
TESSERACT_CMD = r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

HEADERS = [
	"Nom","Prenom","DateNaissance","Adresse","CodePostal","Ville",
	"Telephone","Email","StatutAdhesion","Categorie","TypeAdhesion",
	"BadgeCaution","CleCaution","MontantLicence","MontantCotisation",
	"Total","DateInscription","NomResponsableLegal","TelResponsableLegal",
	"EmailResponsableLegal","AutresRemarques","SourcePDF"
]

# -----------------------------------------------------------------------------	
def extract_with_acroform(pdf_path):
	"""Try to read AcroForm fields directly."""
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
	"""Convert pages to images then run OCR."""
	images = convert_from_path(pdf_path, dpi=300)
	return "\n".join(pytesseract.image_to_string(img, lang="fra") for img in images)

def parse_text(text):
	"""Extract key/value pairs from plain text using regex."""
	data = {}
	def grab(label, pattern):
		m = re.search(pattern, text, re.IGNORECASE)
		data[label] = m.group(1).strip() if m else ""

	grab("Nom", r"Nom\s*:\s*([^\n]+)")
	grab("Prenom", r"Pr[ée]nom\s*:\s*([^\n]+)")
	grab("DateNaissance", r"Date\s+de\s+naissance\s*:\s*([^\n]+)")
	grab("Adresse", r"Adresse\s*:\s*([^\n]+)")
	grab("CodePostal", r"Code\s*Postal\s*:\s*([0-9]{4,5})")
	grab("Ville", r"Ville\s*:\s*([^\n]+)")
	grab("Telephone", r"T[ée]l[ée]phone\s*:\s*([^\n]+)")
	grab("Email", r"Email\s*:\s*([^\n]+)")

	# Check-boxes (simple heuristiques, ajustez si besoin)
	data["StatutAdhesion"] = "Nouvel" if re.search(r"Nouvel\s+adh[ée]rent.*?[xX✓✔☑]", text, re.IGNORECASE) else "Renouvellement"
	if re.search(r"Adulte.*?[xX✓✔☑]", text, re.IGNORECASE):
		data["Categorie"] = "Adulte"
	elif re.search(r"Enfant.*?[xX✓✔☑]", text, re.IGNORECASE):
		data["Categorie"] = "Enfant"
	else:
		data["Categorie"] = "Ecole"

	data["BadgeCaution"] = "Oui" if re.search(r"Caution\s+pour\s+badge.*?[xX✓✔☑]", text, re.IGNORECASE) else "Non"
	data["CleCaution"]  = "Oui" if re.search(r"Caution\s+pour\s+cl[ée].*?[xX✓✔☑]", text, re.IGNORECASE)  else "Non"

	grab("Total", r"TOTAL\s*-\s*([^\n]+)")
	grab("DateInscription", r"Date\s+d['’]inscription\s*:\s*([^\n]+)")
	grab("NomResponsableLegal",  r"Nom\s+du\s+responsable\s+l[ée]gal\s*:\s*([^\n]+)")
	grab("TelResponsableLegal",  r"T[ée]l[ée]phone\s+du\s+responsable\s+l[ée]gal\s*:\s*([^\n]+)")
	grab("EmailResponsableLegal",r"Email\s+du\s+responsable\s+l[ée]gal\s*:\s*([^\n]+)")
	grab("AutresRemarques",      r"Autres\s+remarques\s*:\s*([^\n]+)")

	return data

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
	data["SourcePDF"] = os.path.basename(pdf_path)
	return data

def process_folder(folder, csv_out):
	logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
	pdfs = [f for f in os.listdir(folder) if f.lower().endswith(".pdf")]
	if not pdfs:
		logging.warning("No PDF files found in %s", folder)
		return
	write_header = not os.path.isfile(csv_out)
	with open(csv_out, "a", newline="", encoding="utf-8") as fh:
		writer = csv.DictWriter(fh, fieldnames=HEADERS)
		if write_header:
			writer.writeheader()
		for pdf in pdfs:
			logging.info("Processing %s", pdf)
			row = extract_pdf(os.path.join(folder, pdf))
			writer.writerow(row)

if __name__ == "__main__":
	process_folder(PDF_FOLDER, CSV_OUTPUT)
