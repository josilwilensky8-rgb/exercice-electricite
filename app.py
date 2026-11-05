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

# ---------------------------------------------------------------- Indicateurs
annee_precedente = communes_choisies[communes_choisies["annee"] == annee - 1]
total = filtre["kwh"].sum()
par_abonne = filtre["kwh_par_abonne"].mean()
heures = filtre["heures_courant"].mean()

if annee_precedente.empty:
    deltas = [None, None, None]
else:
    deltas = [
        f"{(total / annee_precedente['kwh'].sum() - 1) * 100:+.1f} % sur un an",
        f"{(par_abonne / annee_precedente['kwh_par_abonne'].mean() - 1) * 100:+.1f} % sur un an",
        f"{heures - annee_precedente['heures_courant'].mean():+.1f} h sur un an",
    ]

col1, col2, col3 = st.columns(3)
col1.metric("Consommation totale (millions de kWh)", f"{total / 1_000_000:.2f}", deltas[0], border=True)
col2.metric("Consommation par abonné (kWh par mois)", f"{par_abonne:.1f}", deltas[1], border=True)
col3.metric("Courant disponible (heures par jour)", f"{heures:.1f}", deltas[2], border=True)

# ---------------------------------------------------------------- Données
st.write(f"{len(filtre)} relevés pour cette sélection.")
st.dataframe(filtre, hide_index=True)
