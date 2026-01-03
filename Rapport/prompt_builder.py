def generate_bd_prompt_logic(party_name, analysis_results, satire_angle):
    if not analysis_results: return ""
    
    # 1. Sélection des 6 meilleurs thèmes uniquement (pour éviter l'erreur de longueur)
    top_themes = analysis_results[:6]
    themes_str = ", ".join([f"{t[0]}" for t in top_themes])
    
    # 2. Exemples : On prend seulement les 3 premiers thèmes
    examples_str = ""
    for theme, freq, phrases in analysis_results[:3]:
        examples_str += f"\n### THÈME : {theme}\n"
        for p in phrases[:2]:
            # On coupe les phrases trop longues (>150 caractères)
            clean_p = (p[:150] + "...") if len(p) > 150 else p
            examples_str += f"- « {clean_p} »\n"

    # 3. LE PROMPT EXACT QUE VOUS AVEZ DEMANDÉ
    prompt = f"""
Crée une planche de bande dessinée satirique de 4 cases inspirée du programme du parti politique "{party_name}".

OBJECTIF :
Produire une caricature politique claire, mordante et intelligible, qui met en scène de façon humoristique le décalage entre les promesses du programme et la réalité concrète vécue par les citoyens.

STYLE GRAPHIQUE :
- Bande dessinée française moderne (inspiration presse satirique).
- Trait expressif, contours nets, visages lisibles.
- Couleurs franches mais équilibrées.
- Décors simples et immédiatement reconnaissables (plateau télé, rue, bureau administratif, meeting, café, marché, logement, etc.).
- Mise en page claire : une idée forte par case, lecture fluide de gauche à droite.
Bande blanche autour de la planche afin d’avoir une bonne lisibilité.

TON & SATIRE :
- Satire assumée, intelligente.
- Ironie appuyée.
- Insister de manière satirique sur les idées, contradictions ou simplifications du programme.

ANGLE SCÉNARISTIQUE :
{satire_angle}

STRUCTURE NARRATIVE :
- Chaque case représente une situation concrète liée à un thème politique.
- Les bulles de dialogues, naturelles, percutantes et crédibles.
- Les dialogues s’inspirent du vocabulaire, du ton et des idées du programme sans jamais reprendre une phrase exacte.
- Progression claire : mise en place -> décalage -> absurdité -> chute.
- La dernière case doit contenir une chute satirique visuelle ou textuelle immédiatement compréhensible.

THÈMES POLITIQUES À INTÉGRER :
{themes_str}

MATÉRIEL D’INSPIRATION (EXTRAITS DU PROGRAMME) :
{examples_str}

PERSONNAGES :
- Archétypes reconnaissables et bienveillants de ce courant politique : militant, élu, citoyen, expert.
- Expressions faciales très marquées.
- Gestuelle exagérée mais crédible.

CONTRAINTES STRICTES :
- Toujours inclure des bulles de dialogue.
- Aucun texte explicatif hors bulles.
- Aucun slogan ou phrase copiée mot à mot.
- Priorité absolue à la lisibilité, à la narration visuelle et à l’impact satirique.
"""
    # Sécurité technique pour ne jamais dépasser la limite
    return prompt[:3900]