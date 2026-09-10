# Données externes sourcées pour le challenge — Togo Télécoms & Inclusion Numérique

## 1. population_prefectures_togo_2022.csv
Source officielle : INSEED Togo, RGPH-5 (recensement de novembre 2022), Livret "Distribution spatiale de la population résidente par sexe" (avril 2023).
https://aniit.org/wp-content/uploads/2024/09/rgph5_livret_01_effectifs-spatiale_par_sexe_-inseed_2mai2023-arms-1.pdf

Contenu : population par préfecture (39 préfectures), hommes/femmes/total. Total vérifié = 8 095 498 hab. (correspond au total national officiel).
Les noms de préfecture sont écrits pour correspondre EXACTEMENT au champ `prefecture_nom_bdd` de vos fichiers CSV (Moov, Togocom, mobile money, etc.), donc une simple jointure (merge/join) sur ce champ suffit.

## 2. togo_prefectures_boundaries.geojson
Source : geoBoundaries.org (licence CC BY 4.0), niveau ADM2 pour le Togo.
https://github.com/wmgeolab/geoBoundaries (release TGO/ADM2)

⚠️ Limite importante : ce fichier ne contient que 37 polygones (préfectures "historiques"), alors que le Togo compte aujourd'hui 39 préfectures. Il manque des polygones séparés pour :
- **Agoè-Nyivé** (issue de la scission de Golfe / Grand Lomé)
- **Kpendjal-Ouest** (issue de la scission de Kpendjal)
- **Oti-Sud** (issue de la scission d'Oti)

**Solution recommandée pour le dashboard** : pour la carte choroplèthe, fusionner temporairement les paires suivantes le temps d'afficher la densité (poids démographique combiné) :
- Golfe + Agoè-Nyivé → polygone "Golfe" du GeoJSON (Grand Lomé)
- Kpendjal + Kpendjal-Ouest → polygone "Kpendjal"
- Oti + Oti-Sud → polygone "Oti"
Ou alternativement, afficher la carte au niveau RÉGION (5 régions, sans ambiguïté) et garder le niveau préfecture pour les tableaux/graphiques en barres (pas de carte).

## 3. Couverture réseau mobile — non trouvée en open data prête à l'emploi
Aucune source officielle togolaise (ARCEP Togo) ne publie de carte de couverture 2G/3G/4G téléchargeable comme le fait l'ARCEP française. Deux options :
a) **Proxy méthodologique** (recommandé vu le délai) : calculer une distance au point de service le plus proche (agence télécom ou agent mobile money) par canton, et considérer "zone blanche" = canton dont la population n'a aucun point de service dans un rayon de X km. À documenter explicitement comme hypothèse dans le rapport.
b) OpenCelliD (opencellid.org) : base communautaire de positions d'antennes, téléchargeable gratuitement par pays (MCC Togo = 615) après inscription gratuite. Couverture potentiellement incomplète pour le Togo — à vérifier avant de s'appuyer dessus.

## 4. Autres limites de données déjà identifiées dans vos fichiers
- Le fichier "Agences - Télécom" est en réalité la fusion exacte de "Agences - Togocom" + "Agences - Moov" (91 = 62+29) — ne pas le traiter comme une 3ᵉ source indépendante.
- Le fichier "Agences - CANAL+" est vide (0 ligne) — à mentionner comme donnée non disponible plutôt qu'à ignorer silencieusement.
