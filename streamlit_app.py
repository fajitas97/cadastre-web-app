# streamlit_app.py
import streamlit as st
import geopandas as gpd
import pandas as pd
import requests
import gzip
from io import BytesIO
import time
import warnings

st.set_page_config(page_title="Cadastre Finder", layout="wide")

# -------------------- Utilitaires --------------------
@st.cache_data(show_spinner=False)
def load_geojson_for_dept(dept_code: str = "14"):
    """Télécharge et charge (avec cache) le GeoJSON gz du cadastre pour le département donné.
    Retourne un GeoDataFrame.
    """
    url_geojson = f"https://cadastre.data.gouv.fr/data/etalab-cadastre/2025-04-01/geojson/departements/{dept_code}/cadastre-{dept_code}-parcelles.json.gz"
    r = requests.get(url_geojson, timeout=60)
    r.raise_for_status()
    with gzip.GzipFile(fileobj=BytesIO(r.content)) as gz:
        gdf = gpd.read_file(gz)
    return gdf

@st.cache_data
def build_commune_labels_and_map(gdf):
    unique_codes = list(map(str, gdf['commune'].unique()))
    commune_labels = []
    code_to_nom = {}
    for code in unique_codes:
        try:
            r = requests.get(f"https://geo.api.gouv.fr/communes/{code}?fields=nom&format=json", timeout=6)
            if r.status_code == 200:
                nom = r.json().get("nom")
                if nom:
                    label = f"{nom} ({code})"
                    commune_labels.append(label)
                    code_to_nom[code] = nom
                    time.sleep(0.01)
                    continue
        except Exception:
            pass
        commune_labels.append(code)
        code_to_nom[code] = code

    commune_labels = sorted(commune_labels, key=lambda x: x.split(" (")[0].lower())
    return commune_labels, code_to_nom

# helper links
lien_geoportail_from_coords = lambda lon, lat: (
    f"https://www.geoportail.gouv.fr/carte?c={lon},{lat}&z=19"
    "&l0=ORTHOIMAGERY.ORTHOPHOTOS::GEOPORTAIL:OGC:WMTS(1)"
    "&l1=CADASTRALPARCELS.PARCELLAIRE_EXPRESS::GEOPORTAIL:OGC:WMTS(1)&permalink=yes"
)

lien_google_maps_from_coords = lambda lat, lon: f"https://www.google.com/maps?q={lat},{lon}&z=19"

lien_street_view_from_coords = lambda lat, lon: f"https://www.google.com/maps/@?api=1&map_action=pano&viewpoint={lat},{lon}"

lien_adresse_approx_from_coords = lambda lat, lon: f"https://adresse.data.gouv.fr/recherche/?q={lat}+{lon}"

# extract parcel name
extraire_nom_parcelle = lambda id_cad: id_cad.split("_")[1] if (isinstance(id_cad, str) and "_" in id_cad) else id_cad

# -------------------- UI --------------------
st.title("Cadastre Finder — application web")
st.caption("Charge un département, filtre par communes et surface, et explore les parcelles trouvées.")

with st.sidebar:
    st.header("Configuration")
    dept_code = st.text_input("Code département (2 chiffres)", value="14")
    if st.button("(Re)charger les données du département"):
        st.session_state['reload'] = True

# Load data (with cache)
try:
    gdf = load_geojson_for_dept(dept_code)
except Exception as e:
    st.error(f"Impossible de charger le GeoJSON du cadastre pour le département {dept_code} : {e}")
    st.stop()

commune_labels, code_to_nom = build_commune_labels_and_map(gdf)

# Main controls
col1, col2 = st.columns([2,1])
with col1:
    communes_sel = st.multiselect("Communes (recherche intégrée)", options=commune_labels, default=[], help="Tape quelques lettres pour filtrer la liste et sélectionner plusieurs communes.")
with col2:
    surface = st.number_input("Surface (m²)", min_value=1, value=469)
    run = st.button("Lancer la recherche")

# Display selected communes summary
st.markdown("**Communes sélectionnées :**")
if communes_sel:
    st.write("\n".join(communes_sel))
else:
    st.write("(Aucune commune sélectionnée)")

# Search handler
if run:
    # extract codes
    codes = []
    for s in communes_sel:
        if "(" in s and s.strip().endswith(")"):
            codes.append(s.split("(")[-1].strip(")"))
        else:
            codes.append(s)

    if len(codes) == 0:
        st.warning("Sélectionne au moins une commune.")
    elif surface <= 0:
        st.warning("Saisis une surface positive.")
    else:
        with st.spinner("Filtrage des parcelles..."):
            try:
                gdf_filtre = gdf[gdf['commune'].isin(codes) & (gdf['contenance'] == surface)].copy()
            except Exception as e:
                st.error(f"Erreur lors du filtrage : {e}")
                st.stop()

        st.write(f"**Nombre de parcelles trouvées :** {len(gdf_filtre)}")
        if gdf_filtre.empty:
            st.info("Aucune parcelle trouvée pour ces critères.")
        else:
            # centroid calculation (more precise via reprojection)
            try:
                gdf_proj = gdf_filtre.to_crs(epsg=2154)
                cent_proj = gdf_proj.geometry.centroid
                cent_wgs84 = gpd.GeoSeries(cent_proj, crs=2154).to_crs(epsg=4326)
                gdf_filtre['centroid'] = cent_wgs84.values
            except Exception:
                warnings.warn("Reprojection échouée, utilisation des centroïdes bruts.")
                gdf_filtre['centroid'] = gdf_filtre.geometry.centroid

            # build table
            rows = []
            for idx, row in gdf_filtre.iterrows():
                c = row['centroid']
                lon, lat = c.x, c.y
                rows.append({
                    'nom_parcelle': extraire_nom_parcelle(row['id']),
                    'code_insee': row['commune'],
                    'nom_commune': code_to_nom.get(str(row['commune']), str(row['commune'])),
                    'surface_m2': row['contenance'],
                    'url_geoportail': lien_geoportail_from_coords(lon, lat),
                    'url_google_maps': lien_google_maps_from_coords(lat, lon),
                    'url_street_view': lien_street_view_from_coords(lat, lon),
                    'url_adresse_approx': lien_adresse_approx_from_coords(lat, lon)
                })

            df = pd.DataFrame(rows)

            # show table with clickable links (markdown)
            def make_link(url, label):
                return f"[{label}]({url})"

            df_display = df.copy()
            df_display['Géoportail'] = df.apply(lambda r: make_link(r['url_geoportail'], 'Géoportail'), axis=1)
            df_display['Google Maps'] = df.apply(lambda r: make_link(r['url_google_maps'], 'Maps'), axis=1)
            df_display['Street View'] = df.apply(lambda r: make_link(r['url_street_view'], 'Street View'), axis=1)
            df_display['API Adresse'] = df.apply(lambda r: make_link(r['url_adresse_approx'], 'API Adresse'), axis=1)

            cols_to_show = ['nom_parcelle', 'code_insee', 'nom_commune', 'surface_m2', 'Géoportail', 'Google Maps', 'Street View', 'API Adresse']

            st.dataframe(df_display[cols_to_show], use_container_width=True)

            # CSV download
            csv = df.to_csv(index=False)
            st.download_button("Télécharger CSV", csv, file_name=f"parcelles_{'_'.join(codes)}_{surface}m2.csv", mime='text/csv')

            # Optional: show map with the centroids
            try:
                # convert centroids to DataFrame of lat/lon for st.map
                pts = pd.DataFrame([{'lat': g.y, 'lon': g.x} for g in gdf_filtre['centroid']])
                st.map(pts, use_container_width=True)
            except Exception:
                pass
