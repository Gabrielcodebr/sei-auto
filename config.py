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
import shutil
import sys


# =====================================================================
# 1. CAMINHOS E AMBIENTE
# ---------------------------------------------------------------------
# Estes caminhos funcionam nos DOIS modos:
#   - Rodando pelo .bat / "python main_gui.py" (modo desenvolvimento)
#   - Rodando pelo SeiAuto.exe (modo empacotado / distribuível)
#
# Em ambos, BASE_DIR é a pasta onde o usuário enxerga o app, e é lá
# que ficam documentos/, pipeline_config.json, ordem_manual.json, etc.
# =====================================================================

def _base_dir():
    """Pasta raiz do app.

    Quando empacotado (.exe via PyInstaller), aponta para a pasta onde
    está o executável — que é onde o usuário coloca os arquivos e edita
    configs. NÃO usamos sys._MEIPASS aqui de propósito: aquela pasta é
    temporária e some quando o exe fecha.
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def _tesseract_path():
    """Localiza o tesseract.exe tentando, em ordem:

      1. Embutido ao lado do exe/script (Tesseract-OCR/tesseract.exe)
         — usado quando distribuímos o Tesseract junto.
      2. Instalação por usuário (%LOCALAPPDATA%\\Programs\\Tesseract-OCR).
      3. Instalação global (C:\\Program Files\\Tesseract-OCR).
      4. No PATH do sistema (retorna 'tesseract' e deixa o SO achar).
    """
    base = _base_dir()
    candidatos = [
        os.path.join(base, "Tesseract-OCR", "tesseract.exe"),
        os.path.join(
            os.environ.get("LOCALAPPDATA", ""),
            "Programs", "Tesseract-OCR", "tesseract.exe",
        ),
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ]
    for c in candidatos:
        if c and os.path.exists(c):
            return c
    return "tesseract"  # confia no PATH


# Pasta raiz do projeto (calculada automaticamente, não mexer)
BASE_DIR = _base_dir()

# Caminho do executável do Tesseract OCR (detectado automaticamente)
TESSERACT_PATH = _tesseract_path()

# Pasta onde estão os documentos numerados do processo
DOCUMENTOS_DIR = os.path.join(BASE_DIR, "documentos")

# Garante que a pasta de documentos exista (na primeira execução do exe
# o usuário ainda não a criou — queremos que ela já apareça pra ele).
try:
    os.makedirs(DOCUMENTOS_DIR, exist_ok=True)
except OSError:
    # Não é fatal aqui — a validação abaixo mostra a mensagem certa, e a
    # GUI avisa quando o usuário tentar adicionar arquivos.
    pass


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

# Data usada em QUALQUER campo de data quando não foi possível extrair/
# informar uma data real. Propositalmente "impossível" (não é a data de
# hoje) para ficar óbvio na revisão manual que precisa ser corrigida.
# O bot NUNCA deve inserir o texto literal "[DATA]" no SEI.
DATA_FALLBACK_PADRAO = "01/01/1999"


# =====================================================================
# 5. TIPOS DE DOCUMENTO, ASSINATURAS E TEMPLATE DE DESPACHO
# ---------------------------------------------------------------------
# Migraram para pipeline.py / pipeline_config.json (aba "Pipeline de
# Documentos" na GUI). Cada tipo de documento agora é um "passo" do
# pipeline, com categoria (fixo inicial / ciclo / fixo final), ordem
# de execução, detecção pelo nome do arquivo, e se é um passo "ativo"
# ou não — tudo editável sem tocar em código.
# =====================================================================


# =====================================================================
# 6. VALIDAÇÃO
# =====================================================================

def validar_configuracoes():
    """Valida se as configurações estão corretas"""
    erros = []

    # Verifica Tesseract. Se veio do PATH, checa via shutil.which em vez
    # de os.path.exists (que só funciona com caminho absoluto).
    if TESSERACT_PATH == "tesseract":
        if shutil.which("tesseract") is None:
            erros.append(
                "Tesseract não encontrado. Instale-o ou coloque o "
                "tesseract.exe ao lado do programa (pasta 'Tesseract-OCR')."
            )
    elif not os.path.exists(TESSERACT_PATH):
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


# =====================================================================
# 7. OVERRIDES DO USUÁRIO (via GUI)
# ---------------------------------------------------------------------
# Se existir user_config.json na raiz do projeto, seus valores
# sobrescrevem os defaults acima. Criado e editado pela interface
# gráfica (main_gui.py). Seguro: se não existir, nada muda.
# =====================================================================
try:
    from gui.config_manager import _apply_overrides as _sei_apply_overrides
    _sei_apply_overrides(globals())
except Exception:
    pass