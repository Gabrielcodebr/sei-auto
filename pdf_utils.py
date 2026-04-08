"""
Funções para manipulação de arquivos PDF
ATUALIZADO: Usa PyMuPDF (fitz) ao invés de pdf2image
Não precisa mais do Poppler!

VERSÃO 2.0 - Correções:
- Data da Nota de Empenho: extrai após "Data Emissão"
- Data da Ordem Bancária: extrai após "Data Pagamento"
- Resolução dos prints reduzida em 20%
"""

import os
import re
import fitz  # PyMuPDF
from PIL import Image
import io
import config
import ocr_utils


# ============== CONFIGURAÇÃO DE RESOLUÇÃO ==============
# Fator de redução: 0.8 = 80% do original (20% menor)
RESOLUTION_FACTOR = 0.8


def renderizar_primeira_pagina_pdf(pdf_path, dpi=None):
    """
    Renderiza a primeira página de um PDF como imagem
    
    Args:
        pdf_path: Caminho do arquivo PDF
        dpi: Resolução (usa config.PDF_DPI * RESOLUTION_FACTOR se None)
        
    Returns:
        Objeto PIL.Image da primeira página
    """
    try:
        if dpi is None:
            # Aplica redução de 20% na resolução
            dpi = int(config.PDF_DPI * RESOLUTION_FACTOR)
        
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
        
        print(f"  📐 Resolução: {dpi} DPI (reduzido em {int((1-RESOLUTION_FACTOR)*100)}%)")
        
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


def renderizar_pagina_pdf(pdf_path, pagina_idx, dpi=None):
    """
    Renderiza uma página específica de um PDF como imagem PIL.
    """
    try:
        if dpi is None:
            dpi = int(config.PDF_DPI * RESOLUTION_FACTOR)

        doc = fitz.open(pdf_path)
        if pagina_idx >= len(doc):
            doc.close()
            return None

        page = doc[pagina_idx]
        zoom = dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        img_data = pix.tobytes("png")
        imagem = Image.open(io.BytesIO(img_data))
        doc.close()
        return imagem

    except Exception as e:
        print(f"❌ Erro ao renderizar página {pagina_idx} do PDF: {e}")
        return None


def _empilhar_imagens_verticalmente(imagens):
    """
    Concatena várias imagens PIL verticalmente em uma única imagem.
    A largura final é a maior largura entre as imagens; imagens menores
    são centralizadas horizontalmente sobre fundo branco.
    """
    if not imagens:
        return None
    if len(imagens) == 1:
        return imagens[0]

    largura_final = max(img.width for img in imagens)
    altura_final  = sum(img.height for img in imagens)

    resultado = Image.new('RGB', (largura_final, altura_final), 'white')
    y_offset = 0
    for img in imagens:
        if img.mode != 'RGB':
            img = img.convert('RGB')
        x_offset = (largura_final - img.width) // 2
        resultado.paste(img, (x_offset, y_offset))
        y_offset += img.height

    return resultado


# Assinaturas conhecidas (nome + CPF) para corte da Planilha de Pesquisa
# de Preço. Cada item é uma tupla (nome, cpf).
ASSINATURAS_PLANILHA_PRECO = [
    ("RODRIGO BARBIERI", "230599118-51"),  # DMPP
    ("ROSANA METZNER",   "066313968-67"),  # UFIEC
]


def processar_planilha_pesquisa_preco(pdf_path):
    """
    Processa a Planilha de Pesquisa de Preço (Quadro Comparativo).

    Regras:
    - Renderiza todas as páginas do PDF.
    - Em cada página, procura por uma das assinaturas conhecidas
      (nome + CPF) — ver ASSINATURAS_PLANILHA_PRECO.
    - Quando encontra a assinatura em uma página, mantém tudo até o
      final dessa linha e descarta o restante (e todas as páginas
      seguintes — útil quando o sistema gera páginas vazias extras).
    - Concatena as páginas resultantes verticalmente em uma única imagem
      (compatível com o editor do SEI, que cola uma única imagem).
    - Se a assinatura não for encontrada em nenhuma página, retorna
      todas as páginas concatenadas (fallback seguro).
    """
    try:
        print("  📄 Processando Planilha de Pesquisa de Preço (multi-página)...")

        doc = fitz.open(pdf_path)
        total_paginas = len(doc)
        doc.close()

        if total_paginas == 0:
            print("  ❌ PDF sem páginas")
            return None

        print(f"  📑 PDF possui {total_paginas} página(s)")

        paginas_processadas = []
        assinatura_encontrada = False

        for idx in range(total_paginas):
            print(f"  🖼️  Renderizando página {idx + 1}/{total_paginas}...")
            imagem = renderizar_pagina_pdf(pdf_path, idx)
            if imagem is None:
                continue

            # Procura qualquer uma das assinaturas conhecidas nesta página
            print(f"  🔍 Procurando assinatura na página {idx + 1}...")
            coords_nome = None
            coords_cpf  = None
            assinante   = None

            for nome, cpf in ASSINATURAS_PLANILHA_PRECO:
                c_cpf  = ocr_utils.localizar_texto_na_imagem(imagem, cpf)
                c_nome = ocr_utils.localizar_texto_na_imagem(imagem, nome)
                if c_cpf or c_nome:
                    coords_cpf  = c_cpf
                    coords_nome = c_nome
                    assinante   = nome
                    break

            if coords_cpf or coords_nome:
                # Determina o Y final do recorte: pega o MAIOR y+h entre os
                # encontrados, para garantir que tanto nome quanto CPF
                # fiquem visíveis na imagem final.
                y_corte = 0
                if coords_nome:
                    _, y, _, h = coords_nome
                    y_corte = max(y_corte, y + h)
                if coords_cpf:
                    _, y, _, h = coords_cpf
                    y_corte = max(y_corte, y + h)

                # Se só achou o nome, adiciona uma margem para incluir o
                # CPF que normalmente fica logo abaixo.
                if coords_nome and not coords_cpf:
                    _, _, _, h = coords_nome
                    y_corte += int(h * 2.5)

                # Pequena margem inferior para não cortar rente
                margem = 15
                y_corte = min(imagem.height, y_corte + margem)

                largura, altura = imagem.size
                imagem_cortada = imagem.crop((0, 0, largura, y_corte))
                print(f"  ✂️ Assinatura '{assinante}' encontrada na página "
                      f"{idx + 1}: cortando de {altura}px para {y_corte}px")
                paginas_processadas.append(imagem_cortada)
                assinatura_encontrada = True
                break  # ignora páginas seguintes (vazias/sobras)
            else:
                print(f"  ➕ Página {idx + 1} sem assinatura — incluindo inteira")
                paginas_processadas.append(imagem)

        if not assinatura_encontrada:
            print("  ⚠️ Assinatura não encontrada em nenhuma página — "
                  "usando todas as páginas sem corte")

        if not paginas_processadas:
            print("  ❌ Nenhuma página renderizada")
            return None

        print(f"  🧩 Empilhando {len(paginas_processadas)} página(s) em uma imagem única...")
        return _empilhar_imagens_verticalmente(paginas_processadas)

    except Exception as e:
        print(f"❌ Erro ao processar planilha de pesquisa de preço: {e}")
        return None


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
        # Usa DPI maior para OCR (precisa de mais detalhe para leitura)
        imagem = renderizar_primeira_pagina_pdf(pdf_path, dpi=config.PDF_DPI)
        if imagem:
            return ocr_utils.extrair_texto_imagem(imagem)
        return ""
    except Exception as e:
        print(f"❌ Erro ao extrair texto do PDF: {e}")
        return ""


# ============== FUNÇÕES DE EXTRAÇÃO DE DATA ESPECÍFICA ==============

def extrair_data_apos_campo(texto, campo):
    """
    Extrai a data que aparece logo após um campo específico.
    
    Args:
        texto: Texto completo do documento
        campo: Campo a procurar (ex: "Data Emissão", "Data Pagamento")
    
    Returns:
        String com a data no formato DD/MM/YYYY ou None
    """
    # Padrões para encontrar o campo seguido de data
    padroes = [
        # Campo seguido por : ou espaço, depois data DD/MM/YYYY
        rf'{campo}\s*[:\s]+(\d{{2}}[/\-]\d{{2}}[/\-]\d{{4}})',
        # Campo com quebra de linha antes da data
        rf'{campo}\s*\n\s*(\d{{2}}[/\-]\d{{2}}[/\-]\d{{4}})',
        # Campo seguido por data YYYY-MM-DD (ISO)
        rf'{campo}\s*[:\s]+(\d{{4}}[/\-]\d{{2}}[/\-]\d{{2}})',
    ]
    
    for padrao in padroes:
        match = re.search(padrao, texto, re.IGNORECASE | re.MULTILINE)
        if match:
            data = match.group(1)
            # Converte YYYY-MM-DD para DD/MM/YYYY se necessário
            if re.match(r'\d{4}[-/]\d{2}[-/]\d{2}', data):
                partes = re.split(r'[-/]', data)
                data = f"{partes[2]}/{partes[1]}/{partes[0]}"
            return data
    
    return None


def extrair_dados_nota_empenho(pdf_path):
    """
    Extrai dados específicos de uma Nota de Empenho.
    - Data: DEVE estar após "Data Emissão" (não pega qualquer data)
    - Número: padrão 2025NE03848
    
    Retorna dicionário com 'data' e 'numero'.
    """
    try:
        print("  🔍 Extraindo dados da Nota de Empenho...")
        texto = extrair_texto_completo_pdf(pdf_path)
        
        # DATA: Procura especificamente após "Data Emissão"
        data = extrair_data_apos_campo(texto, r'Data\s*(?:de\s*)?Emiss[ãa]o')
        
        # Fallback: tenta "Emissão" sozinho
        if not data:
            data = extrair_data_apos_campo(texto, r'Emiss[ãa]o')
        
        # NÚMERO: padrão NE
        numero = ocr_utils.extrair_numero_documento(texto)
        
        if data:
            print(f"  ✅ Data (após 'Data Emissão'): {data}")
        else:
            print("  ⚠️ Data de emissão não encontrada")
        
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
    - Data: DEVE estar após "Data Pagamento" (não pega qualquer data)
    - Número: padrão OB (ex: 2025OB03848)
    
    Usa regex específico para padrão OB,
    com fallbacks para leituras incorretas do Tesseract (0B, 08, O8).

    Retorna dicionário com 'data' e 'numero'.
    """
    try:
        print("  🔍 Extraindo dados da Ordem Bancária...")
        texto = extrair_texto_completo_pdf(pdf_path)

        print(f"  📄 Texto extraído (primeiros 300 chars):\n{texto[:300]}")

        # DATA: Procura especificamente após "Data Pagamento"
        data = extrair_data_apos_campo(texto, r'Data\s*(?:de\s*)?Pagamento')
        
        # Fallback: tenta "Pagamento" sozinho
        if not data:
            data = extrair_data_apos_campo(texto, r'Pagamento')

        # NÚMERO: Tenta variações que o Tesseract pode gerar para "OB"
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
            print(f"  ✅ Data (após 'Data Pagamento'): {data}")
        else:
            print("  ⚠️ Data de pagamento não encontrada")

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


def extrair_dados_nota_fiscal(pdf_path):
    """
    Extrai dados específicos de uma Nota Fiscal.
    - Número: busca após "NF-e" e "Nº", remove pontos e zeros à esquerda
    Retorna dicionário com 'data' e 'numero'.
    
    NOTA: O número da NF agora é extraído do nome do arquivo no sei_automation.py,
    esta função serve como fallback.
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
            print(f"  ✅ Número NF (OCR): {numero}")
        else:
            print("  ⚠️ Número NF não encontrado via OCR")

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

        # CNPJ: procura "CNPJ" seguido de ":" e captura tudo até ter 14 dígitos
        cnpj = None
        
        # Tenta diferentes padrões
        padroes_cnpj = [
            r'CNPJ\s*[:\s]+([0-9.\-/\s]{14,25})',  # CNPJ: XX.XXX.XXX/XXXX-XX
            r'CNPJ\s*[:\s]*(\d{2}[.\s]?\d{3}[.\s]?\d{3}[/\s]?\d{4}[-\s]?\d{2})',  # Formato com pontos
            r'CNPJ[:\s]+(\d{14})',  # 14 dígitos direto
        ]
        
        for padrao in padroes_cnpj:
            match = re.search(padrao, texto, re.IGNORECASE)
            if match:
                # Remove tudo que não for dígito
                apenas_digitos = re.sub(r'\D', '', match.group(1))
                # Pega apenas os primeiros 14 dígitos
                if len(apenas_digitos) >= 14:
                    cnpj = apenas_digitos[:14]
                    break
        
        # Fallback: procura qualquer sequência de 14 dígitos após "CNPJ"
        if not cnpj:
            pos_cnpj = texto.upper().find('CNPJ')
            if pos_cnpj != -1:
                trecho = texto[pos_cnpj:pos_cnpj + 50]
                apenas_digitos = re.sub(r'\D', '', trecho)
                if len(apenas_digitos) >= 14:
                    cnpj = apenas_digitos[:14]

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
    print(f"Fator de resolução: {RESOLUTION_FACTOR} ({int((1-RESOLUTION_FACTOR)*100)}% menor)")
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