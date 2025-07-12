import streamlit as st
import pandas as pd
from extractor import extract_pdf

st.title("Tennis Club – Import PDF → CSV")

uploaded_files = st.file_uploader(
	"Déposez un ou plusieurs formulaires PDF",
	type="pdf",
	accept_multiple_files=True
)

if uploaded_files:
	data = []
	with st.spinner("Extraction en cours…"):
		for up in uploaded_files:
			data.append(extract_pdf(up))	# retourne un dict
	df = pd.DataFrame(data)
	st.success(f"{len(df)} adhésion(s) importée(s) !")
	st.dataframe(df)

	# Téléchargement CSV
	csv_bytes = df.to_csv(index=False).encode("utf-8")
	st.download_button(
		label="📥 Télécharger le CSV",
		data=csv_bytes,
		file_name="adherents.csv",
		mime="text/csv"
	)
