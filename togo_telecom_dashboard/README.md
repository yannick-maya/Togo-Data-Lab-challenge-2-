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

## Structure du projet

```
togo_telecom_dashboard/
├── app.py                              # Page d'accueil (Vue d'ensemble)
├── pages/                              # Pages additionnelles du dashboard (multipage Streamlit)
│   ├── 1_🗺️_Cartographie_Infrastructures.py
│   ├── 2_📱_Mobile_Money_vs_Population.py
│   ├── 3_📡_Zones_Blanches.py
│   └── 4_💡_Recommandations.py
├── src/
│   ├── data_pipeline.py                # Nettoyage + calcul des indicateurs (à lancer une fois)
│   ├── data_loader.py                  # Chargement des données préparées, avec cache Streamlit
│   └── utils.py                        # Fonctions utilitaires (parsing WKT, mapping préfectures)
├── data/
│   ├── raw/                            # Fichiers bruts fournis pour le challenge (inchangés)
│   ├── external/                       # Données externes sourcées (population, limites admin.)
│   │   └── README_donnees_externes.md  # Détail des sources et de leurs limites
│   └── processed/                      # Généré par data_pipeline.py — consommé par le dashboard
├── .streamlit/config.toml              # Thème visuel
├── requirements.txt
└── README.md                           # Ce fichier
```

## Choix méthodologiques clés (voir aussi `data/external/README_donnees_externes.md`)

- **Agences unifiées** : le fichier "Agences - Télécom" fourni est en réalité
  la réunion exacte de "Agences - Togocom" + "Agences - Moov" (91 = 62 + 29
  lignes). Il est écarté du pipeline pour éviter un double comptage ; le
  dashboard travaille sur l'union Togocom + Moov.
- **CANAL+** : le fichier fourni est vide (0 ligne). Il est chargé et
  signalé comme tel dans l'application plutôt qu'ignoré silencieusement.
- **Population** : donnée officielle par préfecture, RGPH-5 (INSEED Togo,
  recensement de novembre 2022). Non disponible au niveau canton dans le
  temps imparti au challenge — les ratios "par habitant" sont donc calculés
  au niveau préfecture uniquement.
- **Limites administratives** : geoBoundaries.org (CC BY 4.0), niveau
  préfecture (37 polygones). Le Togo comptant aujourd'hui 39 préfectures,
  3 préfectures issues de scissions récentes (Agoè-Nyivé, Kpendjal-Ouest,
  Oti-Sud) sont regroupées avec leur préfecture d'origine pour la
  cartographie — voir le détail dans `data/external/README_donnees_externes.md`.
- **Zones blanches** : aucune donnée officielle de couverture réseau
  2G/3G/4G n'est disponible en open data pour le Togo. Le dashboard utilise
  donc un **proxy infrastructure** (absence d'agence physique + faible
  densité d'agents mobile money) plutôt qu'une mesure de couverture radio
  réelle. Ce choix est assumé et explicitement affiché dans l'application.

## Correspondance avec les critères d'évaluation du challenge

| Critère | Comment il est adressé |
|---|---|
| **C1 — Ergonomie, clarté visuelle, navigation** | Structure multipage claire (Accueil → Cartographie → Mobile money → Zones blanches → Recommandations), KPIs en en-tête, thème visuel cohérent, notes méthodologiques visibles sans encombrer les graphiques. |
| **C2 — Pertinence des analyses, compréhension des données, qualité des conclusions** | Détection et traitement explicite des anomalies du jeu de données (doublon Télécom, CANAL+ vide), croisement infrastructure × population × territoire, score de priorisation transparent et reproductible en page *Recommandations*. |
| **C3 — Richesse des interactions, filtres, fluidité** | Filtres région / préfecture / opérateur / couches sur la carte, cartes interactives (zoom, survol), tableaux triables, sélection dynamique du nombre de résultats affichés. |
| **C4 — Structure, clarté, méthodologie du rapport** | Les choix méthodologiques et leurs limites sont documentés à trois niveaux : ce README, `data/external/README_donnees_externes.md`, et directement dans l'interface (encadrés d'avertissement contextuels). À reprendre dans le rapport PowerPoint associé. |

## Notes pour aller plus loin (hors délai du challenge)

- Compléter la population au niveau canton (les données existent dans le
  Livret RGPH-5 "Distribution spatiale de la population" de l'INSEED, mais
  n'ont pas été transcrites intégralement faute de temps).
- Remplacer le proxy "zones blanches" par une vraie donnée de couverture
  réseau si l'ARCEP Togo venait à la publier, ou en s'appuyant sur
  OpenCelliD (inscription gratuite requise, couverture communautaire à
  vérifier pour le Togo).
