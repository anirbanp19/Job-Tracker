"""Extract plaintext from the candidate's PDF resume."""
import pypdf


def extract_resume_text(pdf_path: str) -> str:
    reader = pypdf.PdfReader(pdf_path)
    chunks = []
    for page in reader.pages:
        text = page.extract_text() or ""
        chunks.append(text)
    return "\n".join(chunks).strip()
