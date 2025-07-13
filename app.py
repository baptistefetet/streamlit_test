import streamlit as st
import pandas as pd
import tempfile
import os
import json
import importlib
import re
import extractor

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)

def save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, indent=2, ensure_ascii=False)

cfg = load_config()

with st.sidebar.expander("Configuration des champs"):
    st.write("Champs actuels:")
    for f in cfg:
        st.write(f"- {f['name']} ({f['type']})")

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
        st.experimental_rerun()

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
                data.append(extractor.extract_pdf(tmp_path))  # Passe le chemin du fichier
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
