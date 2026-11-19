# Démarrage dans Claude Code

1. Dézippe `radar-marches.zip` à l'endroit de ton choix.
2. Ouvre Claude Code dans le dossier `radar-marches`.
3. Colle le message ci-dessous tel quel.

---

```
Lis CLAUDE.md et README.md : c'est mon dashboard Radar Marchés (7 onglets, données dans data/, mise à jour automatique par scripts/update.py via GitHub Actions).

Aide-moi à le mettre en ligne, étape par étape, en m'expliquant simplement chaque action :
1. Vérifie que tout fonctionne en local : lance `python3 scripts/update.py`, puis `python3 -m http.server 8000`, et dis-moi ce qui a marché ou échoué (Yahoo Finance, CoinGecko, flux RSS). Vérifie en particulier les flux Le Temps et Financial Times de PRESS_FEEDS : s'ils ne répondent pas, trouve les bonnes adresses de flux RSS publics et corrige-les.
2. Crée un dépôt GitHub « radar-marches » (avec gh si disponible, sinon guide-moi), pousse le code.
3. Active GitHub Pages (branche main, dossier racine) et les permissions « Read and write » des Actions.
4. Lance le workflow « Mise à jour Radar Marchés » une première fois et vérifie qu'il a commité de nouvelles données.
5. Donne-moi l'adresse finale de l'app, et explique comment l'ajouter à l'écran d'accueil de mon iPhone.

Ne me demande pas de clé API Claude pour l'instant : je l'ajouterai plus tard si je veux que les textes se réécrivent automatiquement.
```

---

## Ensuite, pour perfectionner l'app

La liste des améliorations prévues est dans `CLAUDE.md` (section « Pistes à faire »). Exemple de demande :

```
Affiche les news (champ news[]) dans l'onglet Synthèse, avec un lien vers chaque article.
```
