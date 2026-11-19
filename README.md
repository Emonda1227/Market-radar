# Radar Marchés

> **Pour commencer : ouvre `DEMARRAGE.md`.**

Dashboard des marchés (indices mondiaux, volatilité, taux, or, crypto, change CHF, contreparties, macro, valeurs stars). Chaque élément a une note 🟢🟠🔴. Les explications en termes simples sont placées juste après chaque tableau.

## Comment ça marche

```
GitHub Actions (toutes les 30 min, en semaine)
   └─ scripts/update.py ─► récupère les cours + news ─► note 🟢🟠🔴 ─► data/latest.json + data/history.json
GitHub Pages
   └─ index.html ─► lit data/*.json à l'ouverture, puis toutes les 5 min
```

Les données sont donc récentes à l'ouverture de l'app, sur téléphone comme sur ordinateur, sans rien demander à personne.

## Mise en ligne (une seule fois)

1. Crée un dépôt GitHub (par ex. `radar-marches`) et pousse ce dossier.
2. **Settings → Pages**: choisis *Deploy from a branch*, puis la branche `main` et le dossier `/ (root)`.
3. **Settings → Actions → General → Workflow permissions**: choisis *Read and write*.
4. Optionnel, pour que les explications soient réécrites automatiquement par Claude : **Settings → Secrets → Actions**, puis ajoute `ANTHROPIC_API_KEY`. Sans ce secret, les chiffres et les notes se mettent à jour, mais les textes restent ceux du dernier relevé.
5. **Actions → Mise à jour Radar Marchés → Run workflow** lance un premier test.

L'adresse sera `https://<ton-compte>.github.io/radar-marches/`. Sur iPhone, ouvre-la dans Safari, puis Partager → *Sur l'écran d'accueil*.

## Sources de données

| Donnée | Source | Clé ? |
|---|---|---|
| Indices, VIX, or, Brent, taux US 10 ans, change | Yahoo Finance (point d'accès non officiel) | non |
| MSCI World / ACWI / EM / USA / Europe | ETF qui les répliquent (URTH, ACWI, EEM, EUSA, IEUR) : ce sont des approximations | non |
| Bitcoin, XRP | CoinGecko | non |
| News | Flux RSS (Yahoo Finance, FXStreet) | non |
| Presse « À la une » | Flux RSS publics Le Temps et Financial Times (titres + liens ; articles FT réservés aux abonnés) | non |
| Explications en français simple | API Claude (optionnel) | oui |

Pas encore automatisés : V2X, Bund et Confédération 10 ans, Bloomberg Global Agg / Commodity, contreparties. Voir `CLAUDE.md`.

## Grilles de notation

| Élément | 🟢 | 🟠 | 🔴 |
|---|---|---|---|
| Indices actions (variation du jour) | > −1 % | −1 à −2 %, ou > +2 % | ≤ −2 % |
| VIX / V2X (niveau) | < 20 | 20–30 | > 30 |
| Or | < ±1,5 % | ±1,5–3 % | ≥ ±3 % |
| Bitcoin | < ±5 % | ±5–10 % | ≥ ±10 % |
| XRP | < ±7 % | ±7–15 % | ≥ ±15 % |
| Change (CHF/EUR, CHF/USD, EUR/USD) | < ±0,5 % | ±0,5–1 % | ≥ ±1 % |
| Taux 10 ans | < 10 pb | 10–20 pb | ≥ 20 pb |
| Brent | < ±2 % | ±2–4 % | ≥ ±4 % |
| Bloomberg Global Agg | < ±0,3 % | ±0,3–0,7 % | ≥ ±0,7 % |
| Bloomberg Commodity | < ±1,5 % | ±1,5–3 % | ≥ ±3 % |
| News, contreparties, macro | appréciation qualitative | | |

## Tester en local

```bash
pip install requests
python scripts/update.py           # met à jour data/
python -m http.server 8000         # puis ouvre http://localhost:8000
```

Information de marché uniquement, ce n'est pas un conseil en investissement.
