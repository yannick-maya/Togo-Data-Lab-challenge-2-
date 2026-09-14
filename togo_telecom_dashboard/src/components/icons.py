"""
Bibliothèque d'icônes SVG en ligne fine (style Lucide/Phosphor).

Une seule famille de style dans toute l'application : trait ``stroke``
uniforme (1.6), géométrie 24x24, couleur héritée du contexte via
``currentColor``. Aucun émoji n'est utilisé comme icône ; passer ici pour
les en-têtes de page, la marque plutôt que par des caractères Unicode.
"""

_FILL_SPEC = "fill:none;stroke:currentColor;stroke-width:1.6;stroke-linecap:round;stroke-linejoin:round;"

_PATHS: dict[str, str] = {
    "radar": (
        '<path d="M19.07 4.93A10 10 0 0 0 6.99 3.34"/>'
        '<path d="M4 6h.01"/>'
        '<path d="M2.29 9.62A10 10 0 1 0 21.71 8.34"/>'
        '<path d="M16.24 7.76A6 6 0 1 0 8.23 16.67"/>'
        '<path d="M12 18h.01"/>'
        '<path d="M17.99 11.66A6 6 0 0 1 15.77 16.67"/>'
        '<circle cx="12" cy="12" r="2"/>'
        '<path d="m13.41 10.59 5.66-5.66"/>'
    ),
    "map": (
        '<path d="M14.106 5.553a2 2 0 0 0 1.788 0l3.659-1.83A1 1 0 0 1 21 '
        '4.619v12.764a1 1 0 0 1-.553.894l-4.553 2.277a2 2 0 0 1-1.788 0l-4.212-2.106'
        'a2 2 0 0 0-1.788 0l-3.659 1.83A1 1 0 0 1 3 19.381V6.618a1 1 0 0 1'
        '.553-.894l4.553-2.277a2 2 0 0 1 1.788 0z"/>'
        '<path d="M15 5.764v15"/>'
        '<path d="M9 3.236v15"/>'
    ),
    "wallet": (
        '<path d="M19 7V4a1 1 0 0 0-1-1H5a2 2 0 0 0 0 4h15a1 1 0 0 1 1 1v4h-3a2 2 0 0 0 0 '
        '4h3a1 1 0 0 0 1-1v-2a1 1 0 0 0-1-1"/>'
        '<path d="M3 5v14a2 2 0 0 0 2 2h15a1 1 0 0 0 1-1v-4"/>'
    ),
    "activity": (
        '<path d="M22 12h-2.48a2 2 0 0 0-1.93 1.46l-2.35 8.36a.25.25 0 0 1-.48 0'
        'L9.24 2.18a.25.25 0 0 0-.48 0l-2.35 8.36A2 2 0 0 1 4.49 12H2"/>'
    ),
    "target": (
        '<circle cx="12" cy="12" r="10"/>'
        '<circle cx="12" cy="12" r="6"/>'
        '<circle cx="12" cy="12" r="2"/>'
    ),
    "funnel": (
        '<path d="M3 5h18l-7 8v5l-4 2v-7z"/>'
    ),
    "reset": (
        '<path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/>'
        '<path d="M3 3v5h5"/>'
    ),
}


def svg(name: str, size: int = 18, cls: str = "") -> str:
    """Retourne le SVG inline d'une icône (ligne fine, couleur héritée)."""
    if name not in _PATHS:
        raise KeyError(f"Icône inconnue : {name}")
    attr = f' class="{cls}"' if cls else ""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
        f'viewBox="0 0 24 24" style="{_FILL_SPEC}"{attr} aria-hidden="true">'
        f"{_PATHS[name]}</svg>"
    )