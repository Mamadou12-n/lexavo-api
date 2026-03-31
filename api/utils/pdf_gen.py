"""Génération de PDF pour contrats et rapports — WeasyPrint."""


def generate_pdf(html_content: str, title: str = "Lexavo") -> bytes:
    try:
        from weasyprint import HTML
    except ImportError:
        raise RuntimeError("WeasyPrint requis. pip install weasyprint")
    styled_html = f"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="UTF-8"><title>{title}</title>
<style>
body {{ font-family: 'Helvetica', sans-serif; font-size: 11pt; line-height: 1.6; color: #1C2B3A; margin: 40px; }}
h1 {{ color: #E85D26; font-size: 18pt; }}
h2 {{ color: #1C2B3A; font-size: 14pt; border-bottom: 1px solid #E4E4E7; padding-bottom: 4px; }}
.disclaimer {{ background: #FFF3EE; border-left: 3px solid #E85D26; padding: 12px 16px; font-size: 9pt; color: #71717A; margin-top: 30px; }}
.footer {{ text-align: center; font-size: 8pt; color: #A1A1AA; margin-top: 40px; }}
</style></head><body>
{html_content}
<div class="disclaimer">Outil d'information juridique. Ne remplace pas un avis professionnel.</div>
<div class="footer">Lexavo — lexavo.be</div>
</body></html>"""
    return HTML(string=styled_html).write_pdf()
