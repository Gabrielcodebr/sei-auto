"""
Configurações do projeto de automação SEI
==========================================

Este arquivo é o "painel de controle" do bot. Quase tudo que pode mudar
no SEI ou no seu ambiente está aqui. Em geral, você NÃO precisa mexer
em outros arquivos — só editar valores aqui, salvar e rodar.

Seções:
  1. Caminhos e ambiente
  2. Configurações de OCR e imagem
  3. Coordenadas de tela (cliques do bot)
  4. Tempos de espera
  5. Configuração dos tipos de documento
  6. Assinaturas da Planilha de Pesquisa de Preço
  7. Template do despacho de aprovação
  8. Validação
"""

import os


# =====================================================================
# 1. CAMINHOS E AMBIENTE
# ---------------------------------------------------------------------
# EDITE AQUI se mudar a instalação do Tesseract ou a pasta dos
# documentos do processo.
# =====================================================================

# Caminho do executável do Tesseract OCR
TESSERACT_PATH = r"C:\Users\Gabriel Fatec Itu\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"

# Caminho da pasta bin do Poppler (não é mais necessário — usamos PyMuPDF)
# POPPLER_PATH = r"C:\Programas\poppler-25.12.0\Library\bin"

# Pasta raiz do projeto (calculada automaticamente, não mexer)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Pasta onde estão os documentos numerados do processo
DOCUMENTOS_DIR = os.path.join(BASE_DIR, "documentos")


# =====================================================================
# 2. CONFIGURAÇÕES DE OCR E IMAGEM
# ---------------------------------------------------------------------
# EDITE AQUI se o OCR estiver lendo errado (aumentar PDF_DPI) ou se
# quiser mudar o idioma de leitura.
# =====================================================================

# Idioma do Tesseract (português)
OCR_LANGUAGE = "por"

# Confiança mínima para aceitar resultado do OCR (0-100)
OCR_MIN_CONFIDENCE = 60

# DPI para renderização de PDF (mais = melhor OCR, mais lento)
PDF_DPI = 200

# Formato de imagem para print
IMAGE_FORMAT = "PNG"


# =====================================================================
# 3. COORDENADAS DE TELA
# ---------------------------------------------------------------------
# EDITE AQUI quando o SEI mudar de layout / o bot clicar no lugar
# errado. Use os scripts em calibracao/ para descobrir as coordenadas
# novas. Resolução base testada: 1600x900 com Firefox maximizado.
# =====================================================================

# --- Tela principal ---
COORD_BTN_INCLUIR_DOC   = (354, 180)   # Botão "Incluir Documento"
COORD_BARRA_PESQUISA    = (761, 380)   # Campo de busca de tipo de documento
COORD_BTN_SALVAR_FORM   = (1466, 757)  # Botão "Salvar" do formulário
COORD_AREA_EDICAO       = (817, 589)   # Centro do editor (popup maximizado)

# --- Árvore do processo (ícone da Nota de Empenho) ---
COORD_ICONE_NE_ARVORE_DMPP  = (49, 246)   # 3º arquivo na árvore (DMPP)
COORD_ICONE_NE_ARVORE_UFIEC = (48, 304)   # 5º arquivo na árvore (UFIEC)

# --- Formulário de documento INTERNO ---
COORD_CAMPO_DESCRICAO_INTERNO   = (417, 513)
COORD_CAMPO_NOME_ARVORE_INTERNO = (425, 568)
COORD_RADIO_PUBLICO             = (1120, 668)

# --- Formulário de documento EXTERNO ---
COORD_DROPDOWN_TIPO_EXTERNO      = (451, 351)
COORD_CAMPO_DATA                 = (1038, 357)
COORD_CAMPO_NUMERO               = (406, 413)
COORD_CAMPO_NOME_ARVORE          = (616, 413)
COORD_RADIO_NATO_DIGITAL         = (411, 482)
COORD_RADIO_DIGITALIZADO         = (410, 503)
COORD_DROPDOWN_TIPO_CONFERENCIA  = (1056, 478)
COORD_BTN_ANEXAR_ARQUIVO         = (406, 608)
COORD_RADIO_PUBLICO_EXTERNO      = (1114, 541)

# --- Coordenadas auxiliares (popups e cliques pontuais) ---
# Região onde o SEI mostra o popup "documento similar" (x, y, largura, altura)
REGIAO_POPUP_SIMILAR    = (400, 300, 800, 300)
# Botão OK do popup "documento similar"
COORD_POPUP_OK_SIMILAR  = (861, 526)
# Click pra refocar o editor ao colar despacho com link
COORD_REFOCO_EDITOR     = (934, 496)


# =====================================================================
# 4. TEMPOS DE ESPERA (segundos)
# ---------------------------------------------------------------------
# EDITE AQUI se o SEI estiver lento (aumentar) ou rápido (diminuir).
# Tempos abaixo de 1s ficam direto no código por serem timing fino.
# =====================================================================

# Pausa global do pyautogui (entre TODA ação)
PAUSE_BETWEEN_ACTIONS = 0.5

# Espera padrão genérica (quando não há tempo específico)
WAIT_FOR_ELEMENT = 1.0

# Tempo máximo de espera para upload (em segundos)
MAX_UPLOAD_WAIT = 10

# Tempos específicos por situação. Se algum lugar estiver dando erro
# por carregamento lento, aumente o valor correspondente aqui.
TEMPOS = {
    'pos_pesquisa_externo':   1.5,  # após selecionar "Externo" na barra de busca
    'pos_salvar_form':        2.5,  # após clicar Salvar (esperar editor abrir)
    'pos_salvar_editor':      3.0,  # após Ctrl+Alt+S no editor
    'recarregar_tela':        2.0,  # entre documentos (tela principal recarregando)
    'aguardar_form_carregar': 3.0,  # após abrir formulário interno
    'pos_anexo_upload':       5.0,  # após upload de arquivo externo
    'pos_click_salvar_doc04': 2.0,  # delay específico do despacho de NE
}


# =====================================================================
# 5. CONFIGURAÇÃO DOS TIPOS DE DOCUMENTO
# ---------------------------------------------------------------------
# EDITE AQUI se o SEI mudar o NOME de algum tipo de documento ou se
# quiser ajustar a descrição/nome na árvore que o bot preenche.
#
# Campos possíveis em cada entrada:
#   busca         - texto digitado na barra de busca de tipos
#   descricao     - vai no campo "Descrição" do formulário interno
#   nome_arvore   - vai no campo "Nome na Árvore"
#   tipo_externo  - vai no dropdown de tipo de documento externo
# =====================================================================

DOCUMENTOS = {
    'capa': {
        'busca':       'Informacao',
        'descricao':   'Capa padrão imprensa oficial',
        'nome_arvore': 'Capa',
    },
    'solicitacao': {
        'busca':       'Solicitacao',
        'descricao':   'Solicitação de adiantamento',
        'nome_arvore': 'adiantamento',
    },
    'memorando_justificativa': {
        'busca':       'Memorando',
        'descricao':   'Memorando/Justificativa',
        'nome_arvore': 'Justificativa',
    },
    'nota_empenho': {
        'busca':        'Externo',
        'tipo_externo': 'Nota de empenho',
    },
    'despacho_aprovacao_ne': {
        'busca':       'Despacho',
        'descricao':   'Aprovação de NE',
        'nome_arvore': 'Aprovação de NE',
    },
    'ordem_bancaria': {
        'busca':        'Externo',
        'tipo_externo': 'Ordem bancaria',
    },
    'quadro_comparativo': {
        'busca':       'Planilha',
        'descricao':   'Quadro comparativo',
        'nome_arvore': 'Quadro comparativo',
    },
    'nota_fiscal': {
        'busca':        'Externo',
        'tipo_externo': 'Nota Fiscal',
    },
    'comprovante_fiscal': {
        'busca':        'Externo',
        'tipo_externo': 'Comprovante',
    },
    'declaracao_recebimento': {
        'busca':     'Declaracao',
        'descricao': 'Declaração de Recebimento, Conformidade e Destinação',
        # nome_arvore aqui é dinâmico: vem do nome da empresa do ciclo
    },
    'consulta_optante': {
        'busca':        'Externo',
        'tipo_externo': 'Consulta',
    },
    'cnpj': {
        'busca':        'Externo',
        'tipo_externo': 'Cadastro Nacional De Pessoa Jurídica',
    },
    'guia_iss': {
        'busca':        'Externo',
        'tipo_externo': 'Guia de recolhimento',
    },
    'comprovante_iss': {
        'busca':        'Externo',
        'tipo_externo': 'Comprovante',
    },
    'balancete': {
        'busca':       'Balancete',
        'descricao':   '',
        'nome_arvore': '',
    },
    'extrato_bancario': {
        'busca':            'Externo',
        'tipo_externo':     'Extrato',
        'nome_arvore_fixo': 'Bancário',
    },
    'conciliacao_contabil': {
        'busca':       'Conciliacao',
        'descricao':   'Conciliação bancária',
        'nome_arvore': 'Conciliação bancária',
    },
    'declaracao_encerramento': {
        'busca':       'Declaracao',
        'descricao':   'Declaração de encerramento',
        'nome_arvore': 'Encerramento',
    },
}


# =====================================================================
# 6. ASSINATURAS DA PLANILHA DE PESQUISA DE PREÇO
# ---------------------------------------------------------------------
# EDITE AQUI para adicionar/remover assinantes. O bot procura essas
# assinaturas na planilha e corta tudo que vier depois delas (útil pra
# remover páginas vazias geradas pelo sistema).
# Formato: (NOME_COMPLETO_MAIÚSCULO, CPF_COM_FORMATO)
# =====================================================================

ASSINATURAS_PLANILHA_PRECO = [
    ('RODRIGO BARBIERI', '230599118-51'),  # DMPP
    ('ROSANA METZNER',   '066313968-67'),  # UFIEC
]


# =====================================================================
# 7. TEMPLATE DO DESPACHO DE APROVAÇÃO
# ---------------------------------------------------------------------
# EDITE AQUI para mudar o texto do despacho. Os marcadores
# {numero_ne}, {link_ne} e {data_ne} são preenchidos automaticamente.
# =====================================================================

DESPACHO_APROVACAO_TEMPLATE = """Aprova-se Nota de Empenho {numero_ne}, documento: {link_ne}

São Paulo, {data_ne}

WILLIAN DE OLIVEIRA SALAZAR
Coordenador de Departamento de Orçamento e Finanças – COF"""


# =====================================================================
# 8. VALIDAÇÃO
# =====================================================================

def validar_configuracoes():
    """Valida se as configurações estão corretas"""
    erros = []

    # Verifica Tesseract
    if not os.path.exists(TESSERACT_PATH):
        erros.append(f"Tesseract não encontrado em: {TESSERACT_PATH}")

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
    validar_configuracoes()
