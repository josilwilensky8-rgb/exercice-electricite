from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

DOSSIER = Path(__file__).parent / "donnees"

ROUGE = "#A71E36"
GRIS = "#898781"
COULEURS_COMMUNES = {
    "Cap-Haïtien": "#2a78d6",
    "Delmas": "#eb6834",
    "Port-au-Prince": "#1baf7a",
    "Pétion-Ville": "#eda100",
}
COULEURS_TYPES = {"Commercial": ROUGE, "Résidentiel": GRIS}

st.set_page_config(page_title="L'électricité dans 12 quartiers", page_icon="⚡", layout="wide")

st.title("L'électricité dans 12 quartiers")
st.caption("Relevés mensuels de janvier 2024 à décembre 2025. Données fictives.")


@st.cache_data
def charger_donnees():
    return pd.read_csv(DOSSIER / "consommation_propre.csv")


def nombre(valeur):
    """742780 -> '742 780'"""
    return f"{valeur:,.0f}".replace(",", " ")


def enumerer(elements):
    """['a', 'b', 'c'] -> 'a, b et c'"""
    return elements[0] if len(elements) == 1 else ", ".join(elements[:-1]) + " et " + elements[-1]


def echelle(couleurs, valeurs):
    """Chaque commune (ou type) garde toujours la même couleur, même filtrée."""
    presentes = [nom for nom in couleurs if nom in set(valeurs)]
    return alt.Scale(domain=presentes, range=[couleurs[nom] for nom in presentes])


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

# ---------------------------------------------------------------- Onglets
onglet_abonne, onglet_evolution, onglet_correlation, onglet_coupures, onglet_records = st.tabs(
    ["Qui consomme le plus ?", "Évolution par commune", "Chaleur ou courant ?", "Coupures", "Relevés records"]
)

with onglet_abonne:
    classement = filtre.groupby(["quartier", "type"], as_index=False)["kwh_par_abonne"].mean()
    par_type = filtre.groupby("type")["kwh_par_abonne"].mean()
    st.markdown(
        f"En {annee}, un abonné commercial consomme en moyenne **{par_type['Commercial']:.1f} kWh** par mois, "
        f"contre **{par_type['Résidentiel']:.1f} kWh** pour un abonné résidentiel : "
        f"{par_type['Commercial'] / par_type['Résidentiel']:.1f} fois plus."
    )
    ordre = classement.sort_values("kwh_par_abonne", ascending=False)["quartier"].tolist()
    base = alt.Chart(classement).encode(
        x=alt.X("kwh_par_abonne:Q", title="kWh par abonné et par mois (moyenne)", axis=alt.Axis(tickCount=6)),
        y=alt.Y("quartier:N", sort=ordre, title=None),
    )
    barres = base.mark_bar(cornerRadiusEnd=4).encode(
        color=alt.Color("type:N", scale=echelle(COULEURS_TYPES, classement["type"]),
                        legend=alt.Legend(title=None, orient="top")),
        tooltip=[
            alt.Tooltip("quartier:N", title="Quartier"),
            alt.Tooltip("type:N", title="Type"),
            alt.Tooltip("kwh_par_abonne:Q", title="kWh par abonné", format=".1f"),
        ],
    )
    valeurs = base.mark_text(align="left", dx=5, color="#52514e").encode(
        text=alt.Text("kwh_par_abonne:Q", format=".0f")
    )
    st.altair_chart((barres + valeurs).properties(height=alt.Step(30)))

with onglet_evolution:
    st.caption("Cet onglet compare les deux années : seul le filtre des communes s'applique.")
    debut, fin = annees[0], annees[-1]
    totaux = communes_choisies.pivot_table(index="commune", columns="annee", values="kwh", aggfunc="sum")
    totaux["hausse"] = (totaux[fin] - totaux[debut]) / totaux[debut] * 100
    totaux = totaux.sort_values("hausse", ascending=False)

    premiere = totaux.index[0]
    evolution = (
        f"de {totaux.loc[premiere, debut] / 1e6:.2f} à {totaux.loc[premiere, fin] / 1e6:.2f} millions de kWh "
        f"({totaux.loc[premiere, 'hausse']:+.1f} %)"
    )
    if len(totaux) == 1:
        phrase = f"Entre {debut} et {fin}, **{premiere}** passe {evolution}."
    else:
        derniere = totaux.index[-1]
        phrase = (
            f"Entre {debut} et {fin}, **{premiere}** progresse le plus : {evolution}. "
            f"**{derniere}** progresse le moins ({totaux.loc[derniere, 'hausse']:+.1f} %)."
        )
    st.markdown(phrase)

    par_mois = communes_choisies.groupby(["mois", "commune"], as_index=False)["kwh_par_abonne"].mean()
    par_mois["date"] = pd.to_datetime(par_mois["mois"])
    courbes = (
        alt.Chart(par_mois)
        .mark_line(strokeWidth=2, point=alt.OverlayMarkDef(size=36, filled=True))
        .encode(
            x=alt.X("date:T", title=None, axis=alt.Axis(format="%m/%Y")),
            y=alt.Y("kwh_par_abonne:Q", title="kWh par abonné (moyenne des quartiers)"),
            color=alt.Color("commune:N", scale=echelle(COULEURS_COMMUNES, par_mois["commune"]),
                            legend=alt.Legend(title=None, orient="top")),
            tooltip=[
                alt.Tooltip("commune:N", title="Commune"),
                alt.Tooltip("mois:N", title="Mois"),
                alt.Tooltip("kwh_par_abonne:Q", title="kWh par abonné", format=".1f"),
            ],
        )
        .properties(height=380)
    )
    st.altair_chart(courbes)

    tableau = totaux[[debut, fin]] / 1e6
    tableau.columns = [f"{debut} (millions de kWh)", f"{fin} (millions de kWh)"]
    tableau["Hausse (%)"] = totaux["hausse"]
    tableau.index.name = "Commune"
    st.dataframe(
        tableau,
        column_config={
            f"{debut} (millions de kWh)": st.column_config.NumberColumn(format="%.2f"),
            f"{fin} (millions de kWh)": st.column_config.NumberColumn(format="%.2f"),
            "Hausse (%)": st.column_config.NumberColumn(format="%+.1f %%"),
        },
    )

with onglet_correlation:
    st.caption("Quartiers résidentiels, 2024 et 2025 : seul le filtre des communes s'applique.")
    residentiel = communes_choisies[communes_choisies["type"] == "Résidentiel"]
    corr_courant = residentiel["kwh_par_abonne"].corr(residentiel["heures_courant"])
    corr_chaleur = residentiel["kwh_par_abonne"].corr(residentiel["temperature_c"])
    st.markdown(
        f"Dans les quartiers résidentiels, la consommation par abonné suit les heures de courant "
        f"(corrélation de **{corr_courant:.2f}**), bien plus que la température (**{corr_chaleur:.2f}**)."
    )

    def nuage(colonne, titre, corr):
        return (
            alt.Chart(residentiel, title=alt.Title(f"Corrélation : {corr:.2f}", fontWeight="normal"))
            .mark_circle(size=60, opacity=0.7, color=ROUGE, stroke="white", strokeWidth=1)
            .encode(
                x=alt.X(f"{colonne}:Q", title=titre, scale=alt.Scale(zero=False)),
                y=alt.Y("kwh_par_abonne:Q", title="kWh par abonné"),
                tooltip=[
                    alt.Tooltip("quartier:N", title="Quartier"),
                    alt.Tooltip("mois:N", title="Mois"),
                    alt.Tooltip(f"{colonne}:Q", title=titre, format=".1f"),
                    alt.Tooltip("kwh_par_abonne:Q", title="kWh par abonné", format=".1f"),
                ],
            )
            .properties(height=340)
        )

    gauche, droite = st.columns(2)
    gauche.altair_chart(nuage("heures_courant", "Heures de courant par jour", corr_courant))
    droite.altair_chart(nuage("temperature_c", "Température moyenne (°C)", corr_chaleur))

with onglet_coupures:
    coupures = filtre[filtre["heures_courant"] < 8].sort_values("mois")
    medianes = filtre.groupby("commune")["heures_courant"].median().sort_values()
    if len(medianes) == 1:
        phrase = f"En {annee}, **{medianes.index[0]}** a une médiane de {medianes.iloc[0]:.1f} heures de courant par jour. "
    else:
        phrase = (
            f"En {annee}, la médiane la plus basse est à **{medianes.index[0]}** : "
            f"{medianes.iloc[0]:.1f} heures de courant par jour. "
        )
    if coupures.empty:
        phrase += "Aucun relevé ne descend sous 8 heures par jour."
    elif len(coupures) <= 5:
        details = enumerer([
            f"{quartier} en {mois} ({h:.1f} h)"
            for quartier, mois, h in coupures[["quartier", "mois", "heures_courant"]].itertuples(index=False)
        ])
        sujet = f"**{len(coupures)} relevés** descendent" if len(coupures) > 1 else "**1 relevé** descend"
        phrase += f"{sujet} sous 8 heures par jour : {details}."
    else:
        par_quartier = coupures["quartier"].value_counts().head(3)
        details = enumerer([f"{n} à {quartier}" for quartier, n in par_quartier.items()])
        phrase += f"**{len(coupures)} relevés** descendent sous 8 heures par jour, dont {details}."
    st.markdown(phrase)

    histogramme = (
        alt.Chart(filtre)
        .mark_bar(stroke="white", strokeWidth=1)
        .encode(
            x=alt.X("heures_courant:Q", bin=alt.Bin(step=1), title="Heures de courant par jour"),
            y=alt.Y("count():Q", title="Nombre de relevés"),
            color=alt.Color("commune:N", scale=echelle(COULEURS_COMMUNES, filtre["commune"]),
                            legend=alt.Legend(title=None, orient="top")),
            tooltip=[
                alt.Tooltip("commune:N", title="Commune"),
                alt.Tooltip("heures_courant:Q", bin=alt.Bin(step=1), title="Heures de courant"),
                alt.Tooltip("count():Q", title="Relevés"),
            ],
        )
    )
    seuil = (
        alt.Chart(pd.DataFrame({"seuil": [8]}))
        .mark_rule(color="#2b2b2b", strokeWidth=1.5)
        .encode(x=alt.X("seuil:Q", title="Heures de courant par jour"))
    )
    gauche, droite = st.columns([2, 1])
    gauche.altair_chart((histogramme + seuil).properties(height=340))

    quartiles = (
        filtre.groupby("commune")["heures_courant"]
        .quantile([0.25, 0.5, 0.75])
        .unstack()
        .rename(columns={0.25: "Q1", 0.5: "Médiane", 0.75: "Q3"})
        [["Médiane", "Q1", "Q3"]]
        .sort_values("Médiane")
    )
    quartiles.index.name = "Commune"
    droite.markdown("**Heures de courant par jour**")
    droite.dataframe(quartiles, column_config={c: st.column_config.NumberColumn(format="%.1f") for c in quartiles})
    droite.caption("Le trait noir du graphique marque le seuil de 8 heures.")

with onglet_records:
    records = filtre.nlargest(10, "kwh").copy()
    records["releve"] = records["quartier"] + " · " + records["mois"]
    records["kwh_texte"] = records["kwh"].map(nombre)
    records["milliers_kwh"] = records["kwh"] / 1000
    plus_gros = records.iloc[0]
    st.markdown(
        f"En {annee}, le plus gros relevé est celui de **{plus_gros['quartier']}** en {plus_gros['mois']} : "
        f"**{plus_gros['kwh_texte']} kWh**, avec {plus_gros['heures_courant']:.1f} heures de courant par jour."
    )
    base = alt.Chart(records).encode(
        x=alt.X("milliers_kwh:Q", title="Milliers de kWh sur le mois", axis=alt.Axis(tickCount=6)),
        y=alt.Y("releve:N", sort=records["releve"].tolist(), title=None, axis=alt.Axis(labelLimit=240)),
    )
    barres = base.mark_bar(cornerRadiusEnd=4).encode(
        color=alt.Color("type:N", scale=echelle(COULEURS_TYPES, records["type"]),
                        legend=alt.Legend(title=None, orient="top")),
        tooltip=[
            alt.Tooltip("quartier:N", title="Quartier"),
            alt.Tooltip("mois:N", title="Mois"),
            alt.Tooltip("kwh_texte:N", title="kWh"),
            alt.Tooltip("heures_courant:Q", title="Heures de courant", format=".1f"),
        ],
    )
    valeurs = base.mark_text(align="left", dx=5, color="#52514e").encode(text="kwh_texte:N")
    st.altair_chart((barres + valeurs).properties(height=alt.Step(30)))
    st.dataframe(
        records.head(3)[["mois", "quartier", "type", "kwh"]],
        hide_index=True,
        column_config={
            "mois": "Mois",
            "quartier": "Quartier",
            "type": "Type",
            "kwh": st.column_config.NumberColumn("kWh", format="localized"),
        },
    )

# ---------------------------------------------------------------- Conclusion
st.divider()
st.subheader("Conclusion")
st.markdown(
    "La consommation suit **les heures de courant**, pas la chaleur. Dans les quartiers résidentiels, "
    "la consommation par abonné a une corrélation de **0.76** avec les heures de courant, contre "
    "**-0.15** seulement avec la température, et Cap-Haïtien, où le courant manque le plus (10.0 heures "
    "par jour en médiane), est aussi la commune où les ménages consomment le moins (70.8 kWh par abonné "
    "et par mois). Une corrélation montre que deux mesures varient ensemble, mais elle ne prouve pas que "
    "l'une cause l'autre : d'autres facteurs, comme les revenus, les équipements ou les tarifs, peuvent "
    "jouer, et ces relevés ne couvrent que 24 mois."
)

with st.expander(f"Voir les données filtrées ({len(filtre)} relevés)"):
    st.dataframe(
        filtre,
        hide_index=True,
        column_config={
            "mois": "Mois",
            "quartier": "Quartier",
            "kwh": st.column_config.NumberColumn("kWh", format="%d"),
            "heures_courant": st.column_config.NumberColumn("Heures de courant", format="%.1f"),
            "commune": "Commune",
            "type": "Type",
            "abonnes": "Abonnés",
            "kwh_par_abonne": st.column_config.NumberColumn("kWh par abonné", format="%.1f"),
            "annee": st.column_config.NumberColumn("Année", format="%d"),
            "temperature_c": st.column_config.NumberColumn("Température (°C)", format="%.1f"),
            "pluie_mm": st.column_config.NumberColumn("Pluie (mm)", format="%d"),
        },
    )
