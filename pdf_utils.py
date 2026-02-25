"""
Funções para manipulação de arquivos PDF
ATUALIZADO: Usa PyMuPDF (fitz) ao invés de pdf2image
Não precisa mais do Poppler!
"""

import os
import re
import fitz  # PyMuPDF
from PIL import Image
import io
import config
import ocr_utils


def renderizar_primeira_pagina_pdf(pdf_path, dpi=None):
    """
    Renderiza a primeira página de um PDF como imagem
    
    Args:
        pdf_path: Caminho do arquivo PDF
        dpi: Resolução (usa config.PDF_DPI se None)
        
    Returns:
        Objeto PIL.Image da primeira página
    """
    try:
        if dpi is None:
            dpi = config.PDF_DPI
        
        doc = fitz.open(pdf_path)
        
        if len(doc) == 0:
            print(f"❌ PDF sem páginas: {pdf_path}")
            doc.close()
            return None
        
        page = doc[0]
        
        zoom = dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)
        
        pix = page.get_pixmap(matrix=mat)
        
        img_data = pix.tobytes("png")
        imagem = Image.open(io.BytesIO(img_data))
        
        doc.close()
        
        return imagem
        
    except Exception as e:
        print(f"❌ Erro ao renderizar PDF: {e}")
        return None


def processar_capa_especial(pdf_path):
    """
    Processa a capa com regra especial:
    - Renderiza primeira página
    - Localiza "Tribunal de Contas do Estado de São Paulo"
    - Corta tudo acima dessa linha
    """
    try:
        print("  📄 Renderizando capa...")
        imagem = renderizar_primeira_pagina_pdf(pdf_path)
        
        if not imagem:
            return None
        
        print("  🔍 Procurando texto 'Tribunal de Contas'...")
        
        texto_busca = "Tribunal de Contas do Estado de São Paulo"
        coords = ocr_utils.localizar_texto_na_imagem(imagem, texto_busca)
        
        if coords:
            x, y, w, h = coords
            print(f"  ✅ Texto encontrado na posição Y={y}")
            largura, altura = imagem.size
            imagem_cortada = imagem.crop((0, y, largura, altura))
            print(f"  ✂️ Imagem cortada de {altura}px para {altura - y}px")
            return imagem_cortada
        else:
            print("  ⚠️ Texto 'Tribunal de Contas' não encontrado")
            print("  ℹ️ Usando imagem completa sem corte")
            return imagem
            
    except Exception as e:
        print(f"❌ Erro ao processar capa: {e}")
        return None


def processar_print_padrao(pdf_path):
    """
    Processa PDF padrão para print (apenas renderiza primeira página)
    """
    return renderizar_primeira_pagina_pdf(pdf_path)


def salvar_imagem_temporaria(imagem, prefixo="temp"):
    try:
        temp_path = os.path.join(config.BASE_DIR, f"{prefixo}_temp.{config.IMAGE_FORMAT.lower()}")
        imagem.save(temp_path, config.IMAGE_FORMAT)
        return temp_path
    except Exception as e:
        print(f"❌ Erro ao salvar imagem temporária: {e}")
        return None


def extrair_texto_completo_pdf(pdf_path):
    """
    Extrai todo o texto de um PDF usando OCR
    """
    try:
        imagem = renderizar_primeira_pagina_pdf(pdf_path)
        if imagem:
            return ocr_utils.extrair_texto_imagem(imagem)
        return ""
    except Exception as e:
        print(f"❌ Erro ao extrair texto do PDF: {e}")
        return ""


def extrair_dados_nota_empenho(pdf_path):
    """
    Extrai dados específicos de uma Nota de Empenho.
    Retorna dicionário com 'data' e 'numero'.
    """
    try:
        print("  🔍 Extraindo dados da Nota de Empenho...")
        texto = extrair_texto_completo_pdf(pdf_path)
        
        data   = ocr_utils.extrair_data(texto)
        numero = ocr_utils.extrair_numero_documento(texto)
        
        if data:
            print(f"  ✅ Data: {data}")
        else:
            print("  ⚠️ Data não encontrada")
        
        if numero:
            print(f"  ✅ Número: {numero}")
        else:
            print("  ⚠️ Número não encontrado")
        
        return {'data': data, 'numero': numero}
        
    except Exception as e:
        print(f"❌ Erro ao extrair dados da NE: {e}")
        return {'data': None, 'numero': None}


def extrair_dados_ordem_bancaria(pdf_path):
    """
    Extrai dados específicos de uma Ordem Bancária.
    Usa regex específico para padrão OB (ex: 2025OB03848),
    com fallbacks para leituras incorretas do Tesseract (0B, 08, O8).

    Retorna dicionário com 'data' e 'numero'.
    """
    try:
        print("  🔍 Extraindo dados da Ordem Bancária...")
        texto = extrair_texto_completo_pdf(pdf_path)

        print(f"  📄 Texto extraído (primeiros 300 chars):\n{texto[:300]}")

        data = ocr_utils.extrair_data(texto)

        # Tenta variações que o Tesseract pode gerar para "OB":
        # OB correto, 0B (zero+B), O8 (O+8), 08 (zero+8)
        padroes_ob = [
            r'\d{4}OB\d+',   # correto:  2025OB03848
            r'\d{4}0B\d+',   # zero + B: 20250B03848
            r'\d{4}O8\d+',   # O + 8:    2025O803848
            r'\d{4}08\d+',   # zero + 8: 2025 0803848
        ]

        numero = None
        for padrao in padroes_ob:
            match = re.search(padrao, texto, re.IGNORECASE)
            if match:
                # Normaliza sempre para o formato correto com OB maiúsculo
                numero_raw = match.group(0).upper()
                # Substitui variações pelo OB correto
                numero = re.sub(r'(0B|O8|08)', 'OB', numero_raw)
                print(f"  ✅ Número OB encontrado (padrão '{padrao}'): {numero}")
                break

        if data:
            print(f"  ✅ Data: {data}")
        else:
            print("  ⚠️ Data não encontrada")

        if not numero:
            print("  ⚠️ Número OB não encontrado — verifique o texto acima")

        return {'data': data, 'numero': numero}

    except Exception as e:
        print(f"❌ Erro ao extrair dados da OB: {e}")
        return {'data': None, 'numero': None}


def renderizar_docx_como_imagem(docx_path):
    """
    Converte a primeira página de um .docx em imagem PIL.
    Usa o Word (via win32com) para converter para PDF, depois renderiza com PyMuPDF.
    """
    import tempfile
    import win32com.client

    try:
        print(f"  📄 Convertendo .docx para imagem via Word: {os.path.basename(docx_path)}")

        with tempfile.TemporaryDirectory() as tmpdir:
            nome_base  = os.path.splitext(os.path.basename(docx_path))[0]
            pdf_temp   = os.path.join(tmpdir, nome_base + '.pdf')
            docx_abs   = os.path.abspath(docx_path)

            word = win32com.client.Dispatch("Word.Application")
            word.Visible = False
            try:
                doc = word.Documents.Open(docx_abs)
                doc.SaveAs(pdf_temp, FileFormat=17)  # 17 = wdFormatPDF
                doc.Close()
            finally:
                word.Quit()

            imagem = renderizar_primeira_pagina_pdf(pdf_temp)
            print("  ✅ .docx convertido e renderizado")
            return imagem

    except Exception as e:
        print(f"❌ Erro ao renderizar .docx: {e}")
        return None



    """
    Extrai dados específicos de uma Nota Fiscal.
    - Número: busca após "NF-e" e "Nº"
    - Empresa: busca por ME, LTDA, EIRELI na parte superior do documento
    Retorna dicionário com 'data', 'numero' e 'empresa'.
    """
    try:
        print("  🔍 Extraindo dados da Nota Fiscal...")
        texto = extrair_texto_completo_pdf(pdf_path)

        data = ocr_utils.extrair_data(texto)

        # Número da NF: sempre na frente de "Nº", próximo a "NF-e" no documento
        numero = None
        pos_nfe = texto.upper().find('NF-E')
        if pos_nfe == -1:
            pos_nfe = texto.upper().find('NFE')
        if pos_nfe != -1:
            trecho = texto[pos_nfe:pos_nfe + 300]
            match = re.search(r'N[°º]\s*[:\s]?\s*([\d.]+)', trecho, re.IGNORECASE)
            if match:
                numero = re.sub(r'[.\s]', '', match.group(1))  # remove pontos
                numero = str(int(numero)) if numero.isdigit() else numero  # remove zeros à esquerda
        if not numero:
            match = re.search(r'N[°º]\s*[:\s]?\s*([\d.]+)', texto, re.IGNORECASE)
            if match:
                numero = re.sub(r'[.\s]', '', match.group(1))  # remove pontos
                numero = str(int(numero)) if numero.isdigit() else numero  # remove zeros à esquerda

        # Nome da empresa: captura o nome completo incluindo sufixos
        # Sufixos primários:  LTDA, EIRELI, S.A., S/A, EPP, ME, SS, EI, INDIVIDUAL
        # Sufixos secundários que podem vir depois (com ou sem traço):
        #   LTDA - ME,  LTDA EPP,  EIRELI - ME,  etc.
        SUFIXO_PRIMARIO  = r'(?:LTDA\.?|EIRELI\.?|S\.A\.|S/A|EI\b|INDIVIDUAL)'
        SUFIXO_SECUNDARIO = r'(?:\s*[-–]?\s*(?:ME|EPP|SS)\b)'
        SUFIXO_SOZINHO    = r'(?:ME|EPP|SS)\b'

        empresa = None
        # Padrão 1: nome + sufixo primário + sufixo secundário opcional
        # Ex: GAMA FILTROS LTDA - ME  /  ITU LUZ LTDA EPP  /  EMPRESA EIRELI
        match = re.search(
            rf'([A-ZÀ-Ú][A-ZÀ-Úa-zà-ú0-9\s\-&./]+?{SUFIXO_PRIMARIO}{SUFIXO_SECUNDARIO}?)',
            texto[:600], re.IGNORECASE
        )
        if not match:
            # Padrão 2: nome + sufixo sozinho (ME, EPP, SS sem LTDA antes)
            # Ex: EMPRESA - ME  /  EMPRESA ME
            match = re.search(
                rf'([A-ZÀ-Ú][A-ZÀ-Úa-zà-ú0-9\s&./]+?\s*[-–]?\s*{SUFIXO_SOZINHO})',
                texto[:600], re.IGNORECASE
            )
        if match:
            empresa = match.group(1).strip()

        if data:
            print(f"  ✅ Data: {data}")
        else:
            print("  ⚠️ Data não encontrada")

        if numero:
            print(f"  ✅ Número NF: {numero}")
        else:
            print("  ⚠️ Número NF não encontrado")

        if empresa:
            print(f"  ✅ Empresa: {empresa}")
        else:
            print("  ⚠️ Empresa não encontrada")

        return {'data': data, 'numero': numero, 'empresa': empresa}

    except Exception as e:
        print(f"❌ Erro ao extrair dados da NF: {e}")
        return {'data': None, 'numero': None, 'empresa': None}


def extrair_dados_nota_fiscal(pdf_path):
    """
    Extrai dados específicos de uma Nota Fiscal.
    - Número: busca após "NF-e" e "Nº", remove pontos e zeros à esquerda
    Retorna dicionário com 'data' e 'numero'.
    """
    try:
        print("  🔍 Extraindo dados da Nota Fiscal...")
        texto = extrair_texto_completo_pdf(pdf_path)

        data = ocr_utils.extrair_data(texto)

        # Número: localiza NF-e/NFS-e no texto e busca o Nº nos 300 chars seguintes
        numero = None
        pos_nfe = -1
        for termo in ('NFS-E', 'NFSE', 'NF-E', 'NFE'):
            pos = texto.upper().find(termo)
            if pos != -1:
                pos_nfe = pos
                break
        if pos_nfe != -1:
            trecho = texto[pos_nfe:pos_nfe + 300]
            match = re.search(r'N[°º]\s*[:\s]?\s*([\d.]+)', trecho, re.IGNORECASE)
            if match:
                numero = re.sub(r'[.\s]', '', match.group(1))
                numero = str(int(numero)) if numero.isdigit() else numero

        if not numero:
            match = re.search(r'N[°º]\s*[:\s]?\s*([\d.]+)', texto, re.IGNORECASE)
            if match:
                numero = re.sub(r'[.\s]', '', match.group(1))
                numero = str(int(numero)) if numero.isdigit() else numero

        if data:
            print(f"  ✅ Data: {data}")
        else:
            print("  ⚠️ Data não encontrada")

        if numero:
            print(f"  ✅ Número NF: {numero}")
        else:
            print("  ⚠️ Número NF não encontrado")

        return {'data': data, 'numero': numero}

    except Exception as e:
        print(f"❌ Erro ao extrair dados da NF: {e}")
        return {'data': None, 'numero': None}


def extrair_cnpj_documento(pdf_path):
    """
    Extrai CNPJ de um documento.
    """
    try:
        print("  🔍 Extraindo CNPJ...")
        texto = extrair_texto_completo_pdf(pdf_path)
        cnpj  = ocr_utils.extrair_cnpj(texto)
        
        if cnpj:
            print(f"  ✅ CNPJ: {cnpj}")
        else:
            print("  ⚠️ CNPJ não encontrado")
        
        return cnpj
        
    except Exception as e:
        print(f"❌ Erro ao extrair CNPJ: {e}")
        return None


def extrair_dados_guia_iss(pdf_path):
    """
    Extrai dados da Guia de ISS.
    - Número: após "Nº DA GUIA:"
    - Data:   após "DATA DE EMISSÃO/CÁLCULO"
    Retorna dicionário com 'data' e 'numero'.
    """
    try:
        print("  🔍 Extraindo dados da Guia de ISS...")
        texto = extrair_texto_completo_pdf(pdf_path)

        # Número: logo após "Nº DA GUIA:"
        numero = None
        match = re.search(r'N[°º]\s*DA\s*GUIA\s*[:\s]+(\d+)', texto, re.IGNORECASE)
        if match:
            numero = str(int(match.group(1)))  # remove zeros à esquerda

        # Data: logo após "DATA DE EMISSÃO/CÁLCULO"
        data = None
        match = re.search(
            r'DATA\s+DE\s+EMISS[ÃA]O[/\s]*C[ÁA]LCULO\s*[:\s]+(\d{2}/\d{2}/\d{4})',
            texto, re.IGNORECASE
        )
        if match:
            data = match.group(1)
        else:
            data = ocr_utils.extrair_data(texto)  # fallback genérico

        if data:
            print(f"  ✅ Data: {data}")
        else:
            print("  ⚠️ Data não encontrada")

        if numero:
            print(f"  ✅ Número Guia ISS: {numero}")
        else:
            print("  ⚠️ Número da guia não encontrado")

        return {'data': data, 'numero': numero}

    except Exception as e:
        print(f"❌ Erro ao extrair dados da guia ISS: {e}")
        return {'data': None, 'numero': None}


def extrair_dados_consulta(pdf_path):
    """
    Extrai dados da Consulta de Optante.
    - Data: após "Data da consulta:"
    - CNPJ: após "CNPJ:" — só dígitos, sempre 14
    Retorna dicionário com 'data' e 'numero'.
    """
    try:
        print("  🔍 Extraindo dados da Consulta de Optante...")
        texto = extrair_texto_completo_pdf(pdf_path)

        # Data: logo após "Data da consulta:"
        data = None
        match = re.search(r'Data\s+da\s+consulta\s*[:\s]+(\d{2}/\d{2}/\d{4})', texto, re.IGNORECASE)
        if match:
            data = match.group(1)
        else:
            data = ocr_utils.extrair_data(texto)

        # CNPJ: logo após "CNPJ:" — remove tudo que não for dígito, garante 14 dígitos
        cnpj = None
        match = re.search(r'CNPJ\s*[:\s]+([0-9.\-/]+)', texto, re.IGNORECASE)
        if match:
            apenas_digitos = re.sub(r'\D', '', match.group(1))
            if len(apenas_digitos) == 14:
                cnpj = apenas_digitos
            else:
                print(f"  ⚠️ CNPJ encontrado mas com {len(apenas_digitos)} dígitos: '{apenas_digitos}'")

        if data:
            print(f"  ✅ Data: {data}")
        else:
            print("  ⚠️ Data não encontrada")

        if cnpj:
            print(f"  ✅ CNPJ: {cnpj}")
        else:
            print("  ⚠️ CNPJ não encontrado")

        return {'data': data, 'numero': cnpj}

    except Exception as e:
        print(f"❌ Erro ao extrair dados da consulta: {e}")
        return {'data': None, 'numero': None}


def extrair_dados_cnpj(pdf_path):
    """
    Extrai dados do Cadastro Nacional de Pessoa Jurídica.
    - Data: após "Emitido no dia"
    - CNPJ: linha logo abaixo de "NÚMERO DE INSCRIÇÃO" — só dígitos, sempre 14
    Retorna dicionário com 'data' e 'numero'.
    """
    try:
        print("  🔍 Extraindo dados do CNPJ...")
        texto = extrair_texto_completo_pdf(pdf_path)

        # Data: logo após "Emitido no dia"
        data = None
        match = re.search(r'Emitido\s+no\s+dia\s+(\d{2}/\d{2}/\d{4})', texto, re.IGNORECASE)
        if match:
            data = match.group(1)
        else:
            data = ocr_utils.extrair_data(texto)

        # CNPJ: o que vem logo após "NÚMERO DE INSCRIÇÃO" (pode estar na mesma linha ou na próxima)
        cnpj = None
        match = re.search(
            r'N[ÚU]MERO\s+DE\s+INSCRI[ÇC][ÃA]O\s*[:\s]*([0-9.\-/\s]+)',
            texto, re.IGNORECASE
        )
        if match:
            apenas_digitos = re.sub(r'\D', '', match.group(1))[:14]  # pega só os primeiros 14
            if len(apenas_digitos) == 14:
                cnpj = apenas_digitos
            else:
                print(f"  ⚠️ CNPJ encontrado mas com {len(apenas_digitos)} dígitos: '{apenas_digitos}'")

        if data:
            print(f"  ✅ Data: {data}")
        else:
            print("  ⚠️ Data não encontrada")

        if cnpj:
            print(f"  ✅ CNPJ: {cnpj}")
        else:
            print("  ⚠️ CNPJ não encontrado")

        return {'data': data, 'numero': cnpj}

    except Exception as e:
        print(f"❌ Erro ao extrair dados do CNPJ: {e}")
        return {'data': None, 'numero': None}


def extrair_data_extrato(pdf_path):
    """
    Extrai data de um extrato bancário.
    """
    try:
        print("  🔍 Extraindo data do extrato...")
        texto = extrair_texto_completo_pdf(pdf_path)
        data  = ocr_utils.extrair_data(texto)
        
        if data:
            print(f"  ✅ Data: {data}")
        else:
            print("  ⚠️ Data não encontrada")
        
        return data
        
    except Exception as e:
        print(f"❌ Erro ao extrair data do extrato: {e}")
        return None


# ===== TESTES =====

if __name__ == "__main__":
    print("="*70)
    print("Testando funções de PDF com PyMuPDF")
    print("="*70)
    
    if not os.path.exists(config.DOCUMENTOS_DIR):
        print(f"\n⚠️ Pasta de documentos não encontrada: {config.DOCUMENTOS_DIR}")
        print("Crie a pasta e adicione alguns PDFs para testar")
    else:
        pdfs = [f for f in os.listdir(config.DOCUMENTOS_DIR) if f.lower().endswith('.pdf')]
        
        if pdfs:
            print(f"\n📁 Encontrados {len(pdfs)} arquivos PDF")
            print(f"Testando com o primeiro: {pdfs[0]}")
            
            pdf_teste = os.path.join(config.DOCUMENTOS_DIR, pdfs[0])
            
            print("\n1️⃣ Testando renderização...")
            img = renderizar_primeira_pagina_pdf(pdf_teste)
            if img:
                print(f"   ✅ PDF renderizado: {img.size} pixels, modo {img.mode}")
            else:
                print(f"   ❌ Falha ao renderizar")
            
            print("\n2️⃣ Testando extração de texto...")
            texto = extrair_texto_completo_pdf(pdf_teste)
            if texto:
                print(f"   ✅ Texto extraído: {len(texto)} caracteres")
                print(f"   Primeiros 100 chars: {texto[:100]}...")
            else:
                print(f"   ⚠️ Nenhum texto extraído")
        else:
            print("\n⚠️ Nenhum PDF encontrado na pasta documentos/")
    
    print("\n" + "="*70)
    print("✅ Testes concluídos!")
    print("="*70)