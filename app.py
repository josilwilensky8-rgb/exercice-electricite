from pathlib import Path

import pandas as pd
import streamlit as st

DOSSIER = Path(__file__).parent / "donnees"

st.set_page_config(page_title="L'électricité dans 12 quartiers", page_icon="⚡", layout="wide")

st.title("L'électricité dans 12 quartiers")
st.caption("Relevés mensuels de janvier 2024 à décembre 2025. Données fictives.")


@st.cache_data
def charger_donnees():
    return pd.read_csv(DOSSIER / "consommation_propre.csv")


df = charger_donnees()

st.markdown(
    "Une compagnie d'électricité suit chaque mois la consommation de 12 quartiers de Port-au-Prince, "
    "Delmas, Pétion-Ville et Cap-Haïtien. Son directeur veut savoir si **la consommation suit la "
    "chaleur, ou les heures de courant**."
)

st.write(f"Le fichier propre compte {len(df)} relevés.")
st.dataframe(df.head(10), hide_index=True)
