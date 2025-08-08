import os
import PyPDF2
import docx

def _read_from_txt(file_path: str) -> str:
    """Reads content from a plain text file."""
    try:
        with open(file_path, "r", encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Error reading TXT file {file_path}: {e}")
        return ""

def _read_from_pdf(file_path: str) -> str:
    """Extracts text content from a PDF file."""
    try:
        text = ""
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text += page.extract_text() or ""
        return text
    except Exception as e:
        print(f"Error reading PDF file {file_path}: {e}")
        return ""

def _read_from_docx(file_path: str) -> str:
    """Extracts text content from a DOCX file."""
    try:
        doc = docx.Document(file_path)
        return "\n".join([para.text for para in doc.paragraphs])
    except Exception as e:
        print(f"Error reading DOCX file {file_path}: {e}")
        return ""

def read_text_from_file(file_path: str) -> str:
    """
    Reads text content from a file based on its extension.
    Supports .txt, .pdf, and .docx files.
    """
    _, file_extension = os.path.splitext(file_path)
    file_extension = file_extension.lower()

    print(f"--- 📄 Reading file: {file_path} (type: {file_extension}) ---")

    if file_extension == ".txt" or file_extension == ".md":
        return _read_from_txt(file_path)
    elif file_extension == ".pdf":
        return _read_from_pdf(file_path)
    elif file_extension == ".docx":
        return _read_from_docx(file_path)
    else:
        print(f"--- ⚠️ Unsupported file type: {file_extension} ---")
        return ""

