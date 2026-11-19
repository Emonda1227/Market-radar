# Radar Marchés : notes pour Claude Code

## Utilisateur
Basé à Genève, pas expert en investissement : il veut des textes en français simple. Chaque explication va **juste après le tableau** qu'elle commente, jamais regroupée à la fin. Le change se lit côté franc (CHF/EUR, CHF/USD).

## Fichiers
- `index.html` : application complète (HTML, CSS et JS dans un seul fichier, sans dépendance).
  - Elle embarque un relevé de secours (`FALLBACK`), puis charge `data/history.json` et `data/latest.json` (`loadData()`). Le rechargement se fait toutes les 5 min et au retour sur l'onglet.
  - Onglets (7) : synthese, indices, volatilite, actifs, stars, risques, horaires.
  - `S.stars` (onglet Stars) : `{featured{r,title,text}, groups[{id,title,asof,note,full,rows[{id,r,flag,name,ticker,yahoo,last,cur,d,w,y,ytd,fromHigh,scope,sub,outlook{tone,text}}]}], disclaimer, sources}`. Grille actions seules : 🟢 < ±3 %, 🟠 ±3–6 %, 🔴 ≥ ±6 %. update.py met à jour chaque ligne via son symbole `yahoo` (`yahoo_perf` : jour, 1 semaine = 5 séances, 1 an, depuis janvier, écart au plus haut 1 an). `outlook.tone` ∈ Positif/Neutre/Prudent, réécrit par Claude si la clé API est présente.
  - `S.press` (bloc « À la une : Le Temps & Financial Times » dans Synthèse) : `{asof, items[{src,r,t,why,url,date}], note}`. Rempli par `press()` dans update.py depuis `PRESS_FEEDS` (flux RSS publics, titres + liens uniquement). **URL des flux à vérifier au premier lancement.** Le FT est payant : on n'affiche que titre + lien.
  - `S.cro` (onglet Risques, vue CRO) : `{summary, stress[{r,t,why,action}], escalate[{r,t,why,action}], emerging[{r,t,why,horizon}], notes{stress,escalate,emerging}, disclaimer, sources}`. update.py le recopie tel quel ; à régénérer via Claude (explain) pour rester à jour.
  - `EXCH` (onglet Horaires) : horaires locaux officiels + fuseau IANA ; la conversion en heure de Genève et les changements d'heure sont calculés en JS (`tzOff`, `at`). Jours fériés non gérés (piste : ajouter une liste par bourse).
  - Habillages via `data-skin` et mises en page iPhone/iPad via `data-layout`, enregistrés dans localStorage.
  - Les compteurs 🟢🟠🔴 sont cliquables et filtrent les éléments (`FILTER`).
  - `INV` contient vix et v2x : pour eux, une hausse s'affiche en rouge.
  - L'état ouvert/fermé est calculé en direct à l'heure de Genève, à partir de `open` et `close`.
- `scripts/update.py` : récupère les données, applique les notes et écrit `data/`. Il part du relevé précédent : seuls les chiffres et les notes changent, et les textes aussi si `ANTHROPIC_API_KEY` est défini.
- `.github/workflows/update.yml` : lance la mise à jour toutes les 30 min en semaine.

## Schéma d'un relevé (`data/latest.json`)
- `id`, `ts` (ISO avec fuseau), `edition`, `overall` (g/o/r), `headline`, `bref[]`.
- `indices[]` : groupes `{id, title, asof, note, rows[{id, r, flag, name, last, d, w, ytd, open, close, scope}]}`.
- `vol`, `rates`, `assets.gold`, `assets.crypto`, `assets.fx` : `{rows, note}`.
- `derives[]`, `counterparty[]`, `macro{rows, agenda, note}`, `risk`, `lexique[]`, `sources[]`.
- `news[]` (`{t, link, src}`) : ajouté par update.py, **pas encore affiché dans l'UI**.
- Les notes `r` valent `g`, `o`, `r` ou `n` (pas de donnée).

## Pistes à faire
1. Afficher `news[]` dans l'onglet Synthèse (titre et lien, note 🟢🟠🔴 si Claude est actif).
2. Ajouter V2X (pas sur Yahoo : chercher une source), Bund 10 ans (`^DE10Y` ?), Confédération 10 ans (SNB data portal) et les indices Bloomberg.
3. Calculer `w` (5 jours) et `ytd` avec `range=ytd` sur Yahoo.
4. Alertes urgentes : en cas de note rouge, envoyer une notification (ntfy.sh ou Pushover) depuis le workflow.
5. Rendre `asof` plus précis par marché (clôture ou en séance).
6. Yahoo est un point d'accès non officiel : prévoir une solution de repli (Twelve Data, Finnhub, Alpha Vantage avec clé dans les secrets GitHub).

## Confidentialité
Le dépôt et le site sont publics : ne jamais y mettre le nom de l'utilisateur, de son employeur ou de produits liés à son employeur.
