# Diagnostic Télécoms & Inclusion Numérique — Togo

Dashboard Streamlit construit pour le challenge de diagnostic de l'accès aux
télécommunications et services numériques au Togo, avec recommandations
stratégiques d'extension de la connectivité.

## Installation et lancement

```bash
# 1. Créer un environnement virtuel (recommandé)
python -m venv venv
source venv/bin/activate        # Windows : venv\Scripts\activate

# 2. Installer les dépendances
pip install -r requirements.txt

# 3. Générer les données préparées (obligatoire au premier lancement,
#    et à refaire si les fichiers dans data/raw/ ou data/external/ changent)
python src/data_pipeline.py

# 4. Lancer le dashboard
streamlit run app.py
```

L'application s'ouvre sur `http://localhost:8501`.

### Lancement avec Docker

```bash
docker compose up --build
```

L'application s'ouvre sur `http://localhost:8501`. L'image embarque les données
préparées (`data/processed/`) : aucune étape de génération n'est nécessaire au
démarrage en conteneur. Pour régénérer les données préparées (nouveaux fichiers
dans `data/raw/` ou `data/external/`), lancer en local
`python src/data_pipeline.py` avant de reconstruire l'image.

## Structure du projet

```
togo_telecom_dashboard/
├── app.py                              # Page d'accueil (Vue d'ensemble)
├── pages/                              # Pages additionnelles du dashboard (multipage Streamlit)
│   ├── 1_Cartographie_Infrastructures.py
│   ├── 2_Mobile_Money_vs_Population.py
│   ├── 3_Zones_Blanches.py
│   └── 4_Recommandations.py
├── src/
│   ├── data_pipeline.py                # Nettoyage + calcul des indicateurs (à lancer une fois)
│   ├── data_loader.py                  # Chargement des données préparées, avec cache Streamlit
│   ├── style_loader.py                 # Design system : tokens, héros, styles Plotly
│   ├── components/
│   │   ├── filter_bar.py               # Barre de filtres horizontale partagée (persistance session_state)
│   │   └── icons.py                    # Icônes SVG ligne fine (aucun émoji dans l'app)
│   └── utils.py                        # Fonctions utilitaires (parsing WKT, mapping préfectures)
├── data/
│   ├── raw/                            # Fichiers bruts fournis pour le challenge (inchangés)
│   ├── external/                       # Données externes sourcées (population, limites admin., CANAL+)
│   │   └── README_donnees_externes.md  # Détail des sources et de leurs limites
│   └── processed/                      # Généré par data_pipeline.py — consommé par le dashboard
├── .streamlit/config.toml              # Thème visuel
├── requirements.txt
├── Dockerfile / docker-compose.yml     # Lancement conteneurisé
└── README.md                           # Ce fichier
```

## Choix méthodologiques clés (voir aussi `data/external/README_donnees_externes.md`)

- **Agences unifiées** : le fichier "Agences - Télécom" fourni est en réalité
  la réunion exacte de "Agences - Togocom" + "Agences - Moov" (91 = 62 + 29
  lignes). Il est écarté du pipeline pour éviter un double comptage ; le
  dashboard travaille sur l'union Togocom + Moov.
- **CANAL+** : le fichier fourni est vide (0 ligne). Il est chargé et
  signalé comme tel dans l'application ; en complément, une couche de
  points de vente CANAL+ **externes** (API canalbox.tg + OpenStreetMap,
  ≈ 21 points) est proposée sur la carte (désactivée par défaut).
- **Population** : données officielles RGPH-5 (INSEED Togo, recensement de
  novembre 2022). Les effectifs **par préfecture** (approche directe) sont
  complétés par une désagrégation **par canton** (≈ 339 des 373 cantons,
  soit 5,61 millions d'habitants ; 34 cantons sans effectif publié) issue du
  Livret « Distribution spatiale de la population » et des découpes
  cantonales HDX (nom exact ou rapprochement flou). Les ratios « par
  habitant » sont cadrés et signalés quand le dénominateur est partiel.
- **Limites administratives cantonales** : HDX TGO adm3 (37 préfectures
  multi-polygones), complétées par la table des cantons HDX (373 cantons).
  Les 39 préfectures actuelles sont ramenées à leurs polygones HDX via un
  mapping explicite (ex. « Plaine du Mo » = préfecture « Mô ») — voir le
  détail dans `data/external/README_donnees_externes.md`.
- **Distances réelles à l'équipement** : distance orthodromique (haversine)
  de chaque canton à l'agence opérateur la plus proche, calculée par
  recherche k-d sur sphère (moyenne 17,4 km ; 258 cantons à plus de 10 km,
  ≈ 3,4 M d'habitants).
- **Inégalités de répartition** : courbes de Lorenz et coefficients de Gini
  agences opérateurs (0,38) et agents mobile money (0,31) vs population.
- **Score de priorisation paramétrable** : combinaison pondérée (curseurs
  en tête de la page *Recommandations*) de la démographie, de la
  sous-desserte physique, de l'éloignement moyen et des cantons déjà
  identifiés — chaque composante normalisée en 0-1.
- **Zones blanches** : aucune donnée officielle de couverture réseau
  2G/3G/4G n'est disponible en open data pour le Togo. Le dashboard utilise
  donc un **proxy infrastructure** (absence d'agence physique + faible
  densité d'agents mobile money + éloignement) plutôt qu'une mesure de
  couverture radio réelle. Ce choix est assumé et explicitement affiché
  dans l'application.

## Correspondance avec les critères d'évaluation du challenge

| Critère | Comment il est adressé |
|---|---|
| **C1 — Ergonomie, clarté visuelle, navigation** | Structure multipage claire (Accueil → Cartographie → Mobile money → Zones blanches → Recommandations), KPIs en en-tête, thème visuel cohérent, notes méthodologiques visibles sans encombrer les graphiques. |
| **C2 — Pertinence des analyses, compréhension des données, qualité des conclusions** | Détection et traitement explicite des anomalies du jeu de données (doublon Télécom, CANAL+ vide → couche externe issue de canalbox.tg + OSM), désagrégation de la population RGPH-5 au niveau canton (exact + flou documenté), distances orthodromiques à l'équipement le plus proche, inégalités de répartition (Lorenz/Gini), score de priorisation transparent, pondéré et reproductible en page *Recommandations*. |
| **C3 — Richesse des interactions, filtres, fluidité** | Filtres globaux persistants dans un bandeau horizontal partagé en tête du contenu (région, préfecture, opérateur, statut de desserte, couches dont CANAL+ externe, coloration des cantons), cartes interactives (zoom, survol), tableaux triables, curseurs de pondération du score de priorité, visualisations régionales comparables d'une page à l'autre (mêmes couleurs par région, même tri par population). |
| **C4 — Structure, clarté, méthodologie du rapport** | Les choix méthodologiques et leurs limites sont documentés à trois niveaux : ce README, `data/external/README_donnees_externes.md`, et directement dans l'interface (encadrés d'avertissement contextuels). À reprendre dans le rapport PowerPoint associé. |

## Notes pour aller plus loin (hors délai du challenge)

- Un fichier de population cantonale téléchargeable serait la façon la plus
  simple de consolider les 34 cantons sans effectif publié (repris au
  niveau préfecture dans le dashboard).
- Remplacer le proxy "zones blanches" par une vraie donnée de couverture
  réseau si l'ARCEP Togo venait à la publier, ou en s'appuyant sur
  OpenCelliD (inscription gratuite requise, couverture communautaire à
  vérifier pour le Togo).
