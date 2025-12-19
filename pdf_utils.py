"""
Funções para manipulação de arquivos PDF
"""

import os
from pdf2image import convert_from_path
from PIL import Image
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
        
        # Converte apenas a primeira página
        imagens = convert_from_path(
            pdf_path,
            dpi=dpi,
            first_page=1,
            last_page=1,
            poppler_path=config.POPPLER_PATH
        )
        
        if imagens:
            return imagens[0]
        else:
            print(f"❌ Nenhuma página encontrada no PDF: {pdf_path}")
            return None
            
    except Exception as e:
        print(f"❌ Erro ao renderizar PDF: {e}")
        return None


def processar_capa_especial(pdf_path):
    """
    Processa a capa com regra especial:
    - Renderiza primeira página
    - Localiza "Tribunal de Contas do Estado de São Paulo"
    - Corta tudo acima dessa linha
    
    Args:
        pdf_path: Caminho do arquivo PDF da capa
        
    Returns:
        Objeto PIL.Image processado ou None
    """
    try:
        print("  📄 Renderizando capa...")
        imagem = renderizar_primeira_pagina_pdf(pdf_path)
        
        if not imagem:
            return None
        
        print("  🔍 Procurando texto 'Tribunal de Contas'...")
        
        # Texto a procurar (normalizado, case-insensitive)
        texto_busca = "Tribunal de Contas do Estado de São Paulo"
        
        # Localiza o texto na imagem
        coords = ocr_utils.localizar_texto_na_imagem(imagem, texto_busca)
        
        if coords:
            x, y, w, h = coords
            print(f"  ✅ Texto encontrado na posição Y={y}")
            
            # Corta a imagem: mantém do Y encontrado até o final
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
    
    Args:
        pdf_path: Caminho do arquivo PDF
        
    Returns:
        Objeto PIL.Image da primeira página
    """
    return renderizar_primeira_pagina_pdf(pdf_path)


def salvar_imagem_temporaria(imagem, prefixo="temp"):
    """
    Salva imagem temporariamente para uso posterior
    
    Args:
        imagem: Objeto PIL.Image
        prefixo: Prefixo do nome do arquivo
        
    Returns:
        Caminho do arquivo salvo
    """
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
    
    Args:
        pdf_path: Caminho do arquivo PDF
        
    Returns:
        String com todo o texto extraído
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
    Extrai dados específicos de uma Nota de Empenho
    
    Args:
        pdf_path: Caminho do PDF da Nota de Empenho
        
    Returns:
        Dicionário com 'data' e 'numero'
    """
    try:
        print("  🔍 Extraindo dados da Nota de Empenho...")
        texto = extrair_texto_completo_pdf(pdf_path)
        
        data = ocr_utils.extrair_data(texto)
        numero = ocr_utils.extrair_numero_documento(texto)
        
        if data:
            print(f"  ✅ Data: {data}")
        else:
            print("  ⚠️ Data não encontrada")
        
        if numero:
            print(f"  ✅ Número: {numero}")
        else:
            print("  ⚠️ Número não encontrado")
        
        return {
            'data': data,
            'numero': numero
        }
        
    except Exception as e:
        print(f"❌ Erro ao extrair dados da NE: {e}")
        return {'data': None, 'numero': None}


def extrair_dados_ordem_bancaria(pdf_path):
    """
    Extrai dados específicos de uma Ordem Bancária
    
    Args:
        pdf_path: Caminho do PDF da Ordem Bancária
        
    Returns:
        Dicionário com 'data' e 'numero'
    """
    try:
        print("  🔍 Extraindo dados da Ordem Bancária...")
        texto = extrair_texto_completo_pdf(pdf_path)
        
        data = ocr_utils.extrair_data(texto)
        numero = ocr_utils.extrair_numero_documento(texto)
        
        if data:
            print(f"  ✅ Data: {data}")
        else:
            print("  ⚠️ Data não encontrada")
        
        if numero:
            print(f"  ✅ Número: {numero}")
        else:
            print("  ⚠️ Número não encontrado")
        
        return {
            'data': data,
            'numero': numero
        }
        
    except Exception as e:
        print(f"❌ Erro ao extrair dados da OB: {e}")
        return {'data': None, 'numero': None}


def extrair_dados_nota_fiscal(pdf_path):
    """
    Extrai dados específicos de uma Nota Fiscal
    
    Args:
        pdf_path: Caminho do PDF da Nota Fiscal
        
    Returns:
        Dicionário com 'data', 'numero' e 'empresa'
    """
    try:
        print("  🔍 Extraindo dados da Nota Fiscal...")
        texto = extrair_texto_completo_pdf(pdf_path)
        
        data = ocr_utils.extrair_data(texto)
        numero = ocr_utils.extrair_numero_documento(texto)
        empresa = ocr_utils.extrair_nome_empresa(texto)
        
        if data:
            print(f"  ✅ Data: {data}")
        else:
            print("  ⚠️ Data não encontrada")
        
        if numero:
            print(f"  ✅ Número: {numero}")
        else:
            print("  ⚠️ Número não encontrado")
        
        if empresa:
            print(f"  ✅ Empresa: {empresa}")
        else:
            print("  ⚠️ Nome da empresa não encontrado")
        
        return {
            'data': data,
            'numero': numero,
            'empresa': empresa
        }
        
    except Exception as e:
        print(f"❌ Erro ao extrair dados da NF: {e}")
        return {'data': None, 'numero': None, 'empresa': None}


def extrair_cnpj_documento(pdf_path):
    """
    Extrai CNPJ de um documento
    
    Args:
        pdf_path: Caminho do PDF
        
    Returns:
        String com CNPJ formatado ou None
    """
    try:
        print("  🔍 Extraindo CNPJ...")
        texto = extrair_texto_completo_pdf(pdf_path)
        
        cnpj = ocr_utils.extrair_cnpj(texto)
        
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
    Extrai dados específicos de uma Guia de ISS
    
    Args:
        pdf_path: Caminho do PDF da Guia
        
    Returns:
        Dicionário com 'data' e 'numero'
    """
    try:
        print("  🔍 Extraindo dados da Guia de ISS...")
        texto = extrair_texto_completo_pdf(pdf_path)
        
        data = ocr_utils.extrair_data(texto)
        numero = ocr_utils.extrair_numero_guia_iss(texto)
        
        if data:
            print(f"  ✅ Data: {data}")
        else:
            print("  ⚠️ Data não encontrada")
        
        if numero:
            print(f"  ✅ Número: {numero}")
        else:
            print("  ⚠️ Número não encontrado")
        
        return {
            'data': data,
            'numero': numero
        }
        
    except Exception as e:
        print(f"❌ Erro ao extrair dados da guia ISS: {e}")
        return {'data': None, 'numero': None}


def extrair_data_extrato(pdf_path):
    """
    Extrai data de um extrato bancário
    
    Args:
        pdf_path: Caminho do PDF do extrato
        
    Returns:
        String com a data ou None
    """
    try:
        print("  🔍 Extraindo data do extrato...")
        texto = extrair_texto_completo_pdf(pdf_path)
        
        data = ocr_utils.extrair_data(texto)
        
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
    print("Testando funções de PDF...")
    
    # Verifica se a pasta de documentos existe
    if not os.path.exists(config.DOCUMENTOS_DIR):
        print(f"⚠️ Pasta de documentos não encontrada: {config.DOCUMENTOS_DIR}")
        print("Crie a pasta e adicione alguns PDFs para testar")
    else:
        # Lista arquivos PDF na pasta
        pdfs = [f for f in os.listdir(config.DOCUMENTOS_DIR) if f.lower().endswith('.pdf')]
        
        if pdfs:
            print(f"\n📁 Encontrados {len(pdfs)} arquivos PDF")
            print(f"Testando com o primeiro: {pdfs[0]}")
            
            pdf_teste = os.path.join(config.DOCUMENTOS_DIR, pdfs[0])
            
            # Testa renderização
            img = renderizar_primeira_pagina_pdf(pdf_teste)
            if img:
                print(f"✅ PDF renderizado com sucesso: {img.size}")
            
            # Testa extração de texto
            texto = extrair_texto_completo_pdf(pdf_teste)
            if texto:
                print(f"✅ Texto extraído: {len(texto)} caracteres")
                print(f"Primeiros 100 chars: {texto[:100]}...")
        else:
            print("⚠️ Nenhum PDF encontrado na pasta documentos/")
    
    print("\n✅ Testes concluídos!")