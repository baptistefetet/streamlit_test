import streamlit as st
import pandas as pd
import tempfile
import os
import json
import importlib
import re
import extractor

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
UPLOADER_KEY = "pdfs"	# key for the file_uploader


# ───────────────────────────────
# Helpers for the configuration
# ───────────────────────────────
def load_config():
	"""Return the current config (disk on Windows, session_state elsewhere)."""
	if os.name != "nt" and "config" in st.session_state:
		return st.session_state["config"]

	try:
		with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
			return json.load(fh)
	except FileNotFoundError:
		return []

def save_config(cfg):
	"""Persist the config if allowed; otherwise keep it in session_state."""
	if os.name == "nt":
		with open(CONFIG_PATH, "w", encoding="utf-8") as fh:
			json.dump(cfg, fh, indent=2, ensure_ascii=False)
	else:
		# In-memory only
		st.session_state["config"] = cfg


cfg = load_config()


# ───────────────────────────────
# Sidebar – dynamic field settings
# ───────────────────────────────
with st.sidebar.expander("Configuration des champs"):
	st.write("Champs actuels :")
	for f in cfg:
		st.write(f"- {f['name']} ({f['type']})")

	# Delete an existing field
	if cfg:
		field_names = [f["name"] for f in cfg]
		field_to_delete = st.selectbox("Supprimer un champ", [""] + field_names)
		if field_to_delete and st.button("Supprimer le champ"):
			cfg = [f for f in cfg if f["name"] != field_to_delete]
			save_config(cfg)
			importlib.reload(extractor)
			st.rerun()

	# Add a new field
	with st.form("add_field"):
		st.subheader("Ajouter un champ")
		new_name = st.text_input("Nom du champ")
		new_type = st.selectbox("Type", ["text", "number", "checkbox"])
		submitted = st.form_submit_button("Ajouter")

	if submitted and new_name:
		entry = {
			"name": new_name.upper(),
			"type": new_type,
			"acro_key": new_name.lower(),
		}
		if new_type == "checkbox":
			cb = r"[xX✓✔☑☒✗✘❌■]"
			entry["pattern"] = rf"(?:{cb}\s*{re.escape(new_name)})|(?:{re.escape(new_name)}[^\n]{{0,30}}{cb})"
			entry["checked_value"] = "1"
			entry["unchecked_value"] = "0"
		cfg.append(entry)
		save_config(cfg)
		importlib.reload(extractor)
		st.rerun()


# ───────────────────────────────
# Main – PDF → CSV importer
# ───────────────────────────────
st.title("Tennis Club – Import PDF → CSV")

uploaded_files = st.file_uploader(
	"Déposez un ou plusieurs formulaires PDF",
	type="pdf",
	accept_multiple_files=True,
	key=UPLOADER_KEY,
)

import_clicked = st.button("Importer")	# separate widget ⇒ safe to reset uploader

if import_clicked and uploaded_files:
	data = []
	with st.spinner("Extraction en cours…"):
		for up in uploaded_files:
			# Copy the uploaded PDF to a temp file on disk
			with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
				tmp.write(up.read())
				tmp.flush()
				tmp_path = tmp.name
			try:
				# extractor.extract_pdf expects a file path
				data.append(extractor.extract_pdf(tmp_path))
			finally:
				os.remove(tmp_path)

	# Convert to DataFrame and persist to CSV (overwrite)
	df = pd.DataFrame(data)
	csv_path = os.path.join(os.path.dirname(__file__), "adherents.csv")
	df.to_csv(csv_path, index=False, encoding="utf-8")

	st.success(f"{len(df)} adhésion(s) importée(s) !")
	st.dataframe(df)

	# Offer a CSV to download (in-memory, regenerated each run)
	csv_bytes = df.to_csv(index=False).encode("utf-8")
	st.download_button(
		label="📥 Télécharger le CSV",
		data=csv_bytes,
		file_name="adherents.csv",
		mime="text/csv",
	)

	# ───────────────────────────────
	# Reset the uploader so the next Browse starts clean
	# ───────────────────────────────
	del st.session_state[UPLOADER_KEY]		# or st.session_state.pop(UPLOADER_KEY, None)
