import requests
import random
import re
import string
from bs4 import BeautifulSoup
from collections import Counter

# --- CONFIGURATION THÈMES ---
THEMES_DEFINITIONS = {
    "IMMIGRATION & FRONTIÈRES": ["immigration", "immigré", "migrant", "frontière", "clandestin", "sans-papiers", "expulsion", "oqtf", "visa", "intégration", "étranger", "flux", "asile"],
    "SÉCURITÉ & JUSTICE": ["sécurité", "insécurité", "police", "policier", "gendarme", "justice", "prison", "délinquance", "criminel", "violence", "ordre", "sanction", "peine", "drogue"],
    "ÉCONOMIE & POUVOIR D'ACHAT": ["économie", "impôt", "taxe", "tva", "pouvoir d'achat", "salaire", "smic", "retraite", "dette", "déficit", "budget", "inflation", "prix", "euro", "entreprise"],
    "TRAVAIL & EMPLOI": ["travail", "emploi", "chômage", "chômeur", "salarié", "patron", "embauche", "licenciement", "carrière", "métier", "formation"],
    "ÉCOLOGIE & ÉNERGIE": ["écologie", "climat", "environnement", "biodiversité", "énergie", "nucléaire", "renouvelable", "carbone", "pollution", "agriculteur", "agriculture"],
    "SANTÉ & SOCIAL": ["santé", "hôpital", "médecin", "soin", "urgence", "sécu", "social", "solidarité", "handicap", "rsa", "aides", "logement"],
    "ÉDUCATION & FAMILLE": ["école", "collège", "lycée", "université", "professeur", "enseignant", "éducation", "famille", "enfant", "natalité"],
    "SOUVERAINETÉ & INSTITUTIONS": ["souveraineté", "nation", "patrie", "peuple", "référendum", "démocratie", "constitution", "liberté", "république", "laïcité"],
    "EUROPE & INTERNATIONAL": ["europe", "européen", "ue", "bruxelles", "commission", "international", "diplomatie", "guerre", "armée", "défense", "otan"]
}

STOPWORDS = {"le", "la", "les", "de", "des", "du", "un", "une", "au", "aux", "ce", "cet", "cette", "ces", "je", "tu", "il", "elle", "on", "nous", "vous", "ils", "elles", "mais", "ou", "et", "donc", "or", "ni", "car", "que", "qui", "quoi", "dont", "où", "pour", "par", "dans", "sur", "avec", "sans", "vers", "être", "avoir", "faire", "plus", "moins", "très", "bien", "tout", "tous", "toute", "toutes", "ne", "pas", "y", "en", "a", "est", "votre", "notre", "leur", "nos", "vos", "leurs"}
EXCLUDE = {"macron", "mélenchon", "melenchon", "pen", "marine", "france", "français", "rassemblement", "national", "insoumise", "parti", "socialiste", "républicains", "renaissance", "bardella", "attal", "politique", "programme"}

def get_text(url):
    if "demo" in url: return "Texte de démo."
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer"]): tag.decompose()
        return re.sub(r"\s+", " ", soup.get_text(" "))
    except: return None

def clean_tokens(txt):
    txt = txt.lower().translate(str.maketrans("", "", string.punctuation))
    return [t for t in txt.split() if len(t) > 3 and t not in STOPWORDS and t not in EXCLUDE]

def get_sentences_for_theme(txt, keywords, max_ex=8):
    sentences = re.split(r'(?<=[\.\?\!])\s+', txt)
    examples = []
    pattern = r"\b(" + "|".join([re.escape(k) for k in keywords]) + r")\b"
    for s in sentences:
        if re.search(pattern, s.lower()):
            s = s.strip()
            if 30 < len(s) < 300 and s not in examples:
                examples.append(s)
            if len(examples) >= max_ex: break
    return examples

def scrape_political_site(url):
    full_text = get_text(url)
    if not full_text: return None 
    tokens = clean_tokens(full_text)
    scores = {t: 0 for t in THEMES_DEFINITIONS}
    for tok in tokens:
        for theme, kws in THEMES_DEFINITIONS.items():
            if any(tok.startswith(k) for k in kws):
                scores[theme] += 1
                break
    sorted_themes = sorted([(k, v) for k, v in scores.items() if v > 0], key=lambda x: x[1], reverse=True)
    results = []
    for th, sc in sorted_themes:
        sents = get_sentences_for_theme(full_text, THEMES_DEFINITIONS[th])
        if sents: results.append((th, sc, sents))
    return results

def generate_bd_prompt_logic(
    party_name,
    analysis_results,
    angle_satirique="",
    max_quotes=60,
    seed=None
):
    """
    Prompt BD satirique + caricatural (gros nez, couleurs vives),
    avec sélection aléatoire et équilibrée des phrases extraites.
    
    analysis_results: liste de tuples (theme, score, [phrases])
    """
    import random

    if seed is not None:
        random.seed(seed)

    # --- 1) Construire une pool de phrases par thème ---
    pools = []
    for (theme, score, phrases) in (analysis_results or []):
        clean_phrases = []
        for p in (phrases or []):
            if isinstance(p, str):
                s = p.strip()
                if s:
                    clean_phrases.append(s)
        if clean_phrases:
            random.shuffle(clean_phrases)
            pools.append((theme, score, clean_phrases))

    if not pools:
        return "Impossible de générer un prompt : aucune phrase n'a été extraite."

    # --- 2) Sélection aléatoire mais équilibrée entre thèmes (round-robin) ---
    pools_sorted = sorted(pools, key=lambda x: x[1], reverse=True)

    selected = []
    idx = 0
    while len(selected) < max_quotes and any(len(p[2]) > 0 for p in pools_sorted):
        theme, score, ph = pools_sorted[idx % len(pools_sorted)]
        if ph:
            selected.append((theme, ph.pop(0)))
        idx += 1

    # Thèmes dominants (affichage)
    top_themes = [t for (t, _, _) in pools_sorted][:8]

    # --- 3) Prompt "satire claire + style BD fort" ---
    prompt = ""
    prompt += "Génère UNE SEULE IMAGE : une planche de BANDE DESSINÉE satirique en français.\n"
    prompt += "But : se MOQUER du parti/courant politique ci-dessous et de sa communication (langue de bois, promesses vagues, contradictions, posture morale, éléments de com').\n"
    prompt += "Satire : piquante, absurde, ironique, avec une vraie moquerie visible (sans insultes gratuites).\n"
    prompt += "Règles de sécurité : pas de haine, pas de propos violents, pas d’attaques sur des caractéristiques protégées. On se moque des idées et du storytelling politique.\n\n"

    prompt += f"Parti / courant : {party_name}\n"
    if angle_satirique:
        prompt += f"Angle satirique (priorité) : {angle_satirique}\n"
    prompt += "\n"

    # Style visuel très BD / caricature
    prompt += "STYLE VISUEL OBLIGATOIRE (TRÈS BD) :\n"
    prompt += "- Bande dessinée franco-belge / presse satirique.\n"
    prompt += "- Caricature assumée : gros nez, mentons exagérés, mimiques énormes, postures théâtrales.\n"
    prompt += "- Contours épais, encrage net, dessin lisible.\n"
    prompt += "- Couleurs vives et contrastées (rouges, bleus, jaunes), ambiance drôle.\n"
    prompt += "- Décors simples mais reconnaissables : plateau TV, meeting, rue, bureau, marché.\n"
    prompt += "- Bulles très lisibles, texte court en français.\n"
    prompt += "- Pas réaliste, pas photo.\n\n"

    prompt += "À ÉVITER ABSOLUMENT : photoréalisme, style peinture/aquarelle, texte illisible, trop de petits détails.\n\n"

    # Format / cases
    prompt += "FORMAT : une planche unique en 1024x1024.\n"
    prompt += "NOMBRE DE CASES : plusieurs cases (entre 6 et 10), organisées proprement et lisiblement.\n"
    prompt += "Chaque case = une idée / une promesse / une contradiction / un décalage entre discours et réalité.\n\n"

    # Thèmes
    prompt += "THÈMES DOMINANTS À UTILISER :\n"
    for t in top_themes:
        prompt += f"- {t}\n"
    prompt += "\n"

    # Matière (phrases)
    prompt += "MATIÈRE D’INSPIRATION (utiliser ces extraits comme base d'idées, sans les recopier mot à mot) :\n"
    for theme, q in selected:
        prompt += f"- [{theme}] {q}\n"
    prompt += "\n"

    # Directives satire (plus explicites)
    prompt += "DIRECTIVES SATIRIQUES (IMPORTANT) :\n"
    prompt += "- Exagère les effets d’annonce et les slogans creux.\n"
    prompt += "- Montre un personnage 'spin doctor' qui reformule tout en langage politique ridicule.\n"
    prompt += "- Fais ressortir les contradictions (ex: promesse simple vs réalité complexe).\n"
    prompt += "- Ajoute des détails comiques (tableaux, graphiques bidons, éléments de com' absurdes).\n"
    prompt += "- Finir par une CHUTE claire et drôle qui ridiculise la posture ou la promesse.\n\n"

    # Fil narratif (sans imposer 4 cases)
    prompt += "FIL NARRATIF RECOMMANDÉ :\n"
    prompt += "Début : promesse spectaculaire.\n"
    prompt += "Milieu : accumulation de com' + contradictions + déconnexion du terrain.\n"
    prompt += "Fin : réalité qui rattrape + punchline finale moqueuse.\n\n"

    prompt += "RAPPEL : satire mordante mais 'safe'. Bulles courtes, lisibles, en français.\n"

    return prompt

def generate_bd_prompt_logic(
    party_name,
    analysis_results,
    angle_satirique="",
    max_quotes=60,
    seed=None
):
    """
    Génère un prompt très orienté "BD satirique franco-belge" (comme l'exemple),
    avec phrases sélectionnées aléatoirement et de façon équilibrée par thèmes.
    
    analysis_results: liste de tuples (theme, score, [phrases])
    """
    import random

    if seed is not None:
        random.seed(seed)

    # --- 1) Construire une pool de phrases par thème ---
    pools = []
    for (theme, score, phrases) in (analysis_results or []):
        clean_phrases = []
        for p in (phrases or []):
            if isinstance(p, str):
                s = p.strip()
                if s:
                    clean_phrases.append(s)

        if clean_phrases:
            random.shuffle(clean_phrases)
            pools.append((theme, score, clean_phrases))

    if not pools:
        return "Impossible de générer un prompt : aucune phrase n'a été extraite."

    # --- 2) Sélection aléatoire mais équilibrée entre thèmes (round-robin) ---
    pools_sorted = sorted(pools, key=lambda x: x[1], reverse=True)

    selected = []
    idx = 0
    while len(selected) < max_quotes and any(len(p[2]) > 0 for p in pools_sorted):
        theme, score, ph = pools_sorted[idx % len(pools_sorted)]
        if ph:
            selected.append((theme, ph.pop(0)))
        idx += 1

    # Thèmes dominants (affichage)
    top_themes = [t for (t, _, _) in pools_sorted][:8]

    # --- 3) Prompt final : style BD + satire claire ---
    prompt = ""
    prompt += "Génère UNE SEULE IMAGE : une planche de bande dessinée satirique en français.\n\n"

    prompt += "STYLE VISUEL (OBLIGATOIRE) :\n"
    prompt += "- Bande dessinée franco-belge très lisible, style presse satirique.\n"
    prompt += "- Dessin cartoon propre et net, contours noirs épais.\n"
    prompt += "- Personnages caricaturaux avec GROS NEZ, sourcils marqués, expressions exagérées.\n"
    prompt += "- Visages très expressifs (sourires forcés, regards cyniques/ironiques).\n"
    prompt += "- Couleurs vives et contrastées (bleu, rouge, jaune), éclairage clair.\n"
    prompt += "- Composition propre : cases bien séparées par des bordures blanches.\n"
    prompt += "- Bulles de dialogue grandes, texte TRÈS lisible, en MAJUSCULES, en français.\n"
    prompt += "- Pas réaliste, pas photo, pas peinture.\n\n"

    prompt += "À ÉVITER ABSOLUMENT : photoréalisme, style peinture/aquarelle, texte illisible, gore, haine.\n\n"

    prompt += "FORMAT :\n"
    prompt += "- Planche unique en 1024x1024\n"
    prompt += "- Plusieurs cases (6 à 10), organisées de manière fluide et lisible.\n"
    prompt += "- Une idée claire par case.\n\n"

    prompt += "TON & SATIRE :\n"
    prompt += "- Satire politique claire et visible.\n"
    prompt += "- On se MOQUE du parti/courant politique et de sa communication.\n"
    prompt += "- Exagérer la langue de bois, les slogans creux, les promesses irréalistes.\n"
    prompt += "- Montrer le décalage entre le discours officiel et la réalité quotidienne.\n"
    prompt += "- Humour ironique, absurde, mordant mais compréhensible par tous.\n"
    prompt += "- Règles de sécurité : pas de haine, pas d’insultes, pas d’attaques sur des caractéristiques protégées.\n"
    prompt += "  On caricature les idées et le storytelling politique, pas des personnes privées.\n\n"

    prompt += f"PARTI / COURANT : {party_name}\n"
    if angle_satirique:
        prompt += f"ANGLE SATIRIQUE PRIORITAIRE : {angle_satirique}\n"
    prompt += "\n"

    prompt += "MISE EN SCÈNE RECOMMANDÉE (à varier) :\n"
    prompt += "- Meeting politique avec drapeaux, foule enthousiaste, slogans.\n"
    prompt += "- Coulisses (bureau / salon feutré) où le discours change.\n"
    prompt += "- Citoyens (supermarché, factures, travail) qui subissent la réalité.\n"
    prompt += "- Dernière case : chute satirique très claire (panneau absurde, retournement, punchline).\n\n"

    prompt += "DIALOGUES (OBLIGATOIRE) :\n"
    prompt += "- Bulles courtes, percutantes, en MAJUSCULES.\n"
    prompt += "- Ton politique simpliste et volontairement excessif.\n"
    prompt += "- Exemple de ton (à adapter) : « NOUS PRENONS LE CONTRÔLE ! », « LA RICHESSE POUR LE PEUPLE ! », « C’EST NOUS QUI DÉCIDONS ! »\n\n"

    prompt += "THÈMES DOMINANTS À INTÉGRER :\n"
    for t in top_themes:
        prompt += f"- {t}\n"
    prompt += "\n"

    prompt += "MATIÈRE D’INSPIRATION (utiliser ces extraits comme base d'idées, sans copier mot à mot) :\n"
    for theme, q in selected:
        prompt += f"- [{theme}] {q}\n"
    prompt += "\n"

    prompt += "IMPORTANT :\n"
    prompt += "- Utiliser les extraits pour nourrir les idées de chaque case.\n"
    prompt += "- Faire ressortir au moins 2 contradictions ou décalages.\n"
    prompt += "- Finir par une chute satirique visible et drôle.\n"
    prompt += "- Garder un dessin lisible et des bulles lisibles.\n"

    return prompt