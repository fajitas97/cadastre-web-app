import streamlit as st
import pandas as pd
import geopandas as gpd
import requests

st.set_page_config(page_title="Recherche Cadastre", layout="wide")

# Chargement des données GeoJSON
@st.cache_data
def load_cadastre(url):
    try:
        gdf = gpd.read_file(url)
        return gdf
    except Exception as e:
        st.error(f"Erreur lors du chargement : {e}")
        return None

# Correction ici : on met _gdf pour éviter le hash
@st.cache_data
def build_commune_labels_and_map(_gdf):
    commune_labels = [
        f"{row['nom']} ({row['insee']})" for _, row in _gdf.iterrows()
    ]
    code_to_nom = {row['insee']: row['nom'] for _, row in _gdf.iterrows()}
    return commune_labels, code_to_nom

# URL de tes données cadastre
cadastre_url = "TON_URL_GEOJSON_ICI"
gdf = load_cadastre(cadastre_url)

if gdf is None:
    st.stop()

commune_labels, code_to_nom = build_commune_labels_and_map(gdf)

# Interface de sélection avec recherche multi
selected_communes = st.multiselect(
    "Rechercher et sélectionner des communes :",
    options=commune_labels,
    default=[]
)

# Affichage des communes sélectionnées
if selected_communes:
    st.write("Communes sélectionnées :", selected_communes)

# Filtrage du GeoDataFrame
if selected_communes:
    selected_codes = [label.split("(")[-1].strip(")") for label in selected_communes]
    filtered_gdf = gdf[gdf["insee"].isin(selected_codes)].copy()
else:
    filtered_gdf = gdf.copy()

# Conversion en DataFrame pour affichage
df = pd.DataFrame(filtered_gdf.drop(columns="geometry"))
st.dataframe(df)
