"""
Script de automação para inserção de documentos no SEI (SP)
NAVEGADOR: Firefox
"""

import os
import re
import time
import pyautogui
import pyperclip
from pathlib import Path
from docx import Document as DocxDocument
import config
import ocr_utils
import pdf_utils

# Configurações do pyautogui
pyautogui.PAUSE = config.PAUSE_BETWEEN_ACTIONS
pyautogui.FAILSAFE = True  # Mover mouse para canto superior esquerdo cancela


class SEIAutomation:
    """Classe principal para automação do SEI"""

    # =========================================================
    # COORDENADAS - TELA PRINCIPAL
    # =========================================================
    COORD_BTN_INCLUIR_DOC   = (354, 180)
    COORD_BARRA_PESQUISA    = (761, 380)
    COORD_BTN_SALVAR_FORM   = (1466, 757)
    COORD_RADIO_PUBLICO     = (1120, 668)
    COORD_AREA_EDICAO       = (817, 589)   # Popup maximizado

    # =========================================================
    # COORDENADAS - ÁRVORE DO PROCESSO
    # =========================================================
    COORD_ICONE_NE_ARVORE = (49, 246)   # Ícone da Nota de Empenho na árvore

    # =========================================================
    # COORDENADAS - FORMULÁRIO DOCUMENTO INTERNO
    # =========================================================
    COORD_CAMPO_DESCRICAO_INTERNO   = (417, 513)
    COORD_CAMPO_NOME_ARVORE_INTERNO = (425, 568)

    # =========================================================
    # COORDENADAS - FORMULÁRIO DOCUMENTO EXTERNO
    # =========================================================
    COORD_DROPDOWN_TIPO_EXTERNO      = (451, 351)
    COORD_CAMPO_DATA                 = (1038, 357)
    COORD_CAMPO_NUMERO               = (406, 413)
    COORD_CAMPO_NOME_ARVORE          = (616, 413)
    COORD_RADIO_NATO_DIGITAL         = (411, 482)
    COORD_RADIO_DIGITALIZADO         = (410, 503)
    COORD_DROPDOWN_TIPO_CONFERENCIA  = (1056, 478)
    COORD_BTN_ANEXAR_ARQUIVO         = (406, 608)
    COORD_RADIO_PUBLICO_EXTERNO      = (1114, 541)

    # =========================================================

    def __init__(self, pasta_documentos=None, pular_primeiros=0):
        """
        Args:
            pasta_documentos: Caminho da pasta com documentos
            pular_primeiros:  Número de documentos para pular (já inseridos)
        """
        self.pasta_documentos = pasta_documentos or config.DOCUMENTOS_DIR
        self.pular_primeiros  = pular_primeiros
        self.documentos       = []
        self.dados_contexto   = {}  # Dados compartilhados entre documentos

    # =========================================================
    # UTILITÁRIOS
    # =========================================================

    def aguardar(self, segundos=None):
        if segundos is None:
            segundos = config.WAIT_FOR_ELEMENT
        time.sleep(segundos)

    def carregar_documentos(self):
        """Carrega e ordena lista de documentos da pasta (ordem numérica pelo prefixo)"""
        if not os.path.exists(self.pasta_documentos):
            raise Exception(f"Pasta não encontrada: {self.pasta_documentos}")

        def chave_numerica(nome):
            """Extrai o número do início do nome para ordenação correta: 1, 2, 3... 10, 11..."""
            match = re.match(r'^(\d+)', nome)
            return int(match.group(1)) if match else 9999

        arquivos = sorted(os.listdir(self.pasta_documentos), key=chave_numerica)
        todos_docs = [
            os.path.join(self.pasta_documentos, f)
            for f in arquivos
            if f.lower().endswith(('.pdf', '.docx'))
        ]
        self.documentos = todos_docs[self.pular_primeiros:]

        print(f"\n📁 Total de documentos na pasta: {len(todos_docs)}")
        if self.pular_primeiros > 0:
            print(f"⏭️  Pulando os primeiros {self.pular_primeiros}")
        print(f"📄 Documentos a processar: {len(self.documentos)}")
        for i, doc in enumerate(self.documentos, self.pular_primeiros + 1):
            print(f"  {i}. {os.path.basename(doc)}")

        return self.documentos

    # =========================================================
    # AÇÕES BÁSICAS
    # =========================================================

    def extrair_empresa_do_nome_arquivo(self, filepath):
        """
        Extrai o nome da empresa a partir do nome do arquivo.

        Remove:
        - Prefixo numérico:  "25-"
        - Extensão:          ".pdf", ".docx"
        - Palavras-chave:    NOTA FISCAL, COMPROVANTE DE PAGAMENTO NF,
                             COMPROVANTE, CONSULTA, CADASTRO NACIONAL DE
                             PESSOA JURIDICA, ISS Empresa -
        - Número solto após keyword: ex "NOTA FISCAL 1939 ..." → remove "1939"

        Exemplos:
          "25-NOTA FISCAL 1939 MURILO CRISTOFOLETTI ARMENIO.pdf"
              → "MURILO CRISTOFOLETTI ARMENIO"
          "13-COMPROVANTE DE PAGAMENTO NF 8273 JOSÉ CARLOS ROSATI ITU.pdf"
              → "JOSÉ CARLOS ROSATI ITU"
          "17-ISS Empresa - GAMA FILTROS E REFRIGERACAO LTDA ME.pdf"
              → "GAMA FILTROS E REFRIGERACAO LTDA ME"
        """
        nome = os.path.basename(filepath)
        # Remove extensão
        nome = os.path.splitext(nome)[0]
        # Remove prefixo numérico e traço: "25-"
        nome = re.sub(r'^\d+[-\s]*', '', nome)

        # Remove keywords conhecidas (ordem importa — mais específico primeiro)
        keywords = [
            r'ISS\s+Empresa\s*[-–]\s*',
            r'COMPROVANTE\s+DE\s+PAGAMENTO\s+NF\s*',
            r'COMPROVANTE\s+DA\s+NOTA\s+FISCAL\s*',
            r'COMPROVANTE\s*',
            r'CADASTRO\s+NACIONAL\s+DE\s+PESSOA\s+JURIDICA\s*',
            r'CONSULTA\s+CNPJ\s*',
            r'CONSULTA\s+OPTANTE\s*',
            r'NOTA\s+FISCAL\s*',
            r'CONSULTA\s*',
        ]
        for kw in keywords:
            nome = re.sub(kw, '', nome, flags=re.IGNORECASE).strip()

        # Remove número solto que sobrou logo no início: "1939 MURILO..." → "MURILO..."
        nome = re.sub(r'^\d+\s*', '', nome).strip()

        print(f"  🏢 Empresa extraída do nome do arquivo: '{nome}'")
        return nome or '[EMPRESA]'

    def clicar_botao_incluir_documento(self):
        print("\n🖱️ Clicando em 'Incluir Documento'...")
        pyautogui.click(self.COORD_BTN_INCLUIR_DOC)
        self.aguardar(1.5)
        print("✅ Lista de documentos aberta")

    def pesquisar_e_selecionar_tipo_doc(self, texto_busca):
        """Pesquisa e seleciona tipo de documento na barra de busca"""
        print(f"🔍 Buscando: '{texto_busca}'")
        pyautogui.click(self.COORD_BARRA_PESQUISA)
        self.aguardar(0.5)
        pyautogui.hotkey('ctrl', 'a')
        pyautogui.write(texto_busca, interval=0.05)
        self.aguardar(0.8)
        pyautogui.press('down')
        self.aguardar(0.3)
        pyautogui.press('enter')
        self.aguardar(1.5)
        print(f"✅ Selecionado: '{texto_busca}'")

    def preencher_formulario_interno(self, descricao, nome_arvore):
        """
        Preenche os campos Descrição e Nome na Árvore do formulário
        de documento interno usando coordenadas fixas.
        """
        print("  ⏳ Aguardando formulário carregar...")
        self.aguardar(3)

        print(f"  ✏️ Preenchendo 'Descrição': {descricao}")
        pyautogui.click(self.COORD_CAMPO_DESCRICAO_INTERNO)
        self.aguardar(0.4)
        pyautogui.hotkey('ctrl', 'a')
        pyautogui.press('delete')
        self.aguardar(0.1)
        pyperclip.copy(descricao)
        pyautogui.hotkey('ctrl', 'v')
        self.aguardar(0.5)

        print(f"  ✏️ Preenchendo 'Nome na Árvore': {nome_arvore}")
        pyautogui.click(self.COORD_CAMPO_NOME_ARVORE_INTERNO)
        self.aguardar(0.4)
        pyautogui.hotkey('ctrl', 'a')
        pyautogui.press('delete')
        self.aguardar(0.1)
        pyperclip.copy(nome_arvore)
        pyautogui.hotkey('ctrl', 'v')
        self.aguardar(0.5)

        print("  ✅ Campos preenchidos!")

    def selecionar_dropdown_tipo_externo(self, tipo_documento):
        """Seleciona tipo no dropdown de documentos externos"""
        print(f"📋 Selecionando tipo externo: '{tipo_documento}'")
        pyautogui.click(self.COORD_DROPDOWN_TIPO_EXTERNO)
        self.aguardar(0.8)
        palavras = tipo_documento.split()[:3]
        pyautogui.write(' '.join(palavras), interval=0.08)
        self.aguardar(1)
        pyautogui.press('enter')
        self.aguardar(0.5)
        print("✅ Tipo selecionado")

    def preencher_campo_clicando(self, coord, texto, limpar=True):
        """Preenche campo clicando em coordenada específica"""
        pyautogui.click(coord)
        self.aguardar(0.3)
        if limpar:
            pyautogui.hotkey('ctrl', 'a')
            pyautogui.press('delete')
            self.aguardar(0.1)
        if texto:
            pyperclip.copy(str(texto))
            pyautogui.hotkey('ctrl', 'v')
            self.aguardar(0.3)

    def selecionar_nivel_acesso_publico(self, n_scrolls=6):
        """Formulários INTERNOS — rola e clica em Público"""
        print("🔓 Selecionando Nível de Acesso: Público")
        for _ in range(n_scrolls):
            pyautogui.scroll(-400)
            self.aguardar(0.2)
        pyautogui.click(self.COORD_RADIO_PUBLICO)
        self.aguardar(0.3)
        print("✅ Público selecionado")

    def selecionar_nivel_acesso_publico_externo(self):
        """Formulários EXTERNOS — usa coordenada própria calibrada"""
        print("🔓 Selecionando Nível de Acesso: Público (externo)")
        for _ in range(6):
            pyautogui.scroll(-400)
            self.aguardar(0.2)
        pyautogui.click(self.COORD_RADIO_PUBLICO_EXTERNO)
        self.aguardar(0.3)
        print("✅ Público selecionado")

    def verificar_popup_documento_similar(self, tentativas=5):
        """
        Verifica se o SEI exibiu popup de documento similar após salvar.
        Estratégia: tira screenshot da região do popup e busca texto chave.
        Como fallback, pressiona Enter pois o botão OK já fica focado por padrão.
        """
        # Região central da tela onde popups do SEI aparecem (1600x900)
        REGIAO_POPUP = (400, 300, 800, 300)  # x, y, largura, altura

        for i in range(tentativas):
            self.aguardar(0.8)
            try:
                screenshot = pyautogui.screenshot(region=REGIAO_POPUP)
                texto = ocr_utils.extrair_texto_imagem(screenshot, preprocessar=False)

                if 'deseja continuar' in texto.lower() or 'já existe' in texto.lower():
                    print("  ⚠️ Popup de documento similar detectado! Clicando OK...")
                    pyautogui.click(861, 526)
                    self.aguardar(1)
                    print("  ✅ Popup dispensado")
                    return True
            except Exception:
                pass

        # Fallback: pressiona Enter — se o popup estiver aberto o OK está focado,
        # se não estiver não causa efeito colateral
        pyautogui.press('enter')
        self.aguardar(0.5)
        return False

    def clicar_salvar(self):
        """Clica em Salvar e maximiza o popup do editor"""
        print("💾 Clicando em Salvar...")
        pyautogui.click(self.COORD_BTN_SALVAR_FORM)
        self.aguardar(2.5)
        print("  ⏳ Aguardando editor abrir...")
        self.aguardar(1)
        print("  🖼️ Maximizando popup...")
        pyautogui.hotkey('alt', 'space')
        self.aguardar(0.3)
        pyautogui.press('x')
        self.aguardar(0.5)
        print("✅ Salvo e editor aberto")

    def colar_imagem_editor(self, imagem_obj):
        """Cola imagem PIL no editor de texto do SEI"""
        print("📋 Colando imagem no editor...")
        try:
            from PIL import Image
            import io
            import win32clipboard

            output = io.BytesIO()
            imagem_obj.convert('RGB').save(output, 'BMP')
            data = output.getvalue()[14:]
            output.close()

            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
            win32clipboard.CloseClipboard()
            self.aguardar(0.5)

            pyautogui.click(self.COORD_AREA_EDICAO)
            self.aguardar(0.3)
            pyautogui.hotkey('ctrl', 'a')
            self.aguardar(0.2)
            pyautogui.hotkey('ctrl', 'v')
            self.aguardar(1.5)
            print("✅ Imagem colada")

        except Exception as e:
            print(f"❌ Erro ao colar imagem: {e}")
            raise

    def colar_texto_editor(self, texto):
        """Cola texto no editor"""
        print("📝 Colando texto no editor...")
        pyperclip.copy(texto)
        self.aguardar(0.3)
        pyautogui.click(self.COORD_AREA_EDICAO)
        self.aguardar(0.3)
        pyautogui.hotkey('ctrl', 'a')
        self.aguardar(0.2)
        pyautogui.hotkey('ctrl', 'v')
        self.aguardar(0.8)
        print("✅ Texto colado")

    def colar_despacho_com_link(self, texto_antes, link, texto_depois):
        """
        Cola o despacho em três partes para que o link #{...}# seja
        interpretado pelo SEI como referência clicável.

        1. Cola o texto antes do link via Ctrl+V
        2. Cola o link via Ctrl+V (SEI interpreta o #{...}# como hyperlink)
        3. Cola o texto depois do link via Ctrl+V
        """
        print("📝 Colando despacho com link em três partes...")

        # Clica UMA vez para focar o editor e não toca mais no mouse
        pyautogui.click(self.COORD_AREA_EDICAO)
        self.aguardar(0.5)

        # Limpa o conteúdo padrão do editor
        pyautogui.hotkey('ctrl', 'a')
        self.aguardar(0.3)
        pyautogui.press('delete')
        self.aguardar(0.5)

        # Parte 1: texto antes do link
        print("  📋 Colando texto antes do link...")
        pyperclip.copy(texto_antes)
        self.aguardar(0.3)
        pyautogui.hotkey('ctrl', 'v')
        self.aguardar(0.8)

        # Parte 2: o link — #{...}# colado como texto, SEI converte em hyperlink
        print(f"  🔗 Colando link: {link}")
        pyperclip.copy(link)
        self.aguardar(0.3)
        pyautogui.hotkey('ctrl', 'v')
        self.aguardar(0.8)

        # Clica numa área vazia do editor para refocar de forma mais natural
        pyautogui.click(934, 496)
        self.aguardar(0.5)

        # Espaço + dois Enters para "confirmar" o link no editor do SEI
        pyautogui.press('space')
        self.aguardar(0.2)
        pyautogui.press('enter')
        self.aguardar(0.2)
        pyautogui.press('enter')
        self.aguardar(0.3)

        # Parte 3: texto depois do link
        print("  📋 Colando texto depois do link...")
        pyperclip.copy(texto_depois)
        self.aguardar(0.3)
        pyautogui.hotkey('ctrl', 'v')
        self.aguardar(0.8)

        print("✅ Despacho colado com link!")

    def clicar_salvar_editor(self):
        """Salva (Ctrl+Alt+S) e fecha (Ctrl+W) o editor popup"""
        print("💾 Salvando no editor...")
        pyautogui.click(self.COORD_AREA_EDICAO)
        self.aguardar(0.3)
        pyautogui.hotkey('ctrl', 'alt', 's')
        print("  ⏳ Aguardando salvar...")
        self.aguardar(3)
        print("  🚪 Fechando popup...")
        pyautogui.hotkey('ctrl', 'w')
        self.aguardar(1.5)
        print("✅ Editor salvo e fechado")

    def anexar_arquivo_externo(self, arquivo_path):
        """Abre janela de upload do Windows e anexa o arquivo"""
        print(f"📎 Anexando: {os.path.basename(arquivo_path)}")
        pyautogui.click(self.COORD_BTN_ANEXAR_ARQUIVO)
        self.aguardar(2)
        print("  ⏳ Aguardando janela de upload...")
        self.aguardar(1)
        caminho_windows = os.path.abspath(arquivo_path)
        pyperclip.copy(caminho_windows)
        pyautogui.hotkey('ctrl', 'v')
        self.aguardar(0.5)
        pyautogui.press('enter')
        print("  ⏳ Processando upload...")
        self.aguardar(5)
        print("✅ Arquivo anexado")

    def ler_texto_docx(self, docx_path):
        """Lê todo o texto de um arquivo .docx"""
        try:
            doc = DocxDocument(docx_path)
            texto = "\n".join([p.text for p in doc.paragraphs])
            print(f"  ✅ Texto extraído: {len(texto)} caracteres")
            return texto
        except Exception as e:
            print(f"❌ Erro ao ler .docx: {e}")
            return ""

    def capturar_link_documento_arvore(self, coord_icone):
        """
        Captura o link de um documento na árvore do SEI clicando
        com botão ESQUERDO no ícone, depois Tab + Tab + Enter.
        O link vai para a área de transferência automaticamente.

        Args:
            coord_icone: tupla (x, y) com a coordenada do ícone na árvore

        Returns:
            str: link capturado ou placeholder se falhar
        """
        print("🔗 Capturando link do documento na árvore...")

        # Limpa o clipboard antes para detectar se o link foi capturado
        pyperclip.copy('')
        self.aguardar(0.3)

        # Clica no ícone com botão esquerdo
        print(f"  🖱️ Clicando no ícone em {coord_icone}...")
        pyautogui.click(coord_icone)
        self.aguardar(0.8)

        # Tab + Tab + Enter para acionar a opção de copiar link
        print("  ⌨️ Tab → Tab → Enter...")
        pyautogui.press('tab')
        self.aguardar(0.3)
        pyautogui.press('tab')
        self.aguardar(0.3)
        pyautogui.press('enter')
        self.aguardar(0.8)

        # Lê o link do clipboard
        link = pyperclip.paste()

        # O SEI usa formato interno #{XXXXXXXX|XXXXXXXXXX}# ao copiar referência
        if link and (link.startswith('#') or 'http' in link.lower()):
            print(f"  ✅ Link capturado: {link}")
            return link
        else:
            print(f"  ⚠️ Link não detectado no clipboard (valor: '{link}'). Usando placeholder.")
            return '[LINK_DO_DOCUMENTO]'

    # =========================================================
    # DOCUMENTOS INTERNOS (print de PDF)
    # =========================================================

    def processar_documento_01_capa(self, pdf_path):
        """01. CAPA"""
        print("\n" + "="*60)
        print("📄 DOCUMENTO 01: CAPA")
        print("="*60)

        imagem = pdf_utils.processar_capa_especial(pdf_path)
        if not imagem:
            raise Exception("Erro ao processar capa")

        self.clicar_botao_incluir_documento()
        self.pesquisar_e_selecionar_tipo_doc("Informacao")
        self.preencher_formulario_interno("Capa padrão imprensa oficial", "Capa")
        self.selecionar_nivel_acesso_publico()
        self.clicar_salvar()
        self.colar_imagem_editor(imagem)
        self.clicar_salvar_editor()

        print("✅ CAPA inserida!\n")

    def processar_documento_02_solicitacao(self, pdf_path):
        """02. SOLICITAÇÃO DE ADIANTAMENTO"""
        print("\n" + "="*60)
        print("📄 DOCUMENTO 02: SOLICITAÇÃO DE ADIANTAMENTO")
        print("="*60)

        imagem = pdf_utils.processar_print_padrao(pdf_path)
        if not imagem:
            raise Exception("Erro ao renderizar PDF")

        self.clicar_botao_incluir_documento()
        self.pesquisar_e_selecionar_tipo_doc("Solicitacao")
        self.preencher_formulario_interno("Solicitação de adiantamento", "adiantamento")
        self.selecionar_nivel_acesso_publico()
        self.clicar_salvar()
        self.colar_imagem_editor(imagem)
        self.clicar_salvar_editor()

        print("✅ SOLICITAÇÃO inserida!\n")

    # =========================================================
    # DOCUMENTOS EXTERNOS (upload de PDF)
    # =========================================================

    def processar_documento_03_nota_empenho(self, pdf_path):
        """03. NOTA DE EMPENHO"""
        print("\n" + "="*60)
        print("📄 DOCUMENTO 03: NOTA DE EMPENHO")
        print("="*60)

        dados = pdf_utils.extrair_dados_nota_empenho(pdf_path)

        if not dados['data'] or not dados['numero']:
            print("⚠️ ATENÇÃO: Dados não extraídos completamente!")

        # Guarda no contexto para o despacho (doc 04)
        self.dados_contexto['ne_data']   = dados['data']   or '[DATA]'
        self.dados_contexto['ne_numero'] = dados['numero'] or '[NÚMERO]'

        self.clicar_botao_incluir_documento()
        self.pesquisar_e_selecionar_tipo_doc("Externo")
        self.aguardar(1.5)

        self.selecionar_dropdown_tipo_externo("Nota de empenho")
        self.preencher_campo_clicando(self.COORD_CAMPO_DATA,         dados['data'])
        self.preencher_campo_clicando(self.COORD_CAMPO_NUMERO,       dados['numero'])
        self.preencher_campo_clicando(self.COORD_CAMPO_NOME_ARVORE,  dados['numero'])

        pyautogui.click(self.COORD_RADIO_NATO_DIGITAL)
        self.aguardar(0.3)

        # Público ANTES de anexar (evita bagunça de layout)
        self.selecionar_nivel_acesso_publico_externo()

        self.anexar_arquivo_externo(pdf_path)

        print("  📜 Ajustando scroll após upload...")
        for _ in range(3):
            pyautogui.scroll(-400)
            self.aguardar(0.2)

        self.clicar_salvar()

        # Verifica popup "documento similar" antes de prosseguir
        self.verificar_popup_documento_similar()

        print("✅ NOTA DE EMPENHO inserida!\n")

        # Aguarda a tela principal recarregar antes de capturar o link
        print("  ⏳ Aguardando tela principal recarregar...")
        self.aguardar(2)

    def processar_documento_04_despacho_ne(self):
        """04. DESPACHO DE APROVAÇÃO DA NOTA DE EMPENHO"""
        print("\n" + "="*60)
        print("📄 DOCUMENTO 04: DESPACHO DE APROVAÇÃO DA NE")
        print("="*60)

        # Captura o link da NE — fica armazenado na variável (clipboard será
        # reusado mais tarde na colagem em três partes)
        link_ne = self.capturar_link_documento_arvore(self.COORD_ICONE_NE_ARVORE)

        numero_ne = self.dados_contexto.get('ne_numero', '[NÚMERO]')
        data_ne   = self.dados_contexto.get('ne_data',   '[DATA]')

        # Monta o template usando '<<<LINK>>>' como marcador temporário
        # para depois dividir o texto em antes/depois do link
        texto_completo = config.DESPACHO_APROVACAO_TEMPLATE.format(
            numero_ne = numero_ne,
            link_ne   = '<<<LINK>>>',
            data_ne   = data_ne
        )

        # Divide em duas partes ao redor do marcador
        partes = texto_completo.split('<<<LINK>>>')
        texto_antes  = partes[0]
        texto_depois = partes[1] if len(partes) > 1 else ''

        print(f"\n📋 Texto antes do link:")
        print(f"  '{texto_antes}'")
        print(f"🔗 Link: {link_ne}")
        print(f"📋 Texto depois do link:")
        print(f"  '{texto_depois}'")

        self.clicar_botao_incluir_documento()
        self.pesquisar_e_selecionar_tipo_doc("Despacho")
        self.preencher_formulario_interno("Aprovação de NE", "Aprovação de NE")
        self.selecionar_nivel_acesso_publico()
        self.clicar_salvar()
        self.aguardar(2)

        # Cola em três partes: texto → link via Ctrl+V → texto
        self.colar_despacho_com_link(texto_antes, link_ne, texto_depois)

        self.clicar_salvar_editor()

        print("✅ DESPACHO inserido!\n")

    def processar_documento_05_ordem_bancaria(self, pdf_path):
        """05. ORDEM BANCÁRIA"""
        print("\n" + "="*60)
        print("📄 DOCUMENTO 05: ORDEM BANCÁRIA")
        print("="*60)

        dados = pdf_utils.extrair_dados_ordem_bancaria(pdf_path)

        if not dados['data'] or not dados['numero']:
            print("⚠️ ATENÇÃO: Dados não extraídos completamente!")
            print(f"  Data encontrada:   '{dados.get('data', '')}'")
            print(f"  Número encontrado: '{dados.get('numero', '')}'")

        self.clicar_botao_incluir_documento()
        self.pesquisar_e_selecionar_tipo_doc("Externo")
        self.aguardar(1.5)

        self.selecionar_dropdown_tipo_externo("Ordem bancaria")
        self.preencher_campo_clicando(self.COORD_CAMPO_DATA,        dados['data'])
        self.preencher_campo_clicando(self.COORD_CAMPO_NUMERO,      dados['numero'])
        self.preencher_campo_clicando(self.COORD_CAMPO_NOME_ARVORE, dados['numero'])

        pyautogui.click(self.COORD_RADIO_NATO_DIGITAL)
        self.aguardar(0.3)

        # Público ANTES de anexar (evita bagunça de layout)
        self.selecionar_nivel_acesso_publico_externo()

        self.anexar_arquivo_externo(pdf_path)

        print("  📜 Ajustando scroll após upload...")
        for _ in range(3):
            pyautogui.scroll(-400)
            self.aguardar(0.2)

        self.clicar_salvar()

        # Verifica popup "documento similar" antes de prosseguir
        self.verificar_popup_documento_similar()

        print("✅ ORDEM BANCÁRIA inserida!\n")

        print("  ⏳ Aguardando tela principal recarregar...")
        self.aguardar(2)

    def processar_documento_06_quadro_comparativo(self, pdf_path):
        """06. QUADRO COMPARATIVO DE PREÇOS (Planilha de Pesquisa de Preço)"""
        print("\n" + "="*60)
        print("📄 DOCUMENTO 06: QUADRO COMPARATIVO DE PREÇOS")
        print("="*60)

        imagem = pdf_utils.processar_print_padrao(pdf_path)
        if not imagem:
            raise Exception("Erro ao renderizar PDF")

        self.clicar_botao_incluir_documento()
        self.pesquisar_e_selecionar_tipo_doc("Planilha")
        self.preencher_formulario_interno("Quadro comparativo", "Quadro comparativo")
        self.selecionar_nivel_acesso_publico()
        self.clicar_salvar()
        self.colar_imagem_editor(imagem)
        self.clicar_salvar_editor()

        print("✅ QUADRO COMPARATIVO inserido!\n")

    def selecionar_tipo_conferencia(self, tipo="Cópia Autenticada Administrativamente"):
        """
        Seleciona o tipo de conferência no dropdown (documentos digitalizados).
        Digita as primeiras palavras para filtrar e pressiona Enter.
        """
        print(f"📋 Selecionando tipo de conferência: '{tipo}'")
        pyautogui.click(self.COORD_DROPDOWN_TIPO_CONFERENCIA)
        self.aguardar(0.8)
        pyautogui.press('down')
        self.aguardar(0.3)
        pyautogui.press('enter')
        self.aguardar(0.5)
        print("✅ Tipo de conferência selecionado")

    def processar_documento_07_nota_fiscal(self, pdf_path):
        """07. NOTA FISCAL"""
        print("\n" + "="*60)
        print("📄 DOCUMENTO 07: NOTA FISCAL")
        print("="*60)

        dados = pdf_utils.extrair_dados_nota_fiscal(pdf_path)

        if not dados['data'] or not dados['numero']:
            print("⚠️ ATENÇÃO: Dados não extraídos completamente!")
            print(f"  Data:    '{dados.get('data', '')}'")
            print(f"  Número:  '{dados.get('numero', '')}'")

        # Empresa vem do nome do arquivo (mais confiável que OCR)
        empresa = self.extrair_empresa_do_nome_arquivo(pdf_path)

        # Guarda no contexto — comprovante reutiliza
        self.dados_contexto['nf_data']    = dados['data']   or '[DATA]'
        self.dados_contexto['nf_numero']  = dados['numero'] or '[NÚMERO]'
        self.dados_contexto['nf_empresa'] = empresa

        self.clicar_botao_incluir_documento()
        self.pesquisar_e_selecionar_tipo_doc("Externo")
        self.aguardar(1.5)

        self.selecionar_dropdown_tipo_externo("Nota Fiscal")
        self.preencher_campo_clicando(self.COORD_CAMPO_DATA,        dados['data'])
        self.preencher_campo_clicando(self.COORD_CAMPO_NUMERO,      dados['numero'])
        # Nome na árvore: nome da empresa
        self.preencher_campo_clicando(self.COORD_CAMPO_NOME_ARVORE, self.dados_contexto['nf_empresa'])

        pyautogui.click(self.COORD_RADIO_NATO_DIGITAL)
        self.aguardar(0.3)

        self.selecionar_nivel_acesso_publico_externo()

        self.anexar_arquivo_externo(pdf_path)

        print("  📜 Ajustando scroll após upload...")
        for _ in range(3):
            pyautogui.scroll(-400)
            self.aguardar(0.2)

        self.clicar_salvar()

        # Verifica popup "documento similar" antes de prosseguir
        self.verificar_popup_documento_similar()

        print("✅ NOTA FISCAL inserida!\n")

        print("  ⏳ Aguardando tela principal recarregar...")
        self.aguardar(2)

    def processar_documento_08_comprovante_fiscal(self, pdf_path):
        """08. COMPROVANTE DA NOTA FISCAL (digitalizado)"""
        print("\n" + "="*60)
        print("📄 DOCUMENTO 08: COMPROVANTE DA NOTA FISCAL")
        print("="*60)

        # Reutiliza os dados da NF já extraída (inclusive empresa do nome do arquivo)
        data    = self.dados_contexto.get('nf_data',    '[DATA]')
        numero  = self.dados_contexto.get('nf_numero',  '[NÚMERO]')
        empresa = self.dados_contexto.get('nf_empresa', '[EMPRESA]')

        self.clicar_botao_incluir_documento()
        self.pesquisar_e_selecionar_tipo_doc("Externo")
        self.aguardar(1.5)

        self.selecionar_dropdown_tipo_externo("Comprovante")
        self.preencher_campo_clicando(self.COORD_CAMPO_DATA,        data)
        self.preencher_campo_clicando(self.COORD_CAMPO_NUMERO,      numero)
        self.preencher_campo_clicando(self.COORD_CAMPO_NOME_ARVORE, empresa)

        # Digitalizado → habilita dropdown de tipo de conferência
        pyautogui.click(self.COORD_RADIO_DIGITALIZADO)
        self.aguardar(0.5)

        self.selecionar_tipo_conferencia("Cópia Autenticada Administrativamente")

        self.selecionar_nivel_acesso_publico_externo()

        self.anexar_arquivo_externo(pdf_path)

        print("  📜 Ajustando scroll após upload...")
        for _ in range(3):
            pyautogui.scroll(-400)
            self.aguardar(0.2)

        self.clicar_salvar()

        # Verifica popup "documento similar" antes de prosseguir
        self.verificar_popup_documento_similar()

        print("✅ COMPROVANTE FISCAL inserido!\n")

        print("  ⏳ Aguardando tela principal recarregar...")
        self.aguardar(2)

    def processar_documento_09_declaracao_recebimento(self, docx_path):
        """09. DECLARAÇÃO DE RECEBIMENTO (interno - print da primeira página do .docx)"""
        print("\n" + "="*60)
        print("📄 DOCUMENTO 09: DECLARAÇÃO DE RECEBIMENTO")
        print("="*60)

        imagem = pdf_utils.renderizar_docx_como_imagem(docx_path)
        if not imagem:
            raise Exception(
                "Erro ao renderizar .docx da declaração.\n"
                "Instale o LibreOffice: https://www.libreoffice.org/download/\n"
                "Ou verifique se está instalado em C:\\Program Files\\LibreOffice\\"
            )

        # Nome na árvore = empresa do ciclo atual
        empresa = self.dados_contexto.get('nf_empresa', '[EMPRESA]')

        self.clicar_botao_incluir_documento()
        self.pesquisar_e_selecionar_tipo_doc("Declaracao")
        self.preencher_formulario_interno(
            "Declaração de Recebimento, Conformidade e Destinação",
            empresa
        )
        self.selecionar_nivel_acesso_publico()
        self.clicar_salvar()
        self.colar_imagem_editor(imagem)
        self.clicar_salvar_editor()

        print("✅ DECLARAÇÃO DE RECEBIMENTO inserida!\n")

    def processar_documento_10_consulta_optante(self, pdf_path):
        """10. CONSULTA DE OPTANTE (documento externo)"""
        print("\n" + "="*60)
        print("📄 DOCUMENTO 10: CONSULTA DE OPTANTE")
        print("="*60)

        dados   = pdf_utils.extrair_dados_consulta(pdf_path)
        empresa = self.extrair_empresa_do_nome_arquivo(pdf_path)

        self.dados_contexto['consulta_cnpj'] = dados['numero']  # guarda para o doc 11

        self.clicar_botao_incluir_documento()
        self.pesquisar_e_selecionar_tipo_doc("Externo")
        self.aguardar(1.5)

        self.selecionar_dropdown_tipo_externo("Consulta")
        self.preencher_campo_clicando(self.COORD_CAMPO_DATA,        dados['data'])
        self.preencher_campo_clicando(self.COORD_CAMPO_NUMERO,      dados['numero'] or '[CNPJ]')
        self.preencher_campo_clicando(self.COORD_CAMPO_NOME_ARVORE, empresa)

        pyautogui.click(self.COORD_RADIO_NATO_DIGITAL)
        self.aguardar(0.3)

        self.selecionar_nivel_acesso_publico_externo()
        self.anexar_arquivo_externo(pdf_path)

        print("  📜 Ajustando scroll após upload...")
        for _ in range(3):
            pyautogui.scroll(-400)
            self.aguardar(0.2)

        self.clicar_salvar()
        self.verificar_popup_documento_similar()

        print("✅ CONSULTA DE OPTANTE inserida!\n")

        print("  ⏳ Aguardando tela principal recarregar...")
        self.aguardar(2)

    def processar_documento_11_cnpj(self, pdf_path):
        """11. CNPJ (documento externo)"""
        print("\n" + "="*60)
        print("📄 DOCUMENTO 11: CNPJ")
        print("="*60)

        dados   = pdf_utils.extrair_dados_cnpj(pdf_path)
        empresa = self.extrair_empresa_do_nome_arquivo(pdf_path)
        # Reutiliza o CNPJ já encontrado na consulta (mais confiável)
        cnpj    = self.dados_contexto.get('consulta_cnpj') or dados['numero'] or '[CNPJ]'

        self.clicar_botao_incluir_documento()
        self.pesquisar_e_selecionar_tipo_doc("Externo")
        self.aguardar(1.5)

        self.selecionar_dropdown_tipo_externo("Cadastro Nacional De Pessoa Jurídica")
        self.preencher_campo_clicando(self.COORD_CAMPO_DATA,        dados['data'])
        self.preencher_campo_clicando(self.COORD_CAMPO_NUMERO,      cnpj)
        self.preencher_campo_clicando(self.COORD_CAMPO_NOME_ARVORE, empresa)

        pyautogui.click(self.COORD_RADIO_NATO_DIGITAL)
        self.aguardar(0.3)

        self.selecionar_nivel_acesso_publico_externo()
        self.anexar_arquivo_externo(pdf_path)

        print("  📜 Ajustando scroll após upload...")
        for _ in range(3):
            pyautogui.scroll(-400)
            self.aguardar(0.2)

        self.clicar_salvar()
        self.verificar_popup_documento_similar()

        print("✅ CNPJ inserido!\n")

        print("  ⏳ Aguardando tela principal recarregar...")
        self.aguardar(2)

    def processar_documento_12_guia_iss(self, pdf_path):
        """12. GUIA DE ISS (documento externo, opcional)"""
        print("\n" + "="*60)
        print("📄 DOCUMENTO 12: GUIA DE ISS")
        print("="*60)

        dados = pdf_utils.extrair_dados_guia_iss(pdf_path)

        self.clicar_botao_incluir_documento()
        self.pesquisar_e_selecionar_tipo_doc("Externo")
        self.aguardar(1.5)

        self.selecionar_dropdown_tipo_externo("Guia de recolhimento")
        self.preencher_campo_clicando(self.COORD_CAMPO_DATA,        dados['data'])
        self.preencher_campo_clicando(self.COORD_CAMPO_NUMERO,      dados['numero'])
        self.preencher_campo_clicando(self.COORD_CAMPO_NOME_ARVORE, dados['numero'])

        pyautogui.click(self.COORD_RADIO_NATO_DIGITAL)
        self.aguardar(0.3)

        self.selecionar_nivel_acesso_publico_externo()
        self.anexar_arquivo_externo(pdf_path)

        print("  📜 Ajustando scroll após upload...")
        for _ in range(3):
            pyautogui.scroll(-400)
            self.aguardar(0.2)

        self.clicar_salvar()
        self.verificar_popup_documento_similar()

        print("✅ GUIA DE ISS inserida!\n")

        print("  ⏳ Aguardando tela principal recarregar...")
        self.aguardar(2)

    def processar_documento_13_comprovante_iss(self, pdf_path):
        """13. COMPROVANTE DE ISS (documento externo, opcional)"""
        print("\n" + "="*60)
        print("📄 DOCUMENTO 13: COMPROVANTE DE ISS")
        print("="*60)

        dados = pdf_utils.extrair_dados_guia_iss(pdf_path)

        self.clicar_botao_incluir_documento()
        self.pesquisar_e_selecionar_tipo_doc("Externo")
        self.aguardar(1.5)

        self.selecionar_dropdown_tipo_externo("Comprovante")
        self.preencher_campo_clicando(self.COORD_CAMPO_DATA,        dados['data'])
        self.preencher_campo_clicando(self.COORD_CAMPO_NUMERO,      dados['numero'])
        self.preencher_campo_clicando(self.COORD_CAMPO_NOME_ARVORE, dados['numero'])

        pyautogui.click(self.COORD_RADIO_NATO_DIGITAL)
        self.aguardar(0.3)

        self.selecionar_nivel_acesso_publico_externo()
        self.anexar_arquivo_externo(pdf_path)

        print("  📜 Ajustando scroll após upload...")
        for _ in range(3):
            pyautogui.scroll(-400)
            self.aguardar(0.2)

        self.clicar_salvar()
        self.verificar_popup_documento_similar()

        print("✅ COMPROVANTE DE ISS inserido!\n")

        print("  ⏳ Aguardando tela principal recarregar...")
        self.aguardar(2)

    def processar_documento_14_balancete(self, pdf_path):
        """14. BALANCETE DE DESPESAS COM ADIANTAMENTO (interno)"""
        print("\n" + "="*60)
        print("📄 DOCUMENTO 14: BALANCETE")
        print("="*60)

        imagem = pdf_utils.processar_print_padrao(pdf_path)
        if not imagem:
            raise Exception("Erro ao renderizar PDF do balancete")

        self.clicar_botao_incluir_documento()
        self.pesquisar_e_selecionar_tipo_doc("Balancete")
        self.preencher_formulario_interno("Balancete de despesas com adiantamento", "Balancete")
        self.selecionar_nivel_acesso_publico()
        self.clicar_salvar()
        self.colar_imagem_editor(imagem)
        self.clicar_salvar_editor()

        print("✅ BALANCETE inserido!\n")

    def processar_documento_15_extrato_bancario(self, pdf_path):
        """15. EXTRATO BANCÁRIO (externo)"""
        print("\n" + "="*60)
        print("📄 DOCUMENTO 15: EXTRATO BANCÁRIO")
        print("="*60)

        data = pdf_utils.extrair_data_extrato(pdf_path)

        self.clicar_botao_incluir_documento()
        self.pesquisar_e_selecionar_tipo_doc("Externo")
        self.aguardar(1.5)

        self.selecionar_dropdown_tipo_externo("Extrato")
        self.preencher_campo_clicando(self.COORD_CAMPO_DATA,        data)
        self.preencher_campo_clicando(self.COORD_CAMPO_NOME_ARVORE, "Bancário")

        pyautogui.click(self.COORD_RADIO_NATO_DIGITAL)
        self.aguardar(0.3)

        self.selecionar_nivel_acesso_publico_externo()
        self.anexar_arquivo_externo(pdf_path)

        print("  📜 Ajustando scroll após upload...")
        for _ in range(3):
            pyautogui.scroll(-400)
            self.aguardar(0.2)

        self.clicar_salvar()
        self.verificar_popup_documento_similar()

        print("✅ EXTRATO BANCÁRIO inserido!\n")

        print("  ⏳ Aguardando tela principal recarregar...")
        self.aguardar(2)

    def processar_documento_16_conciliacao_contabil(self, pdf_path):
        """16. RELATÓRIO DE CONCILIAÇÃO CONTÁBIL (interno)"""
        print("\n" + "="*60)
        print("📄 DOCUMENTO 16: CONCILIAÇÃO CONTÁBIL")
        print("="*60)

        imagem = pdf_utils.processar_print_padrao(pdf_path)
        if not imagem:
            raise Exception("Erro ao renderizar PDF da conciliação")

        self.clicar_botao_incluir_documento()
        self.pesquisar_e_selecionar_tipo_doc("Conciliacao")
        self.preencher_formulario_interno("Relatório de conciliação contábil", "Conciliação contábil")
        self.selecionar_nivel_acesso_publico()
        self.clicar_salvar()
        self.colar_imagem_editor(imagem)
        self.clicar_salvar_editor()

        print("✅ CONCILIAÇÃO CONTÁBIL inserida!\n")

    def processar_documento_17_declaracao_encerramento(self, pdf_path):
        """17. DECLARAÇÃO DE ENCERRAMENTO (interno)"""
        print("\n" + "="*60)
        print("📄 DOCUMENTO 17: DECLARAÇÃO DE ENCERRAMENTO")
        print("="*60)

        imagem = pdf_utils.processar_print_padrao(pdf_path)
        if not imagem:
            raise Exception("Erro ao renderizar PDF da declaração de encerramento")

        self.clicar_botao_incluir_documento()
        self.pesquisar_e_selecionar_tipo_doc("Declaracao")
        self.preencher_formulario_interno("Declaração de encerramento", "Encerramento")
        self.selecionar_nivel_acesso_publico()
        self.clicar_salvar()
        self.colar_imagem_editor(imagem)
        self.clicar_salvar_editor()

        print("✅ DECLARAÇÃO DE ENCERRAMENTO inserida!\n")

    # =========================================================
    # EXECUÇÃO PRINCIPAL
    # =========================================================

    def executar(self):
        """Executa o processo completo de automação"""
        print("\n" + "="*70)
        print("🤖 AUTOMAÇÃO SEI - INSERÇÃO DE DOCUMENTOS")
        print("="*70)

        print("\n🔍 Verificando configurações...")
        if not config.validar_configuracoes():
            print("\n❌ Corrija as configurações antes de continuar")
            return False

        self.carregar_documentos()

        if not self.documentos:
            print("\n❌ Nenhum documento encontrado!")
            return False

        # ── Detecta posição do Balancete para delimitar os ciclos ──────
        idx_balancete = None
        for i, doc in enumerate(self.documentos):
            if 'balancete' in os.path.basename(doc).lower():
                idx_balancete = i
                break

        if idx_balancete is not None:
            docs_ciclo   = self.documentos[4:idx_balancete]
            docs_finais  = self.documentos[idx_balancete:]
            print(f"\n📊 Balancete encontrado na posição {idx_balancete + 1}")
            print(f"   Arquivos nos ciclos: {len(docs_ciclo)}")
            print(f"   Arquivos finais:     {len(docs_finais)}")
        else:
            docs_ciclo  = self.documentos[4:]
            docs_finais = []
            print("\n⚠️ Balancete não encontrado — processando tudo como ciclos")

        print("\n" + "="*70)
        print("⚠️  INSTRUÇÕES:")
        print("="*70)
        print("1. Firefox aberto e maximizado no SEI")
        print("2. Processo aberto e visível na tela")
        print("3. NÃO mexa no mouse/teclado durante a execução")
        print("4. Para CANCELAR: mova o mouse para o canto SUPERIOR ESQUERDO")
        print("="*70)

        print("\n⏳ Iniciando em 10 segundos... (Ctrl+C para cancelar)")
        try:
            for i in range(10, 0, -1):
                print(f"   {i}...", end='\r')
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\n❌ Cancelado pelo usuário")
            return False

        print("\n\n🚀 INICIANDO AUTOMAÇÃO...\n")

        try:
            # ── Documentos fixos ────────────────────────────────────────
            if len(self.documentos) >= 1:
                self.processar_documento_01_capa(self.documentos[0])

            if len(self.documentos) >= 2:
                self.processar_documento_02_solicitacao(self.documentos[1])

            if len(self.documentos) >= 3:
                self.processar_documento_03_nota_empenho(self.documentos[2])

            self.processar_documento_04_despacho_ne()

            if len(self.documentos) >= 4:
                self.processar_documento_05_ordem_bancaria(self.documentos[3])

            # ── Ciclos de Notas Fiscais ─────────────────────────────────
            # Cada ciclo: Quadro Comparativo → NF → Comprovante → Declaração
            #             → Consulta → CNPJ → Guia ISS (opcional) → Comprovante ISS (opcional)
            idx = 0
            num_nf = 1
            while idx < len(docs_ciclo):
                restantes = docs_ciclo[idx:]

                # Precisa de pelo menos 6 arquivos para um ciclo completo sem ISS
                if len(restantes) < 6:
                    print(f"\n⚠️ Apenas {len(restantes)} arquivo(s) restante(s) antes do balancete — encerrando ciclos.")
                    break

                print(f"\n{'='*70}")
                print(f"🔁 CICLO NOTA FISCAL #{num_nf}")
                print(f"{'='*70}")

                self.processar_documento_06_quadro_comparativo(docs_ciclo[idx]);      idx += 1
                self.processar_documento_07_nota_fiscal(docs_ciclo[idx]);             idx += 1
                self.processar_documento_08_comprovante_fiscal(docs_ciclo[idx]);      idx += 1
                self.processar_documento_09_declaracao_recebimento(docs_ciclo[idx]);  idx += 1
                self.processar_documento_10_consulta_optante(docs_ciclo[idx]);        idx += 1
                self.processar_documento_11_cnpj(docs_ciclo[idx]);                    idx += 1

                # ISS opcional
                while idx < len(docs_ciclo) and 'iss' in os.path.basename(docs_ciclo[idx]).lower():
                    nome = os.path.basename(docs_ciclo[idx]).lower()
                    if 'comprovante' in nome:
                        self.processar_documento_13_comprovante_iss(docs_ciclo[idx])
                    else:
                        self.processar_documento_12_guia_iss(docs_ciclo[idx])
                    idx += 1

                num_nf += 1

            # ── Documentos finais (após todos os ciclos) ────────────────
            if len(docs_finais) >= 1:
                self.processar_documento_14_balancete(docs_finais[0])

            if len(docs_finais) >= 2:
                self.processar_documento_15_extrato_bancario(docs_finais[1])

            if len(docs_finais) >= 3:
                self.processar_documento_16_conciliacao_contabil(docs_finais[2])

            if len(docs_finais) >= 4:
                self.processar_documento_17_declaracao_encerramento(docs_finais[3])

            print("\n" + "="*70)
            print("✅ AUTOMAÇÃO CONCLUÍDA!")
            print("="*70)
            print("\n⚠️ Verifique todos os documentos inseridos")
            print("   Confirme se os dados de OCR estão corretos")
            return True

        except KeyboardInterrupt:
            print("\n\n⚠️ Automação cancelada pelo usuário")
            return False
        except Exception as e:
            print(f"\n\n❌ ERRO DURANTE EXECUÇÃO: {e}")
            import traceback
            traceback.print_exc()
            return False


# =========================================================
# EXECUÇÃO
# =========================================================

if __name__ == "__main__":
    print("="*70)
    print("SEI AUTOMATION - Sistema de Inserção Automática de Documentos")
    print("="*70)

    # Para pular docs já inseridos: SEIAutomation(pular_primeiros=2)
    automacao = SEIAutomation()
    sucesso = automacao.executar()

    if sucesso:
        print("\n✅ Processo finalizado com sucesso!")
    else:
        print("\n❌ Processo finalizado com erros")

    print("\nPressione ENTER para sair...")
    input()