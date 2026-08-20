"""Engine UI strings. EN/ES/FR. Does not translate official document names or tags."""
from __future__ import annotations

LANGS = ("en", "es", "fr")


def lang_of(value) -> str:
    v = (value or "en").strip().lower()
    if v.startswith("es"):
        return "es"
    if v.startswith("fr"):
        return "fr"
    return "en"


STRINGS = {
    "en": {
        "q_when": "When did the problem start?",
        "q_continuous": "Does it happen continuously or intermittently?",
        "q_load": "Does it occur only while processing material or also at idle?",
        "q_noise": "Is there unusual noise? If yes, is it closer to the motor, belt, gearbox, or another area?",
        "q_vibration": "Is there unusual vibration?",
        "q_heat": "Is there overheating or a burning smell?",
        "q_alarm": "Is an alarm or fault code displayed? If yes, what is the exact message?",
        "q_power": "Does the component appear to have power / does it try to start?",
        "q_recent": "Has anything been replaced or adjusted recently?",
        "q_restart": "Does the problem disappear after restarting the machine?",
        "q_where": "Where exactly does the symptom appear?",
        "q_speed": "Does the noise or symptom change with motor speed?",
        "q_obstruction": "Is there a visible obstruction or material buildup?",
        "q_subsystem": "Which machine subsystem is affected?",
        "q_stopped": "Is the component completely stopped or operating abnormally?",
        "q_sudden": "Did the problem appear suddenly or gradually?",
        "need_details": "I need a few more details to narrow this down. ",
        "need_more": "I could not identify a documented alarm from this description. To narrow the problem down, please tell me:",
        "need_more_1": "1. Which machine subsystem is affected?",
        "need_more_2": "2. Is the component completely stopped or operating abnormally?",
        "need_more_3": "3. Did the problem appear suddenly or gradually?",
        "need_more_4": "4. Is there unusual noise, vibration, heat, or smell?",
        "need_more_5": "5. Is any alarm displayed?",
        "not_in_kb": "That component or machine is not identified in the official consultation layer for this baler. ",
        "related": "Documented items may be related to this description: {names}. This is not a confirmed cause. ",
        "insufficient": "There is not enough documented evidence to propose a cause. ",
        "ask_detail": "Please describe the equipment, the symptom, and whether an alarm is present.",
        "audio_hint": " The sound may be consistent with a mechanical issue, but additional information is required.",
        "no_binary": "Media was received. Analysis is unavailable in this Engine. Continue with questions. This is not a confirmed identification.",
        "hyp_note": "Documented association only. Not a confirmed cause.",
        "chk_desc": "Review the documented item '{name}'. Completing this step does not confirm a cause.",
        "chk_safety": "Documentary guidance only. Not authorization to intervene, replace, bypass, or energize.",
        "chk_expected": "The documented reference has been reviewed. Physical condition is not confirmed.",
        "chk_fail": "If the documented condition is not observed, record a user observation and continue. Do not invent a diagnosis.",
        "safe_wire": "A specific wire, terminal, or connection cannot be determined safely from the available documentation. The index identifies tag references on the drawing, but that is not a confirmed terminal or cable. Review the indicated electrical pages and the applicable procedure before any intervention.",
        "safe_claim": "The documentation relates this query to the indicated references. Review the documented reference and procedure. The knowledge base does not confirm a failed component, does not confirm electrical continuity, and does not authorize intervention.",
        "doc_found": "Documented reference: {name}. Official document names are unchanged.",
        "doc_pages": "Documentary pages: {pages}. These locate labels or messages; they do not confirm continuity, a terminal, a cable, or a root cause.",
        "doc_action": "Review the documented action in PL3_INFO if present. This does not authorize intervention.",
    },
    "es": {
        "q_when": "¿Cuándo comenzó el problema?",
        "q_continuous": "¿Ocurre de forma continua o intermitente?",
        "q_load": "¿Ocurre solo al procesar material o también en vacío?",
        "q_noise": "¿Hay un ruido inusual? Si es así, ¿está más cerca del motor, la banda, el reductor u otra zona?",
        "q_vibration": "¿Hay vibración inusual?",
        "q_heat": "¿Hay sobrecalentamiento u olor a quemado?",
        "q_alarm": "¿Se muestra una alarma o código de falla? Si es así, ¿cuál es el mensaje exacto?",
        "q_power": "¿El componente parece tener alimentación / intenta arrancar?",
        "q_recent": "¿Se reemplazó o ajustó algo recientemente?",
        "q_restart": "¿El problema desaparece al reiniciar la máquina?",
        "q_where": "¿Dónde aparece exactamente el síntoma?",
        "q_speed": "¿El ruido o el síntoma cambia con la velocidad del motor?",
        "q_obstruction": "¿Hay una obstrucción visible o acumulación de material?",
        "q_subsystem": "¿Qué subsistema de la máquina está afectado?",
        "q_stopped": "¿El componente está completamente detenido o funciona de forma anormal?",
        "q_sudden": "¿El problema apareció de forma súbita o gradual?",
        "need_details": "Necesito algunos detalles más para acotar el problema. ",
        "need_more": "No pude identificar una alarma documentada a partir de esta descripción. Para acotar el problema, indique:",
        "need_more_1": "1. ¿Qué subsistema de la máquina está afectado?",
        "need_more_2": "2. ¿El componente está completamente detenido o funciona de forma anormal?",
        "need_more_3": "3. ¿El problema apareció de forma súbita o gradual?",
        "need_more_4": "4. ¿Hay ruido, vibración, calor u olor inusual?",
        "need_more_5": "5. ¿Se muestra alguna alarma?",
        "not_in_kb": "Ese componente o máquina no está identificado en la capa de consulta oficial de esta empacadora. ",
        "related": "Hay elementos documentados que podrían relacionarse con esta descripción: {names}. Esto no es una causa confirmada. ",
        "insufficient": "No hay evidencia documental suficiente para proponer una causa. ",
        "ask_detail": "Describa el equipo, el síntoma y si hay una alarma.",
        "audio_hint": " El sonido puede ser compatible con un problema mecánico, pero se requiere información adicional.",
        "no_binary": "Se recibió el archivo. El análisis no está disponible en este Engine. Continúe con preguntas. Esto no es una identificación confirmada.",
        "hyp_note": "Solo una asociación documentada. No es una causa confirmada.",
        "chk_desc": "Revise el elemento documentado '{name}'. Completar este paso no confirma una causa.",
        "chk_safety": "Solo orientación documental. No autoriza intervenir, reemplazar, puentear ni energizar.",
        "chk_expected": "Se revisó la referencia documentada. La condición física no está confirmada.",
        "chk_fail": "Si no se observa la condición documentada, registre una observación y continúe. No invente un diagnóstico.",
        "safe_wire": "No se puede determinar de forma segura un cable, borne o conexión específica con la documentación disponible. El índice identifica referencias del tag en el plano, pero eso no confirma un borne ni un cable. Consulte las páginas eléctricas indicadas y el procedimiento aplicable antes de cualquier intervención.",
        "safe_claim": "La documentación relaciona esta consulta con las referencias indicadas. Consulte la referencia y el procedimiento documentado. La base no confirma un componente defectuoso, no confirma continuidad eléctrica y no autoriza intervención.",
        "doc_found": "Referencia documentada: {name}. Los nombres oficiales de documentos no se traducen.",
        "doc_pages": "Páginas documentales: {pages}. Ubican rótulos o mensajes; no confirman continuidad, borne, cable ni causa raíz.",
        "doc_action": "Consulte la acción documentada en PL3_INFO si existe. Esto no autoriza intervención.",
    },
    "fr": {
        "q_when": "Quand le problème a-t-il commencé ?",
        "q_continuous": "Le phénomène est-il continu ou intermittent ?",
        "q_load": "Se produit-il seulement en traitement de matériau ou aussi à vide ?",
        "q_noise": "Y a-t-il un bruit inhabituel ? Si oui, est-il plus proche du moteur, de la courroie, du réducteur ou d'une autre zone ?",
        "q_vibration": "Y a-t-il une vibration inhabituelle ?",
        "q_heat": "Y a-t-il une surchauffe ou une odeur de brûlé ?",
        "q_alarm": "Un code d'alarme ou de panne s'affiche-t-il ? Si oui, quel est le message exact ?",
        "q_power": "Le composant semble-t-il alimenté / essaie-t-il de démarrer ?",
        "q_recent": "Quelque chose a-t-il été remplacé ou réglé récemment ?",
        "q_restart": "Le problème disparaît-il après un redémarrage ?",
        "q_where": "Où le symptôme apparaît-il exactement ?",
        "q_speed": "Le bruit ou le symptôme change-t-il avec la vitesse du moteur ?",
        "q_obstruction": "Y a-t-il une obstruction visible ou une accumulation de matériau ?",
        "q_subsystem": "Quel sous-système de la machine est concerné ?",
        "q_stopped": "Le composant est-il complètement arrêté ou fonctionne-t-il de manière anormale ?",
        "q_sudden": "Le problème est-il apparu soudainement ou progressivement ?",
        "need_details": "J'ai besoin de quelques précisions pour cerner le problème. ",
        "need_more": "Je n'ai pas identifié d'alarme documentée à partir de cette description. Pour préciser le problème, indiquez :",
        "need_more_1": "1. Quel sous-système de la machine est concerné ?",
        "need_more_2": "2. Le composant est-il complètement arrêté ou fonctionne-t-il de manière anormale ?",
        "need_more_3": "3. Le problème est-il apparu soudainement ou progressivement ?",
        "need_more_4": "4. Y a-t-il un bruit, une vibration, de la chaleur ou une odeur inhabituelle ?",
        "need_more_5": "5. Une alarme s'affiche-t-elle ?",
        "not_in_kb": "Ce composant ou cette machine n'est pas identifié dans la couche de consultation officielle de cette presse. ",
        "related": "Des éléments documentés peuvent être liés à cette description : {names}. Ce n'est pas une cause confirmée. ",
        "insufficient": "Il n'y a pas assez de preuve documentaire pour proposer une cause. ",
        "ask_detail": "Décrivez l'équipement, le symptôme et s'il existe une alarme.",
        "audio_hint": " Le son peut être compatible avec un problème mécanique, mais des informations supplémentaires sont requises.",
        "no_binary": "Le fichier a été reçu. L'analyse n'est pas disponible dans ce moteur. Continuez avec des questions. Ce n'est pas une identification confirmée.",
        "hyp_note": "Association documentée uniquement. Cause non confirmée.",
        "chk_desc": "Examinez l'élément documenté '{name}'. Terminer cette étape ne confirme pas une cause.",
        "chk_safety": "Orientation documentaire uniquement. Cela n'autorise ni intervention, ni remplacement, ni pontage, ni mise sous tension.",
        "chk_expected": "La référence documentée a été examinée. L'état physique n'est pas confirmé.",
        "chk_fail": "Si la condition documentée n'est pas observée, consignez une observation et continuez. N'inventez pas un diagnostic.",
        "safe_wire": "Un câble, une borne ou une connexion spécifique ne peut pas être déterminé de manière sûre à partir de la documentation disponible. L'index identifie des références de tag sur le plan, mais cela ne confirme ni une borne ni un câble. Consultez les pages électriques indiquées et la procédure applicable avant toute intervention.",
        "safe_claim": "La documentation relie cette requête aux références indiquées. Consultez la référence et la procédure documentée. La base ne confirme pas un composant défaillant, ne confirme pas une continuité électrique et n'autorise pas d'intervention.",
        "doc_found": "Référence documentée : {name}. Les noms officiels de documents ne sont pas traduits.",
        "doc_pages": "Pages documentaires : {pages}. Elles localisent des libellés ou messages ; elles ne confirment ni continuité, ni borne, ni câble, ni cause racine.",
        "doc_action": "Consultez l'action documentée dans PL3_INFO si elle existe. Cela n'autorise pas d'intervention.",
    },
}


def t(lang: str, key: str, **vars) -> str:
    pack = STRINGS.get(lang_of(lang)) or STRINGS["en"]
    s = pack.get(key) or STRINGS["en"].get(key) or key
    for k, v in vars.items():
        s = s.replace("{" + k + "}", str(v))
    return s


def need_more_block(lang: str) -> str:
    keys = ["need_details", "need_more", "need_more_1", "need_more_2", "need_more_3", "need_more_4", "need_more_5"]
    return " ".join(t(lang, k) for k in keys)
