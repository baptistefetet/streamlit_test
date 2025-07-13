import streamlit as st
import pandas as pd
import tempfile
import os
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
            # Crée un fichier temporaire qui ne sera pas supprimé automatiquement
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(up.read())
                tmp.flush()
                tmp_path = tmp.name
            try:
                data.append(extract_pdf(tmp_path))  # Passe le chemin du fichier
            finally:
                os.remove(tmp_path)  # Supprime le fichier temporaire après extraction
    df = pd.DataFrame(data)
    st.success(f"{len(df)} adhésion(s) importée(s) !")
    st.dataframe(df)

    # Génère le CSV en mémoire à chaque fois, sans append ni création de fichier sur le disque
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Télécharger le CSV",
        data=csv_bytes,
        file_name="adherents.csv",
        mime="text/csv"
    )