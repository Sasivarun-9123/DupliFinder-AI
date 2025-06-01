from typing import List, Set  # ✅ This was missing!
import hashlib
import re
def calculate_pdf_similarity(file1_path: str, file2_path: str) -> float:
    """Calculate similarity between PDF files"""
    try:
        return _calculate_similarity_pypdf2(file1_path, file2_path)
    except:
        try:
            return _calculate_similarity_pdfminer(file1_path, file2_path)
        except:
            return _calculate_similarity_hash_based(file1_path, file2_path)

def _calculate_similarity_pypdf2(file1_path: str, file2_path: str) -> float:
    """Calculate similarity using PyPDF2"""
    from PyPDF2 import PdfReader
    
    text1 = _extract_text_pypdf2(file1_path)
    text2 = _extract_text_pypdf2(file2_path)
    
    return _jaccard_similarity(text1, text2)

def _extract_text_pypdf2(file_path: str) -> str:
    """Extract text using PyPDF2"""
    from PyPDF2 import PdfReader
    
    text = ""
    with open(file_path, 'rb') as file:
        reader = PdfReader(file)
        for page in reader.pages:
            text += page.extract_text()
    return text

def _calculate_similarity_pdfminer(file1_path: str, file2_path: str) -> float:
    """Calculate similarity using pdfminer"""
    from pdfminer.high_level import extract_text
    
    text1 = extract_text(file1_path)
    text2 = extract_text(file2_path)
    
    return _jaccard_similarity(text1, text2)

def _calculate_similarity_hash_based(file1_path: str, file2_path: str) -> float:
    """Hash-based similarity as fallback"""
    import hashlib
    
    def get_file_blocks(path):
        blocks = set()
        with open(path, 'rb') as f:
            while True:
                chunk = f.read(4096)
                if not chunk:
                    break
                blocks.add(hashlib.md5(chunk).hexdigest())
        return blocks
    
    blocks1 = get_file_blocks(file1_path)
    blocks2 = get_file_blocks(file2_path)
    
    if not blocks1 or not blocks2:
        return 0.0
    
    intersection = len(blocks1.intersection(blocks2))
    union = len(blocks1.union(blocks2))
    
    return intersection / union if union > 0 else 0.0

def _jaccard_similarity(text1: str, text2: str) -> float:
    """Calculate Jaccard similarity between texts"""
    words1 = set(_tokenize_text(text1))
    words2 = set(_tokenize_text(text2))
    
    if not words1 or not words2:
        return 0.0
    
    intersection = len(words1.intersection(words2))
    union = len(words1.union(words2))
    
    return intersection / union if union > 0 else 0.0

def _tokenize_text(text: str) -> List[str]:
    """Clean and tokenize text"""
    import re
    text = re.sub(r'[^\w\s]', '', text.lower())
    return text.split()