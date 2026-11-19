#!/usr/bin/env python3
"""Radar Marchés – mise à jour automatique des données.

Lancé par GitHub Actions (.github/workflows/update.yml), toutes les 30 min en semaine.
1. Récupère les cours (Yahoo Finance, sans clé) et les cryptos (CoinGecko, sans clé).
2. Applique les grilles de notation 🟢🟠🔴 (voir RULES plus bas).
3. Récupère les titres de news (flux RSS).
4. Optionnel : si ANTHROPIC_API_KEY est défini, demande à Claude de réécrire
   le titre du jour, « L'essentiel » et les explications en termes simples.
5. Écrit data/latest.json et ajoute le relevé à data/history.json (60 derniers).

Seule dépendance : requests (pip install requests).
"""
import json, os, re, sys, datetime as dt
from zoneinfo import ZoneInfo
from xml.etree import ElementTree as ET
import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
TZ = ZoneInfo("Europe/Zurich")
UA = {"User-Agent": "Mozilla/5.0 (RadarMarches; +https://github.com)"}

# id du dashboard -> symbole Yahoo Finance
YAHOO = {
    "es50": "^STOXX50E", "stoxx600": "^STOXX", "smi": "^SSMI", "dax": "^GDAXI",
    "cac": "^FCHI", "ftse": "^FTSE", "mib": "FTSEMIB.MI", "ibex": "^IBEX",
    "spx": "^GSPC", "dow": "^DJI", "nasdaq": "^IXIC", "r2k": "^RUT",
    "nikkei": "^N225", "kospi": "^KS11", "hsi": "^HSI", "shanghai": "000001.SS", "sensex": "^BSESN",
    # Les indices MSCI/FTSE ne sont pas publics : on suit des ETF qui les répliquent (proxy).
    "msci_world": "URTH", "acwi": "ACWI", "msci_em": "EEM", "msci_usa": "EUSA", "msci_eu": "IEUR",
    "vix": "^VIX",
    "gold": "GC=F", "brent": "BZ=F", "ust10": "^TNX",
    "chfeur": "CHFEUR=X", "chfusd": "CHFUSD=X", "eurusd": "EURUSD=X",
}
COINGECKO = {"btc": "bitcoin", "xrp": "ripple"}

# Flux RSS de news (titres seulement). Ajoute/retire librement.
RSS = [
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=^GSPC,^STOXX,^SSMI&region=US&lang=en-US",
    "https://www.fxstreet.com/rss/news",
]

# Presse « À la une » : flux RSS publics (titres + lien uniquement).
# URL à vérifier au premier lancement (les journaux changent parfois leurs adresses de flux).
PRESS_FEEDS = [
    ("Le Temps", "https://www.letemps.ch/articles.rss"),
    ("Le Temps", "https://www.letemps.ch/economie.rss"),
    ("Financial Times", "https://www.ft.com/markets?format=rss"),
    ("Financial Times", "https://www.ft.com/rss/home/international"),
]
PRESS_PER_SOURCE = 5

# ---------- grilles de notation (identiques aux alertes) ----------
def sym(d, a, b):
    if d is None: return "n"
    return "r" if abs(d) >= b else "o" if abs(d) >= a else "g"

def r_index(d):
    if d is None: return "n"
    return "r" if d <= -2 else "o" if d <= -1 or d > 2 else "g"

def r_vol(level):
    if level is None: return "n"
    return "g" if level < 20 else "o" if level <= 30 else "r"

RULES = {
    "index": r_index,
    "vol": lambda lvl, d: r_vol(lvl),
    "gold": lambda d: sym(d, 1.5, 3), "btc": lambda d: sym(d, 5, 10), "xrp": lambda d: sym(d, 7, 15),
    "fx": lambda d: sym(d, 0.5, 1), "brent": lambda d: sym(d, 2, 4),
    "rate_bp": lambda bp: sym(bp, 10, 20),
}

# ---------- récupération ----------
def yahoo(sym_):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{requests.utils.quote(sym_)}?range=1d&interval=1h"
    try:
        m = requests.get(url, headers=UA, timeout=15).json()["chart"]["result"][0]["meta"]
        last = m.get("regularMarketPrice")
        prev = m.get("chartPreviousClose") or m.get("previousClose")
        d = (last / prev - 1) * 100 if last and prev else None
        return {"last": last, "prev": prev, "d": d}
    except Exception as e:
        print(f"  ! {sym_}: {e}", file=sys.stderr)
        return None

def yahoo_perf(sym_):
    """Cours, variation du jour, 1 semaine (5 séances), 1 an et depuis janvier, à partir d'un an d'historique."""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{requests.utils.quote(sym_)}?range=1y&interval=1d"
    try:
        res = requests.get(url, headers=UA, timeout=15).json()["chart"]["result"][0]
        m, ts = res["meta"], res.get("timestamp") or []
        closes = res["indicators"]["quote"][0]["close"]
        pts = [(t, c) for t, c in zip(ts, closes) if c is not None]
        last = m.get("regularMarketPrice") or (pts[-1][1] if pts else None)
        if not pts or last is None:
            return None
        # Une seule séance (nouvelle cotation) : on compare au cours de référence fourni par Yahoo (prix d'introduction).
        prev = pts[-2][1] if len(pts) > 1 else m.get("chartPreviousClose")
        week = pts[-6][1] if len(pts) > 5 else None
        # Moins d'un an d'historique (cotation récente) : pas de performance 1 an ni depuis janvier.
        year = pts[0][1] if len(pts) > 200 else None
        y0 = dt.datetime.now(TZ).year
        started_before = dt.datetime.fromtimestamp(pts[0][0], TZ).year < y0
        jan = next((c for t, c in pts if dt.datetime.fromtimestamp(t, TZ).year == y0), None) if started_before else None
        pc = lambda a: round((last / a - 1) * 100, 2) if a else None
        hi = max(c for _, c in pts)
        return {"last": last, "d": pc(prev), "w": pc(week), "y": pc(year), "ytd": pc(jan), "fromHigh": pc(hi)}
    except Exception as e:
        print(f"  ! perf {sym_}: {e}", file=sys.stderr)
        return None

def coingecko():
    ids = ",".join(COINGECKO.values())
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd&include_24hr_change=true"
    try:
        j = requests.get(url, headers=UA, timeout=15).json()
        return {k: {"last": j[v]["usd"], "d": j[v].get("usd_24h_change")} for k, v in COINGECKO.items() if v in j}
    except Exception as e:
        print(f"  ! coingecko: {e}", file=sys.stderr)
        return {}

def press():
    """Derniers titres Le Temps et FT. Retourne [] si aucun flux ne répond."""
    by_src = {}
    for src, url in PRESS_FEEDS:
        if len(by_src.get(src, [])) >= PRESS_PER_SOURCE:
            continue
        try:
            root = ET.fromstring(requests.get(url, headers=UA, timeout=15).content)
            for it in root.iter("item"):
                t = (it.findtext("title") or "").strip()
                if not t:
                    continue
                lst = by_src.setdefault(src, [])
                if len(lst) >= PRESS_PER_SOURCE or any(x["t"] == t for x in lst):
                    continue
                desc = re.sub("<[^>]+>", "", it.findtext("description") or "").strip()
                lst.append({"src": src, "r": "n", "t": t, "why": desc[:180], "url": it.findtext("link"),
                            "date": (it.findtext("pubDate") or "")[:16]})
        except Exception as e:
            print(f"  ! presse {url}: {e}", file=sys.stderr)
    return [x for lst in by_src.values() for x in lst]

RSS_NAMES = {"feeds.finance.yahoo.com": "Yahoo Finance", "www.fxstreet.com": "FXStreet"}

def news(per_source=5):
    """Derniers titres de chaque flux RSS, mélangés (une source après l'autre)."""
    lists = []
    for url in RSS:
        host = url.split("/")[2]
        lst = []
        try:
            root = ET.fromstring(requests.get(url, headers=UA, timeout=15).content)
            for it in root.iter("item"):
                t = (it.findtext("title") or "").strip()
                if t and len(lst) < per_source and all(x["t"] != t for x in lst):
                    lst.append({"t": t, "link": it.findtext("link"), "src": RSS_NAMES.get(host, host),
                                "date": (it.findtext("pubDate") or "")[:16], "r": "n", "why": ""})
        except Exception as e:
            print(f"  ! rss {url}: {e}", file=sys.stderr)
        lists.append(lst)
    out = []
    for i in range(per_source):
        out += [lst[i] for lst in lists if i < len(lst)]
    return out

# ---------- formatage FR ----------
def fr(v, n=2):
    return f"{v:,.{n}f}".replace(",", " ").replace(".", ",") if v is not None else "n.d."

def frp(v):
    if v is None: return "n.d."
    return ("+" if v > 0 else "−" if v < 0 else "") + fr(abs(v)) + " %"

# ---------- construction du relevé ----------
def build(prev):
    s = json.loads(json.dumps(prev))  # copie : on garde textes, drapeaux, horaires, portée
    now = dt.datetime.now(TZ)
    s["ts"] = now.isoformat(timespec="minutes")
    s["id"] = now.strftime("%Y-%m-%d-%H%M")
    s["edition"] = "Matin" if now.hour < 11 else "Midi" if now.hour < 15 else "Après-midi" if now.hour < 19 else "Soir"

    q = {k: yahoo(v) for k, v in YAHOO.items()}
    q.update(coingecko())
    stamp = now.strftime("%Hh%M")

    for g in s.get("indices", []):
        for r in g["rows"]:
            x = q.get(r["id"])
            if x and x.get("last") is not None:
                r["last"], r["d"], r["r"] = round(x["last"], 2), round(x["d"], 2) if x["d"] is not None else None, r_index(x["d"])
        g["asof"] = f"Mise à jour auto {stamp} (Genève)"

    for r in s.get("vol", {}).get("rows", []):
        x = q.get(r["id"])
        if x and x.get("last") is not None:
            r["last"], r["d"], r["r"] = round(x["last"], 2), round(x["d"], 2) if x["d"] is not None else None, r_vol(x["last"])

    for r in s.get("rates", {}).get("rows", []):
        x = q.get(r["id"])
        if not x or x.get("last") is None: continue
        if r["id"] == "ust10":
            bp = (x["last"] - x["prev"]) * 100 if x.get("prev") else None
            r["value"], r["d"], r["r"] = fr(x["last"]) + " %", (f"{bp:+.0f} pb".replace("-", "−") if bp is not None else "n.d."), RULES["rate_bp"](bp)
        elif r["id"] == "brent":
            r["value"], r["d"], r["r"] = fr(x["last"], 1) + " $", frp(x["d"]), RULES["brent"](x["d"])

    a = s.get("assets", {})
    for r in a.get("gold", {}).get("rows", []):
        x = q.get("gold")
        if x and x.get("last"):
            r.update(last=round(x["last"]), value=f"≈ {fr(x['last'], 0)} $ / once", d=frp(x["d"]), r=RULES["gold"](x["d"]), sub="contrat à terme")
    for r in a.get("crypto", {}).get("rows", []):
        x = q.get(r["id"])
        if x and x.get("last"):
            n = 0 if r["id"] == "btc" else 3
            r.update(last=x["last"], value=f"≈ {fr(x['last'], n)} $", d=frp(x["d"]) + " (24 h)", r=RULES[r["id"]](x["d"]), sub="")
    for r in a.get("fx", {}).get("rows", []):
        x = q.get(r["id"])
        if x and x.get("last"):
            base, quote = r["name"].split("/")
            names = {"CHF": "franc", "EUR": "euro", "USD": "dollar"}
            r.update(last=round(x["last"], 4), value=fr(x["last"], 4), d=frp(x["d"]), r=RULES["fx"](x["d"]),
                     sub=f"1 {names[base]} = {fr(x['last'], 4)} {names[quote]}")

    # Valeurs stars : chaque ligne porte son symbole Yahoo dans "yahoo" ; jour, 1 semaine, 1 an, depuis janvier, écart au plus haut sur 1 an
    for g in s.get("stars", {}).get("groups", []):
        for r in g["rows"]:
            sy = r.get("yahoo")
            x = yahoo_perf(sy) if sy else None
            if x:
                r.update(last=round(x["last"], 2), d=x["d"], w=x["w"], y=x["y"], ytd=x["ytd"], fromHigh=x["fromHigh"], r=sym(x["d"], 3, 6))
                if x["w"] is not None:  # garde la mention « nouvelle cotation » tant qu'il n'y a pas d'historique
                    r.pop("sub", None)
        g["asof"] = f"Mise à jour auto {stamp} (Genève)"

    p = press()
    if p:
        s["press"] = {"asof": f"Mise à jour auto {stamp} (Genève)", "items": p,
                      "note": (s.get("press") or {}).get("note", "Titres repris des flux publics avec lien vers l'article ; la lecture complète peut nécessiter un abonnement.")}

    headlines = news()
    if headlines:
        s["news"] = headlines

    # niveau global = la pire note parmi les chiffres
    rated = [r["r"] for g in s.get("indices", []) for r in g["rows"]] + [r["r"] for r in s.get("vol", {}).get("rows", [])]
    rated += [r["r"] for k in ("gold", "crypto", "fx") for r in a.get(k, {}).get("rows", [])]
    s["overall"] = "r" if rated.count("r") >= 3 else "o" if "r" in rated or rated.count("o") >= 2 else "g"

    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            s = explain(s)
        except Exception as e:
            print(f"  ! claude: {e}", file=sys.stderr)
    return s

def explain(s):
    """Réécrit headline / bref / notes en français simple (optionnel)."""
    keys = ["headline", "bref", "risk"]
    notes = {g["id"]: g["note"] for g in s["indices"]}
    payload = {"indices": s["indices"], "vol": s["vol"], "rates": s["rates"], "assets": s["assets"], "news": s.get("news", []),
               "stars": s.get("stars"), "cro": s.get("cro"), "press": s.get("press")}
    prompt = (
        "Tu rédiges un tableau de bord marchés pour un lecteur à Genève, non expert en investissement. "
        "Français simple, phrases courtes, pas de jargon sans explication, aucune recommandation d'investissement. "
        "À partir des données JSON ci-dessous, renvoie UNIQUEMENT un JSON avec : "
        '"headline" (1-2 phrases), "bref" (3 à 5 objets {"r":"g|o|r","t":titre court,"why":1 phrase}), '
        '"risk" (1-2 phrases), "notes" (objet id_groupe -> 2-3 phrases expliquant le tableau), '
        '"vol_note", "gold_note", "crypto_note", "fx_note" (2 phrases chacun), '
        '"news_items" (liste dans le même ordre que news : {"r":"g|o|r","why":1 phrase simple en français résumant la news et son importance}), '
        '"press_items" (liste dans le même ordre que press.items : {"r":"g|o|r","why":1 phrase simple sur pourquoi c\'est important pour un risk manager}), '
        '"stars_notes" (objet id_groupe_stars -> 2 phrases), '
        '"stars_outlook" (objet id_action -> {"tone":"Positif|Neutre|Prudent","text":1-2 phrases sur la tendance à court terme d\'après les chiffres et l\'actualité, sans recommandation}), '
        '"cro" (même structure que le bloc cro reçu : summary, stress[{r,t,why,action}], escalate[{r,t,why,action}], '
        "emerging[{r,t,why,horizon}], notes{stress,escalate,emerging} ; vue Chief Risk Officer d'un gestionnaire d'actifs, "
        'mise à jour selon les données et les news, en gardant les points toujours valables). '
        "Les notes r/g/o sont déjà calculées : garde-les. Données :\n" + json.dumps(payload, ensure_ascii=False)
    )
    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": os.environ["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01", "content-type": "application/json"},
        json={"model": os.environ.get("CLAUDE_MODEL", "claude-haiku-5-5"), "max_tokens": 6000,
              "messages": [{"role": "user", "content": prompt}]},
        timeout=60,
    ).json()
    text = resp["content"][0]["text"]
    j = json.loads(re.search(r"\{.*\}", text, re.S).group(0))
    for k in keys:
        if k in j: s[k] = j[k]
    for g in s["indices"]:
        g["note"] = j.get("notes", {}).get(g["id"], g["note"])
    s["vol"]["note"] = j.get("vol_note", s["vol"]["note"])
    for k in ("gold", "crypto", "fx"):
        s["assets"][k]["note"] = j.get(f"{k}_note", s["assets"][k]["note"])
    for g in s.get("stars", {}).get("groups", []):
        g["note"] = j.get("stars_notes", {}).get(g["id"], g["note"])
        for r in g["rows"]:
            o = j.get("stars_outlook", {}).get(r["id"])
            if isinstance(o, dict) and o.get("text"):
                r["outlook"] = {"tone": o.get("tone", "Neutre"), "text": o["text"]}
    if isinstance(j.get("news_items"), list):
        for it, x in zip(s.get("news", []), j["news_items"]):
            if isinstance(x, dict):
                it["r"] = x.get("r", it.get("r", "n")); it["why"] = x.get("why", it.get("why", ""))
    if s.get("press") and isinstance(j.get("press_items"), list):
        for it, x in zip(s["press"]["items"], j["press_items"]):
            if isinstance(x, dict):
                it["r"] = x.get("r", it["r"]); it["why"] = x.get("why", it["why"])
    if isinstance(j.get("cro"), dict) and s.get("cro"):
        for k in ("summary", "stress", "escalate", "emerging", "notes"):
            if j["cro"].get(k): s["cro"][k] = j["cro"][k]
        s["cro"]["asof"] = s["ts"]
    return s

def main():
    prev = json.load(open(os.path.join(DATA, "latest.json"), encoding="utf-8"))
    s = build(prev)
    json.dump(s, open(os.path.join(DATA, "latest.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    hp = os.path.join(DATA, "history.json")
    hist = json.load(open(hp, encoding="utf-8")) if os.path.exists(hp) else []
    hist = [s] + [h for h in hist if h.get("id") != s["id"]]
    json.dump(hist[:60], open(hp, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"OK {s['id']} niveau={s['overall']}")

if __name__ == "__main__":
    main()
