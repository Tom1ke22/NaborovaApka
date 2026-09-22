"""AI vrstva náborovej aplikácie.

Moduly:
- schemas    – štruktúra faktov, ktoré model vytiahne z CV a chatu
- scoring    – deterministický výpočet skóre 1–10 (bez volania AI)
- cv_text    – extrakcia textu z PDF / DOCX životopisu
- prompts    – popis pozície a obalenie textu od uchádzača
- client     – zdieľaný Gemini klient (None, ak AI nie je nastavená)
- chat       – streamovaný chatbot pre uchádzačov
- extraction – volanie modelu, ktoré z CV + chatu vráti ExtractedProfile
- evaluate   – orchestrácia hodnotenia uchádzača po odoslaní prihlášky

Ako to do seba zapadá:

    CV (PDF/DOCX) ─► cv_text ─┐
                              ├─► extraction ─► ExtractedProfile ─► scoring ─► ai_score
    chat uchádzača ───────────┘

Bez `GEMINI_API_KEY` (alebo s `AI_ENABLED=false`) appka normálne beží:
chatbot odpovie záložnou vetou a uchádzač ostane bez skóre.

Zámerne tu nič neimportujeme, aby sa čisté moduly (scoring, cv_text,
prompts) dali použiť a testovať bez nastaveného API kľúča či databázy.
"""
