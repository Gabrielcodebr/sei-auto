"""
Configurações do projeto de automação SEI
"""

import os

# ===== CAMINHOS DE PROGRAMAS EXTERNOS =====

# Caminho do executável do Tesseract OCR
# Ajuste para o caminho onde você instalou o Tesseract
TESSERACT_PATH = r"C:\Users\Gabriel Fatec Itu\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"

# Caminho da pasta bin do Poppler
# Ajuste para o caminho onde você extraiu o Poppler
POPPLER_PATH = r"C:\Programas\poppler-25.12.0\Library\bin"

# ===== PASTAS DO PROJETO =====

# Pasta raiz do projeto
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Pasta onde estão os documentos numerados
DOCUMENTOS_DIR = os.path.join(BASE_DIR, "documentos")

# ===== CONFIGURAÇÕES DE AUTOMAÇÃO =====

# Tempo de pausa entre ações (em segundos)
PAUSE_BETWEEN_ACTIONS = 0.5

# Tempo de espera para elementos carregarem (em segundos)
WAIT_FOR_ELEMENT = 1.0

# Tempo máximo de espera para upload (em segundos)
MAX_UPLOAD_WAIT = 10

# ===== CONFIGURAÇÕES DE OCR =====

# Idioma do Tesseract (português)
OCR_LANGUAGE = "por"

# Confiança mínima para aceitar resultado do OCR (0-100)
OCR_MIN_CONFIDENCE = 60

# ===== CONFIGURAÇÕES DE IMAGEM =====

# DPI para renderização de PDF
PDF_DPI = 200

# Formato de imagem para print
IMAGE_FORMAT = "PNG"

# ===== TEXTOS FIXOS =====

# Texto do despacho de aprovação (item 4)
DESPACHO_APROVACAO_TEMPLATE = """Aprova-se Nota de Empenho {numero_ne}, documento: {link_ne}

São Paulo, {data_ne}

WILLIAN DE OLIVEIRA SALAZAR
Coordenador de Departamento de Orçamento e Finanças – COF"""

# ===== VALIDAÇÃO =====

def validar_configuracoes():
    """Valida se as configurações estão corretas"""
    erros = []
    
    # Verifica Tesseract
    if not os.path.exists(TESSERACT_PATH):
        erros.append(f"Tesseract não encontrado em: {TESSERACT_PATH}")
    
    # Verifica Poppler
    if not os.path.exists(POPPLER_PATH):
        erros.append(f"Poppler não encontrado em: {POPPLER_PATH}")
    
    # Verifica pasta de documentos
    if not os.path.exists(DOCUMENTOS_DIR):
        erros.append(f"Pasta de documentos não encontrada: {DOCUMENTOS_DIR}")
        erros.append("Crie a pasta 'documentos' na raiz do projeto")
    
    if erros:
        print("❌ ERROS DE CONFIGURAÇÃO:")
        for erro in erros:
            print(f"  - {erro}")
        return False
    
    print("✅ Todas as configurações estão corretas!")
    return True


if __name__ == "__main__":
    # Testa as configurações quando executar este arquivo diretamente
    validar_configuracoes()