# Données externes sourcées pour le challenge — Togo Télécoms & Inclusion Numérique

Toutes les données ci-dessous proviennent de sources publiques, documentées (URL, date de consultation, licence). Aucune valeur n'est interpolée ni inventée : les écarts de couverture sont documentés explicitement.

---

## 1. population_prefectures_togo_2022.csv

- **Source** : INSEED Togo, RGPH-5 (recensement de novembre 2022), Livret « Distribution spatiale de la population résidente par sexe » (avril 2023).
- **URL** : `https://aniit.org/wp-content/uploads/2024/09/rgph5_livret_01_effectifs-spatiale_par_sexe_-inseed_2mai2023-arms-1.pdf`
- **Consulté** : 13/09/2026 — **Licence** : donnée publique (INSEED).
- **Contenu** : population par préfecture (39 préfectures), hommes/femmes/total. Total vérifié = **8 095 498** hab. (total national officiel RGPH-5).
- Les noms de préfecture correspondent exactement au champ `prefecture_nom_bdd` des données BDD (jointure directe sur `prefecture`).

## 2. population_cantons_rgph5_2022.csv (+ script scripts/extract_rgph5_cantons.py)

- **Source** : même livret INSEED (pages 51-107, tables « effectif par sexe des **cantons** de la préfecture … »).
- **Méthode** : extraction pdfplumber par blocs délimités par les lignes « TOTAL PREFECTURE » ; chaque bloc est mis en correspondance **exacte** avec le total de préfecture du CSV (contrôle de cohérence systématique) ; sous-totaux « COMMUNE DE … » détectés par « somme des lignes enfants == sous-total ».
- **Validation** : somme par préfecture == total CSV == ligne « TOTAL PREFECTURE » pour 36/36 préfectures ; somme nationale extraite = **5 866 882** (hors **Golfe**, **Agoè-Nyivé** — publiées en *quartiers*, pas de tableau canton — et **Danyi** — publiée en 2 communes sans canton).
- **Contenu** : 370 lignes, colonnes `prefecture, canton, masculin, feminin, population_totale`.

## 3. tgo_admin_boundaries.geojson.zip → tgo_admin2_prefectures.csv / tgo_admin3_cantons.csv (scripts/build_hdx_csvs.py)

- **Source** : OCHA COD-AB Togo (HDX). **URL** : `https://data.humdata.org/dataset/cod-ab-tgo` — **Consulté** : 13/09/2026 — **Licence** : CC-BY-IGO.
- **ADM2** : 40 préfectures (y compris **Agoe-Nyive, Naki-Ouest, Oti-Sud, Plaine du Mo, Lome Commune**) — remplace le contournement geoBoundaries (37 polygones, voir §5).
- **ADM3** : 373 cantons avec centroïdes (`center_lat/center_lon`), surfaces et codes (`adm3_pcode`).
- ⚠️ HDX ne comporte **pas** les préfectures scindées **Mô** ni **Kpendjal-Ouest** : leurs cantons restent sous `Sotouboua` / `Kpendjal` (voir §4). Le polygone de **Mô** porte le nom HDX « Plaine du Mo » (mappé dans le pipeline).
- Le geojson de l'application (`data/processed/prefectures_merged.geojson`) est désormais **construit à partir de ces polygones HDX** (40 préfectures regroupées sous les clés `polygon_key`, géométries officielles), au lieu du contournement geoBoundaries.

## 4. canton_population_join.csv (script scripts/join_rgph5_adm3.py)

- Jointure RGPH-5 (nom canton PDF) → ADM3 HDX (polygone/centroïde), avec **contexte préfecture**.
- **Taux de résolution : 361/370 = 97,6 %** (305 exactes même préfecture + 11 exactes globales + 4 alias manuels + 41 fuzzy rapides revus).
- **9 cantons sans polygone HDX** (population **conservée**, `adm3_pcode` vide, `method=unmatched`) : `GBODJOME` (Lacs), `EDZI` (Avé), `DJAMA` (Ogou), `HAHOMEGBE` & `AKPAKPAKPE` (Haho), `NYOGBO-NORD NYOGBO-SUD` (Agou), `ZOGBEGAN` (Wawa), `KERIADE` (Sotouboua), `ANIMA` (Doufelgou) — ≈ 180 600 hab., à exclure du raisonnement « par polygone » et à évoquer dans le rapport.
- ⚠️ HDX fusionne parfois 2 cantons RGPH en un seul polygone (ex. `Afagnan/Afagnagan`, `Agou Yiboe/Kati`, `Ganave/Fiata`) : les populations restent distinctes dans le CSV, c'est l'agrégation cartographique qui les cumule.

## 5. togo_prefectures_boundaries.geojson

Source : geoBoundaries.org (CC BY 4.0), ADM2 Togo — **conserve 37 polygones historiques** ; désormais **supplanté** par les HDX ADM2/ADM3 (§3) pour toute analyse, sauf besoin d'un découpage « 37 préfectures » historique.

## 6. Couverture réseau mobile — non disponible en open data

Aucune source officielle (ARCEP Togo) ne publie de carte 2G/3G/4G téléchargeable.
- **OpenCelliD** (MCC 615) : fichier gzip ✓ < 2 Ko → **couverture insuffisante (≈ dizaines de cellules), constatée, non utilisée**.
- **Proxy méthodologique retenu** : distance au plus proche point de service (agence télécom / agent mobile money) par canton + seuil « zone blanche », documenté comme hypothèse dans le rapport.

## 7. CANAL+ (agences / points de vente) — canalbox_stores_2026.json + canal_osm_points_2026.json

- **canalbox_stores_2026.json** : API publique du site `https://www.canalbox.tg/wp-json/gva/v1/stores/?lang=fr` (consultée 13/09/2026) → **7 « CANAL+ STORE »** (ville = Lomé) avec coordonnées. Licence : propriétaire (données exposées publiquement sur le site officiel). Données `created_at` 2025.
- **canal_osm_points_2026.json** : Overpass API (13/09/2026, ODbL) `node["name"~"Canal",i](6.0,-0.2,11.2,1.9)` → 18 nœuds dont ~13 points de vente CANAL+ pertinents (Canal+ Distributeur, Canal+store, Canal Horizon…) + cinémas (CanalOlympia Godopé, Canal wak) — filtre à appliquer.
- **Rappel** : aucune liste publique complète des points de vente CANAL+ au Togo n'existe ; les fichiers précédents (« Agences - CANAL+ » BDD) sont vides/non fournis — documenté, pas ignoré.

## 8. Rappels BDD (ne pas modifier)
- « Agences - Télécom » = fusion exacte de « Agences - Togocom » + « Agences - Moov » (91 = 62+29). Ne pas traiter comme source indépendante ni dédoublonner (c'est la même donnée).