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

# ---------------------------------------------------------------- Filtres
st.sidebar.header("Filtres")
communes = sorted(df["commune"].unique())
choix_communes = st.sidebar.multiselect("Communes", communes, default=communes)
annees = sorted(df["annee"].unique().tolist())
annee = st.sidebar.selectbox("Année", annees, index=annees.index(2025))

if not choix_communes:
    st.warning("Choisissez au moins une commune dans la barre latérale.")
    st.stop()

communes_choisies = df[df["commune"].isin(choix_communes)]
filtre = communes_choisies[communes_choisies["annee"] == annee]

# ---------------------------------------------------------------- Données
st.write(f"{len(filtre)} relevés pour cette sélection.")
st.dataframe(filtre, hide_index=True)
