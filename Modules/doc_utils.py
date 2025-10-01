import docx
from PyPDF2 import PdfReader

def extract_text_from_pdf(file):
    """Extract text from PDF"""
    pdf = PdfReader(file)
    text = ""
    for page in pdf.pages:
        text += page.extract_text() or ""
    return text

def extract_text_from_docx(file):
    """Extract text from Word (docx)"""
    doc = docx.Document(file)
    text = "\n".join([para.text for para in doc.paragraphs])
    return text

def extract_text(file):
    """Generic wrapper for pdf/docx/txt"""
    if file.type == "application/pdf":
        return extract_text_from_pdf(file)
    elif file.type in ["application/vnd.openxmlformats-officedocument.wordprocessingml.document"]:
        return extract_text_from_docx(file)
    elif file.type == "text/plain":
        return file.read().decode("utf-8", errors="ignore")
    else:
        return ""

def chunk_text(text, max_tokens=500):
    """
    Split text into chunks of roughly `max_tokens` words.
    Keeps context better than sentence by sentence.
    """
    words = text.split()
    chunks = []
    for i in range(0, len(words), max_tokens):
        chunk = " ".join(words[i:i+max_tokens])
        chunks.append(chunk)
    return chunks


# def extract_sections(file):
#     """
#     Split document into sections by headings.
#     Returns a list of dicts: [{"header": "Section title", "text": "Section content"}]
#     """
#     full_text = extract_text(file)
#     lines = full_text.split("\n")

#     sections = []
#     current_header = "Introduction"
#     current_text = []

#     for line in lines:
#         line_strip = line.strip()
#         # Heuristic: consider a line in all caps or ending with ':' as a heading
#         if line_strip.isupper() or line_strip.endswith(":"):
#             if current_text:
#                 sections.append({"header": current_header, "text": "\n".join(current_text)})
#                 current_text = []
#             current_header = line_strip
#         else:
#             if line_strip:
#                 current_text.append(line_strip)

#     # Add last section
#     if current_text:
#         sections.append({"header": current_header, "text": "\n".join(current_text)})

#     return sections

def extract_sections(file):
    full_text = extract_text(file)
    lines = full_text.split("\n")

    sections = []
    current_header = "Introduction"
    current_text = []

    for line in lines:
        line_strip = line.strip()
        if line_strip.isupper() or line_strip.endswith(":"):
            if current_text:
                # Apply chunking
                section_text = "\n".join(current_text)
                for chunk in chunk_text(section_text):
                    sections.append({"header": current_header, "text": chunk})
                current_text = []
            current_header = line_strip
        else:
            if line_strip:
                current_text.append(line_strip)

    if current_text:
        section_text = "\n".join(current_text)
        for chunk in chunk_text(section_text):
            sections.append({"header": current_header, "text": chunk})

    return sections
