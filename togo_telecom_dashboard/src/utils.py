"""
Fonctions utilitaires partagées par le pipeline de données et les pages Streamlit.
"""
import re
import pandas as pd

WKT_POINT_RE = re.compile(r"POINT\s*\(\s*([\-0-9.]+)\s+([\-0-9.]+)\s*\)")


def parse_point_wkt(wkt: str):
    """Extrait (longitude, latitude) d'une chaîne 'POINT (lon lat)'.
    Retourne (None, None) si le parsing échoue (valeur manquante, format inattendu).
    """
    if not isinstance(wkt, str):
        return None, None
    m = WKT_POINT_RE.search(wkt)
    if not m:
        return None, None
    lon, lat = float(m.group(1)), float(m.group(2))
    return lon, lat


def add_lonlat(df: pd.DataFrame, geometry_col: str = "geometry") -> pd.DataFrame:
    """Ajoute les colonnes lon/lat à un DataFrame contenant une colonne WKT POINT."""
    coords = df[geometry_col].apply(parse_point_wkt)
    df = df.copy()
    df["lon"] = coords.apply(lambda t: t[0])
    df["lat"] = coords.apply(lambda t: t[1])
    return df


def format_int(n) -> str:
    """Formate un entier avec des espaces comme séparateur de milliers (convention FR)."""
    try:
        return f"{int(round(n)):,}".replace(",", " ")
    except (ValueError, TypeError):
        return str(n)


# Le GeoJSON externe (geoBoundaries, niveau ADM2) ne propose que 37 polygones
# alors que le Togo compte aujourd'hui 39 préfectures, et utilise par endroits
# une orthographe ou un découpage différents. On regroupe donc nos 39
# préfectures et les 37 formes du GeoJSON sous une même clé de groupe ("GROUP_KEY")
# pour pouvoir agréger et faire correspondre les deux. Voir
# data/external/README_donnees_externes.md pour le détail de cette limite.

# Nos préfectures (colonne prefecture_nom_bdd / population) -> clé de groupe
PREFECTURE_TO_GROUP = {
    "Golfe": "GrandLome",
    "Agoè-Nyivé": "GrandLome",          # scission de Golfe (Grand Lomé)
    "Kpendjal": "KpendjalGroup",
    "Kpendjal-Ouest": "KpendjalGroup",  # scission de Kpendjal
    "Oti": "OtiGroup",
    "Oti-Sud": "OtiGroup",              # scission d'Oti
}

# Formes du GeoJSON (propriété shapeName) -> même clé de groupe
SHAPE_NAME_TO_GROUP = {
    "Golfe": "GrandLome",
    "Lome Commune": "GrandLome",        # Lomé-ville, distincte de "Golfe" dans ce jeu de formes
    "Kpendjal": "KpendjalGroup",
    "Oti": "OtiGroup",
    "Ave": "Avé",
    "Plaine de Mô": "Mô",
    "Tone": "Tône",
    "Keran": "Kéran",
    "Tandjouare": "Tandjoaré",
}


def polygon_key(prefecture: str) -> str:
    """Clé de groupe pour une préfecture (table population/indicateurs)."""
    return PREFECTURE_TO_GROUP.get(prefecture, prefecture)


def shape_group_key(shape_name: str) -> str:
    """Clé de groupe pour une forme du GeoJSON (propriété shapeName)."""
    return SHAPE_NAME_TO_GROUP.get(shape_name, shape_name)
