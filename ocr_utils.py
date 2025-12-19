"""
Funções para reconhecimento de texto (OCR) usando Tesseract
"""

import re
import pytesseract
from PIL import Image
import config

# Configurar caminho do Tesseract
pytesseract.pytesseract.tesseract_cmd = config.TESSERACT_PATH


def normalizar_texto(texto):
    """
    Normaliza o texto removendo espaços extras e caracteres especiais
    
    Args:
        texto: String para normalizar
        
    Returns:
        String normalizada
    """
    if not texto:
        return ""
    
    # Remove espaços extras
    texto = " ".join(texto.split())
    # Remove quebras de linha extras
    texto = texto.replace("\n\n", "\n")
    
    return texto.strip()


def extrair_texto_imagem(imagem_path_ou_objeto, preprocessar=True):
    """
    Extrai texto de uma imagem usando OCR
    
    Args:
        imagem_path_ou_objeto: Caminho do arquivo ou objeto PIL.Image
        preprocessar: Se True, aplica pré-processamento na imagem
        
    Returns:
        String com o texto extraído
    """
    try:
        # Carrega a imagem se for um caminho
        if isinstance(imagem_path_ou_objeto, str):
            img = Image.open(imagem_path_ou_objeto)
        else:
            img = imagem_path_ou_objeto
        
        # Pré-processamento básico (se solicitado)
        if preprocessar:
            # Converte para escala de cinza
            img = img.convert('L')
            
            # Aumenta contraste (opcional)
            from PIL import ImageEnhance
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(2.0)
        
        # Executa OCR
        texto = pytesseract.image_to_string(
            img, 
            lang=config.OCR_LANGUAGE,
            config='--psm 6'  # Assume bloco único de texto
        )
        
        return normalizar_texto(texto)
        
    except Exception as e:
        print(f"❌ Erro ao extrair texto da imagem: {e}")
        return ""


def extrair_data(texto):
    """
    Extrai data no formato DD/MM/YYYY do texto
    
    Args:
        texto: String contendo a data
        
    Returns:
        String com a data no formato DD/MM/YYYY ou None
    """
    # Padrões de data
    padroes = [
        r'\b(\d{2})[/\-.](\d{2})[/\-.](\d{4})\b',  # DD/MM/YYYY
        r'\b(\d{2})[/\-.](\d{2})[/\-.](\d{2})\b',  # DD/MM/YY
    ]
    
    for padrao in padroes:
        match = re.search(padrao, texto)
        if match:
            dia, mes, ano = match.groups()
            
            # Converte ano de 2 dígitos para 4
            if len(ano) == 2:
                ano = f"20{ano}"
            
            # Valida dia e mês básicos
            try:
                dia_int = int(dia)
                mes_int = int(mes)
                if 1 <= dia_int <= 31 and 1 <= mes_int <= 12:
                    return f"{dia}/{mes}/{ano}"
            except ValueError:
                continue
    
    return None


def extrair_numero_documento(texto, padrao=None):
    """
    Extrai número de documento do texto
    
    Args:
        texto: String contendo o número
        padrao: Regex customizado (opcional)
        
    Returns:
        String com o número do documento ou None
    """
    if padrao:
        match = re.search(padrao, texto)
        if match:
            return match.group(1) if match.groups() else match.group(0)
    
    # Padrões comuns
    padroes = [
        r'(\d{4}[A-Z]{2}\d+)',  # Ex: 2025NE03848
        r'N[°º]?\s*(\d+)',  # Ex: Nº 123456
        r'Número[:\s]+(\d+)',  # Ex: Número: 123456
    ]
    
    for p in padroes:
        match = re.search(p, texto, re.IGNORECASE)
        if match:
            return match.group(1)
    
    return None


def extrair_cnpj(texto):
    """
    Extrai CNPJ do texto
    
    Args:
        texto: String contendo o CNPJ
        
    Returns:
        String com o CNPJ formatado ou None
    """
    # Remove pontuação para buscar números
    texto_limpo = re.sub(r'[^\d]', '', texto)
    
    # Procura por 14 dígitos consecutivos
    match = re.search(r'(\d{14})', texto_limpo)
    if match:
        cnpj = match.group(1)
        # Formata: 00.000.000/0000-00
        return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"
    
    # Tenta encontrar já formatado
    match = re.search(r'(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})', texto)
    if match:
        return match.group(1)
    
    return None


def extrair_nome_empresa(texto, max_palavras=5):
    """
    Tenta extrair nome da empresa do texto
    
    Args:
        texto: String contendo o nome
        max_palavras: Número máximo de palavras do nome
        
    Returns:
        String com o nome da empresa ou None
    """
    # Procura por padrões comuns
    padroes = [
        r'(?:Razão Social|Empresa|Nome)[:\s]+([A-ZÀ-Ú][A-ZÀ-Ú\s]+(?:LTDA|S\.A\.|ME|EPP)?)',
        r'([A-ZÀÂ-Ú][A-ZÀ-Ú\s]{10,}(?:LTDA|S\.A\.|ME|EPP))',
    ]
    
    for padrao in padroes:
        match = re.search(padrao, texto, re.IGNORECASE)
        if match:
            nome = match.group(1).strip()
            # Limita número de palavras
            palavras = nome.split()[:max_palavras]
            return " ".join(palavras)
    
    return None


def extrair_numero_guia_iss(texto):
    """
    Extrai número da guia de ISS removendo zeros à esquerda
    
    Args:
        texto: String contendo o número da guia
        
    Returns:
        String com o número sem zeros à esquerda ou None
    """
    # Procura pelo padrão específico
    match = re.search(r'N[°º]?\s*DA\s*GUIA[:\s]+(\d+)', texto, re.IGNORECASE)
    if match:
        numero = match.group(1)
        # Remove zeros à esquerda
        return str(int(numero))
    
    return None


def localizar_texto_na_imagem(imagem_path_ou_objeto, texto_busca):
    """
    Localiza um texto específico na imagem e retorna suas coordenadas
    
    Args:
        imagem_path_ou_objeto: Caminho do arquivo ou objeto PIL.Image
        texto_busca: Texto a ser localizado (case-insensitive)
        
    Returns:
        Tupla (x, y, largura, altura) ou None se não encontrado
    """
    try:
        # Carrega a imagem
        if isinstance(imagem_path_ou_objeto, str):
            img = Image.open(imagem_path_ou_objeto)
        else:
            img = imagem_path_ou_objeto
        
        # Executa OCR com dados de posição
        dados = pytesseract.image_to_data(
            img,
            lang=config.OCR_LANGUAGE,
            output_type=pytesseract.Output.DICT
        )
        
        # Normaliza texto de busca
        texto_busca_norm = normalizar_texto(texto_busca.lower())
        palavras_busca = texto_busca_norm.split()
        
        # Procura pelas palavras na sequência
        n_boxes = len(dados['text'])
        for i in range(n_boxes - len(palavras_busca) + 1):
            # Verifica se a sequência de palavras corresponde
            sequencia = []
            for j in range(len(palavras_busca)):
                texto_box = normalizar_texto(dados['text'][i + j].lower())
                sequencia.append(texto_box)
            
            if ' '.join(sequencia) == texto_busca_norm:
                # Retorna coordenadas do primeiro box
                x = dados['left'][i]
                y = dados['top'][i]
                w = dados['width'][i]
                h = dados['height'][i]
                return (x, y, w, h)
        
        return None
        
    except Exception as e:
        print(f"❌ Erro ao localizar texto na imagem: {e}")
        return None


# ===== TESTES =====

if __name__ == "__main__":
    print("Testando funções de OCR...")
    
    # Teste de normalização
    texto = "  Texto   com    espaços   extras  "
    print(f"Normalizado: '{normalizar_texto(texto)}'")
    
    # Teste de extração de data
    texto_data = "Emitido em 15/03/2025 na cidade"
    data = extrair_data(texto_data)
    print(f"Data encontrada: {data}")
    
    # Teste de CNPJ
    texto_cnpj = "CNPJ: 12.345.678/0001-99 da empresa"
    cnpj = extrair_cnpj(texto_cnpj)
    print(f"CNPJ encontrado: {cnpj}")
    
    print("\n✅ Testes concluídos!")