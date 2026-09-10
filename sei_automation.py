"""
Script de automação para inserção de documentos no SEI (SP)
NAVEGADOR: Firefox

VERSÃO 3.0 — Pipeline modular:
- Os tipos de documento NÃO são mais posições fixas no código. São
  "passos" configuráveis (ver pipeline.py): categoria (fixo inicial /
  ciclo / fixo final), ordem de execução, detecção pelo nome do
  arquivo, ativo/inativo — tudo editável na aba "Pipeline de
  Documentos" da GUI, sem tocar em código.
- A lógica de "como preencher cada formulário do SEI" mora em
  processadores.py (mantida quase literal em relação à versão
  anterior — é conhecimento de domínio, não boilerplate).
- Este arquivo cuida de: validar configuração, montar a sequência de
  tarefas a partir do pipeline, aplicar o modo de retomada escolhido
  (do início / pular fixos / ciclo N / arquivo N / a partir do
  despacho de aprovação de NE), e disparar cada tarefa em sequência.

Compatibilidade: a assinatura pública de SEIAutomation(...) e o
método .executar() não mudaram — gui/automation_worker.py continua
funcionando sem alterações.
"""

import os
import re
import time
import pyautogui
import pyperclip
from docx import Document as DocxDocument

import config
import ocr_utils
import pdf_utils
import doc_ordem
import pipeline
import processadores


# Configurações do pyautogui
pyautogui.PAUSE = config.PAUSE_BETWEEN_ACTIONS
pyautogui.FAILSAFE = True  # Mover mouse para canto superior esquerdo cancela


class SEIAutomation:
    """Classe principal para automação do SEI.

    Coordenadas, tempos e caminhos vivem em config.py. Os TIPOS DE
    DOCUMENTO (o que cada passo faz, em que ordem, se está ativo) vivem
    em pipeline.py / pipeline_config.json.
    """

    def __init__(self, pasta_documentos=None, pular_primeiros=0, ciclo_inicial=1,
                 pular_docs_fixos=False, arquivo_inicial=None, tipo_processo='DMPP',
                 iniciar_do_despacho_ne=False, despacho_numero_ne=None, despacho_data_ne=None):
        """
        Args:
            pasta_documentos:   Caminho da pasta com documentos
            pular_primeiros:    (legado, não usado pelo pipeline — mantido só
                                 por compatibilidade de assinatura)
            ciclo_inicial:      Número do ciclo de NF para iniciar (1 = primeiro ciclo)
            pular_docs_fixos:   Se True, pula os documentos fixos iniciais
            arquivo_inicial:    Número do arquivo para iniciar (ex: 31)
            tipo_processo:      'DMPP' (padrão) ou 'UFIEC' (com memorando)
            iniciar_do_despacho_ne: Se True, inicia direto do Despacho de Aprovação da NE
            despacho_numero_ne: Número da NE (usado quando iniciar_do_despacho_ne=True)
            despacho_data_ne:   Data da NE (usado quando iniciar_do_despacho_ne=True)
        """
        self.pasta_documentos = pasta_documentos or config.DOCUMENTOS_DIR
        self.pular_primeiros = pular_primeiros
        self.ciclo_inicial = ciclo_inicial
        self.pular_docs_fixos = pular_docs_fixos
        self.arquivo_inicial = arquivo_inicial
        self.tipo_processo = tipo_processo
        self.iniciar_do_despacho_ne = iniciar_do_despacho_ne
        self.despacho_numero_ne = despacho_numero_ne
        self.despacho_data_ne = despacho_data_ne
        self.dados_contexto = {}   # dados compartilhados entre passos (ex: dados da NF pro comprovante)
        self.tarefas = []          # preenchido por montar_tarefas()

    # =========================================================
    # UTILITÁRIOS
    # =========================================================

    def aguardar(self, segundos=None):
        if segundos is None:
            segundos = config.WAIT_FOR_ELEMENT
        time.sleep(segundos)

    def _data_fallback(self, data):
        """Retorna a data fornecida ou uma data-placeholder óbvia como
        último recurso (formato DD/MM/YYYY).

        NUNCA retorna o texto literal "[DATA]" — isso não pode ir
        parar em um campo do SEI. Quando a data não pôde ser
        determinada, usa config.DATA_FALLBACK_PADRAO (uma data
        propositalmente "impossível", ex: 01/01/1999) para que fique
        óbvio na revisão manual que aquele documento precisa de
        correção.
        """
        if data:
            return data
        placeholder = config.DATA_FALLBACK_PADRAO
        print(f"  ⚠️ Data não encontrada — usando data-placeholder: {placeholder} (REVISAR MANUALMENTE)")
        return placeholder

    # =========================================================
    # MONTAGEM DA SEQUÊNCIA (via pipeline.py)
    # =========================================================

    def montar_tarefas(self):
        self.tarefas = pipeline.montar_tarefas(self.pasta_documentos, config.BASE_DIR, self.tipo_processo)
        return self.tarefas

    def _indice_retomada(self):
        """Decide de que ponto da lista self.tarefas a execução deve
        começar, de acordo com o modo escolhido. Levanta Exception com
        mensagem clara se o ponto pedido não existir (mais seguro do
        que adivinhar um fallback silencioso)."""

        if self.iniciar_do_despacho_ne:
            for i, t in enumerate(self.tarefas):
                if t["step"]["id"] == "despacho_aprovacao_ne":
                    return i
            raise Exception(
                "Modo 'a partir do despacho de aprovação de NE' foi pedido, mas "
                "não há esse passo ativo no pipeline atual."
            )

        if self.arquivo_inicial:
            for i, t in enumerate(self.tarefas):
                if t["arquivo"] is None:
                    continue
                nome = os.path.basename(t["arquivo"])
                m = re.match(r'^(\d+)', nome)
                if m and int(m.group(1)) == self.arquivo_inicial:
                    return i
            raise Exception(
                f"Arquivo {self.arquivo_inicial} não encontrado em nenhuma tarefa "
                "montada pelo pipeline (confira o número, ou se esse arquivo "
                "está sendo classificado corretamente na aba Documentos)."
            )

        if self.ciclo_inicial and self.ciclo_inicial > 1:
            for i, t in enumerate(self.tarefas):
                if t["numero_ciclo"] == self.ciclo_inicial:
                    return i
            raise Exception(
                f"Ciclo {self.ciclo_inicial} não encontrado (a pasta tem menos "
                "ciclos de Nota Fiscal do que isso)."
            )

        if self.pular_docs_fixos:
            for i, t in enumerate(self.tarefas):
                if t["step"]["categoria"] != "fixo_inicial":
                    return i
            return len(self.tarefas)

        return 0

    # =========================================================
    # AÇÕES BÁSICAS (cliques/preenchimento — usadas por processadores.py)
    # =========================================================

    def clicar_botao_incluir_documento(self):
        print("\n🖱️ Clicando em 'Incluir Documento'...")
        pyautogui.click(config.COORD_BTN_INCLUIR_DOC)
        self.aguardar(1.5)
        print("✅ Lista de documentos aberta")

    def pesquisar_e_selecionar_tipo_doc(self, texto_busca):
        """Pesquisa e seleciona tipo de documento na barra de busca"""
        print(f"🔍 Buscando: '{texto_busca}'")
        pyautogui.click(config.COORD_BARRA_PESQUISA)
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
        self.aguardar(config.TEMPOS['aguardar_form_carregar'])

        print(f"  ✏️ Preenchendo 'Descrição': {descricao}")
        pyautogui.click(config.COORD_CAMPO_DESCRICAO_INTERNO)
        self.aguardar(0.4)
        pyautogui.hotkey('ctrl', 'a')
        pyautogui.press('delete')
        self.aguardar(0.1)
        pyperclip.copy(descricao)
        pyautogui.hotkey('ctrl', 'v')
        self.aguardar(0.2)
        pyautogui.press('escape')  # Fecha autocomplete do Firefox
        self.aguardar(0.3)

        print(f"  ✏️ Preenchendo 'Nome na Árvore': {nome_arvore}")
        pyautogui.click(config.COORD_CAMPO_NOME_ARVORE_INTERNO)
        self.aguardar(0.4)
        pyautogui.hotkey('ctrl', 'a')
        pyautogui.press('delete')
        self.aguardar(0.1)
        pyperclip.copy(nome_arvore)
        pyautogui.hotkey('ctrl', 'v')
        self.aguardar(0.2)
        pyautogui.press('escape')  # Fecha autocomplete do Firefox
        self.aguardar(0.3)

        print("  ✅ Campos preenchidos!")

    def selecionar_dropdown_tipo_externo(self, tipo_documento):
        """Seleciona tipo no dropdown de documentos externos"""
        print(f"📋 Selecionando tipo externo: '{tipo_documento}'")
        pyautogui.click(config.COORD_DROPDOWN_TIPO_EXTERNO)
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
            self.aguardar(0.2)
            pyautogui.press('escape')  # Fecha autocomplete do Firefox
            self.aguardar(0.1)

    def selecionar_nivel_acesso_publico(self, n_scrolls=6):
        """Formulários INTERNOS — rola e clica em Público"""
        print("🔓 Selecionando Nível de Acesso: Público")
        for _ in range(n_scrolls):
            pyautogui.scroll(-400)
            self.aguardar(0.2)
        pyautogui.click(config.COORD_RADIO_PUBLICO)
        self.aguardar(0.3)
        print("✅ Público selecionado")

    def selecionar_nivel_acesso_publico_externo(self):
        """Formulários EXTERNOS — usa coordenada própria calibrada"""
        print("🔓 Selecionando Nível de Acesso: Público (externo)")
        for _ in range(6):
            pyautogui.scroll(-400)
            self.aguardar(0.2)
        pyautogui.click(config.COORD_RADIO_PUBLICO_EXTERNO)
        self.aguardar(0.3)
        print("✅ Público selecionado")

    def verificar_popup_documento_similar(self, tentativas=5):
        """
        Verifica se o SEI exibiu popup de documento similar após salvar.
        Estratégia: tira screenshot da região do popup e busca texto chave.
        Como fallback, pressiona Enter pois o botão OK já fica focado por padrão.
        """
        for i in range(tentativas):
            self.aguardar(0.8)
            try:
                screenshot = pyautogui.screenshot(region=config.REGIAO_POPUP_SIMILAR)
                texto = ocr_utils.extrair_texto_imagem(screenshot, preprocessar=False)

                if 'deseja continuar' in texto.lower() or 'já existe' in texto.lower():
                    print("  ⚠️ Popup de documento similar detectado! Clicando OK...")
                    pyautogui.click(*config.COORD_POPUP_OK_SIMILAR)
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
        pyautogui.click(config.COORD_BTN_SALVAR_FORM)
        self.aguardar(config.TEMPOS['pos_salvar_form'])
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

            pyautogui.click(config.COORD_AREA_EDICAO)
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
        pyautogui.click(config.COORD_AREA_EDICAO)
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

        pyautogui.click(config.COORD_AREA_EDICAO)
        self.aguardar(0.5)

        pyautogui.hotkey('ctrl', 'a')
        self.aguardar(0.3)
        pyautogui.press('delete')
        self.aguardar(0.5)

        print("  📋 Colando texto antes do link...")
        pyperclip.copy(texto_antes)
        self.aguardar(0.3)
        pyautogui.hotkey('ctrl', 'v')
        self.aguardar(0.8)

        print(f"  🔗 Colando link: {link}")
        pyperclip.copy(link)
        self.aguardar(0.3)
        pyautogui.hotkey('ctrl', 'v')
        self.aguardar(0.8)

        pyautogui.click(*config.COORD_REFOCO_EDITOR)
        self.aguardar(0.5)

        pyautogui.press('space')
        self.aguardar(0.2)
        pyautogui.press('enter')
        self.aguardar(0.2)
        pyautogui.press('enter')
        self.aguardar(0.3)

        print("  📋 Colando texto depois do link...")
        pyperclip.copy(texto_depois)
        self.aguardar(0.3)
        pyautogui.hotkey('ctrl', 'v')
        self.aguardar(0.8)

        print("✅ Despacho colado com link!")

    def clicar_salvar_editor(self):
        """Salva (Ctrl+Alt+S) e fecha (Ctrl+W) o editor popup"""
        print("💾 Salvando no editor...")
        pyautogui.click(config.COORD_AREA_EDICAO)
        self.aguardar(0.3)
        pyautogui.hotkey('ctrl', 'alt', 's')
        print("  ⏳ Aguardando salvar...")
        self.aguardar(config.TEMPOS['pos_salvar_editor'])
        print("  🚪 Fechando popup...")
        pyautogui.hotkey('ctrl', 'w')
        self.aguardar(1.5)
        print("✅ Editor salvo e fechado")

    def anexar_arquivo_externo(self, arquivo_path):
        """Abre janela de upload do Windows e anexa o arquivo"""
        print(f"📎 Anexando: {os.path.basename(arquivo_path)}")
        pyautogui.click(config.COORD_BTN_ANEXAR_ARQUIVO)
        self.aguardar(2)
        print("  ⏳ Aguardando janela de upload...")
        self.aguardar(1)
        caminho_windows = os.path.abspath(arquivo_path)
        pyperclip.copy(caminho_windows)
        pyautogui.hotkey('ctrl', 'v')
        self.aguardar(0.5)
        pyautogui.press('enter')
        print("  ⏳ Processando upload...")
        self.aguardar(config.TEMPOS['pos_anexo_upload'])
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

    def selecionar_tipo_conferencia(self, tipo="Cópia Autenticada Administrativamente"):
        """
        Seleciona o tipo de conferência no dropdown (documentos digitalizados).
        Digita as primeiras palavras para filtrar e pressiona Enter.
        """
        print(f"📋 Selecionando tipo de conferência: '{tipo}'")
        pyautogui.click(config.COORD_DROPDOWN_TIPO_CONFERENCIA)
        self.aguardar(0.8)
        pyautogui.press('down')
        self.aguardar(0.3)
        pyautogui.press('enter')
        self.aguardar(0.5)
        print("✅ Tipo de conferência selecionado")

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

        pyperclip.copy('')
        self.aguardar(0.3)

        print(f"  🖱️ Clicando no ícone em {coord_icone}...")
        pyautogui.click(coord_icone)
        self.aguardar(0.8)

        print("  ⌨️ Tab → Tab → Enter...")
        pyautogui.press('tab')
        self.aguardar(0.3)
        pyautogui.press('tab')
        self.aguardar(0.3)
        pyautogui.press('enter')
        self.aguardar(0.8)

        link = pyperclip.paste()

        if link and (link.startswith('#') or 'http' in link.lower()):
            print(f"  ✅ Link capturado: {link}")
            return link
        else:
            print(f"  ⚠️ Link não detectado no clipboard (valor: '{link}'). Usando placeholder.")
            return '[LINK_DO_DOCUMENTO]'

    # =========================================================
    # FUNÇÕES DE EXTRAÇÃO DO NOME DO ARQUIVO (usadas por processadores.py)
    # =========================================================

    def extrair_numero_nota_fiscal_do_nome(self, filepath):
        """
        Extrai o número da nota fiscal do nome do arquivo.

        O nome do arquivo segue o padrão: "XX-NOTA FISCAL NNNNN EMPRESA..."
        Onde XX é a ordem e NNNNN é o número da nota.

        Exemplos:
            "37-NOTA FISCAL 17249 ITU LUZ COMÉRCIO.pdf" → "17249"
            "7-NF 12345 EMPRESA XYZ.pdf" → "12345"

        Returns:
            String com o número da nota ou None se não encontrado
        """
        nome = os.path.basename(filepath)
        nome_sem_ext = os.path.splitext(nome)[0]

        nome_sem_ordem = re.sub(r'^\d+[-\s]*', '', nome_sem_ext)
        numeros = re.findall(r'\d+', nome_sem_ordem)

        if numeros:
            numero = numeros[0]
            print(f"  🔢 Número NF extraído do nome do arquivo: {numero}")
            return numero

        print("  ⚠️ Número NF não encontrado no nome do arquivo")
        return None

    def extrair_empresa_do_nome_arquivo(self, filepath):
        """
        Extrai o nome da empresa a partir do nome do arquivo.

        Estratégia:
        - Remove prefixo numérico ("25-")
        - Remove extensão
        - Localiza o traço separador que vem DEPOIS das palavras-chave do tipo
        de documento (ex: "NOTA FISCAL 1939 - EMPRESA" ou "DECLARAÇÃO DE RECEBIMENTO - EMPRESA")
        - Tudo que vier após esse traço é a empresa
        - Se não houver traço separador claro, aplica remoção por keywords como fallback
        """
        nome = os.path.basename(filepath)
        nome = os.path.splitext(nome)[0]
        nome = re.sub(r'^\d+[-\s]*', '', nome).strip()

        if ' - ' in nome:
            partes = nome.split(' - ', 1)
            candidato = partes[1].strip() if len(partes) > 1 else ''
            candidato = re.sub(r'\s*-\s*C[oó]pia\s*$', '', candidato, flags=re.IGNORECASE).strip()
            candidato = re.sub(r'^\d+\s*', '', candidato).strip()
            if candidato:
                print(f"  🏢 Empresa extraída (separador ' - '): '{candidato}'")
                return candidato

        match = re.match(
            r'^[A-ZÀÁÂÃÇÉÊÍÓÔÕÚÜ\s]+\d+\s+(.*)',
            nome
        )
        if match:
            candidato = match.group(1).strip()
            candidato = re.sub(r'^\d+\s*', '', candidato).strip()
            candidato = re.sub(r'\s*-\s*C[oó]pia\s*$', '', candidato, flags=re.IGNORECASE).strip()
            if candidato:
                print(f"  🏢 Empresa extraída (após número): '{candidato}'")
                return candidato

        keywords = [
            r'ISS\s+Empresa\s*[-–]\s*',
            r'COMPROVANTE\s+DE\s+PAGAMENTO\s+NF\s*',
            r'COMPROVANTE\s+DA\s+NOTA\s+FISCAL\s*',
            r'COMPROVANTE\s+DE\s+PAGAMENTO\s*',
            r'COMPROVANTE\s*',
            r'CADASTRO\s+NACIONAL\s+DE\s+PESSOA\s+JURIDICA\s*',
            r'CONSULTA\s+CNPJ\s*',
            r'CONSULTA\s+OPTANTE\s*',
            r'CONSULTA\s*',
            r'NOTA\s+FISCAL\s*',
            r'QUADRO\s+COMPARATIVO\s+[^-]*',
            r'GUIA\s+ISS\s*',
            r'DECLARA[CÇ][AÃ]O\s+[^-]*',
        ]
        for kw in keywords:
            nome = re.sub(kw, '', nome, flags=re.IGNORECASE).strip()

        nome = re.sub(r'^[\d\s\-–—]+', '', nome).strip()
        nome = re.sub(r'\s*-\s*C[oó]pia\s*$', '', nome, flags=re.IGNORECASE).strip()

        print(f"  🏢 Empresa extraída (fallback keywords): '{nome}'")
        return nome or '[EMPRESA]'

    # =========================================================
    # EXECUÇÃO PRINCIPAL
    # =========================================================

    def executar(self):
        """Executa o processo completo de automação"""
        print("\n" + "=" * 70)
        print("🤖 AUTOMAÇÃO SEI - INSERÇÃO DE DOCUMENTOS")
        print("=" * 70)

        print("\n🔍 Verificando configurações...")
        if not config.validar_configuracoes():
            print("\n❌ Corrija as configurações antes de continuar")
            return False

        # ── Conflitos de numeração não resolvidos (2 arquivos, mesmo número) ──
        pendentes = doc_ordem.conflitos_pendentes(self.pasta_documentos, config.BASE_DIR)
        if pendentes:
            print("\n❌ CONFLITO DE NUMERAÇÃO NÃO RESOLVIDO:")
            for grupo in pendentes:
                print("   Mesmo número, ordem ambígua entre:")
                for nome in grupo:
                    print(f"     - {nome}")
            print("\n   Abra a aba 'Documentos' na interface gráfica e defina")
            print("   qual arquivo vem primeiro antes de executar.")
            return False

        # ── Monta a sequência de tarefas a partir do pipeline ──────────
        try:
            self.montar_tarefas()
        except ValueError as e:
            print(f"\n❌ {e}")
            return False

        if not self.tarefas:
            print("\n❌ Nenhuma tarefa gerada — verifique a pasta de documentos e o pipeline.")
            return False

        try:
            indice = self._indice_retomada()
        except Exception as e:
            print(f"\n❌ {e}")
            return False

        tarefas_a_rodar = self.tarefas[indice:]
        if not tarefas_a_rodar:
            print("\n❌ Nada a executar a partir do ponto escolhido.")
            return False

        print("\n" + "=" * 70)
        print("⚠️  INSTRUÇÕES:")
        print("=" * 70)
        print("1. Firefox aberto e maximizado no SEI")
        print("2. Processo aberto e visível na tela")
        print("3. NÃO mexa no mouse/teclado durante a execução")
        print("4. Para CANCELAR: mova o mouse para o canto SUPERIOR ESQUERDO")
        print("=" * 70)
        print(f"\n📋 {len(tarefas_a_rodar)} tarefa(s) a executar (de {len(self.tarefas)} no pipeline completo).")

        print("\n⏳ Iniciando em 10 segundos... (Ctrl+C para cancelar)")
        try:
            for i in range(10, 0, -1):
                print(f"   {i}...", end='\r')
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\n❌ Cancelado pelo usuário")
            return False

        print("\n\n🚀 INICIANDO AUTOMAÇÃO...\n")

        # Retomando a partir do despacho de aprovação de NE: os dados da NE
        # vêm do que foi digitado na GUI (o arquivo da NE não roda nesta execução).
        if self.iniciar_do_despacho_ne:
            self.dados_contexto['ne_numero'] = self.despacho_numero_ne or '[NÚMERO]'
            self.dados_contexto['ne_data'] = self._data_fallback(self.despacho_data_ne)

        ciclo_atual_exibido = None
        try:
            for tarefa in tarefas_a_rodar:
                step = tarefa["step"]
                arquivo = tarefa["arquivo"]
                n_ciclo = tarefa["numero_ciclo"]

                if n_ciclo is not None and n_ciclo != ciclo_atual_exibido:
                    ciclo_atual_exibido = n_ciclo
                    print(f"\n{'=' * 70}")
                    print(f"🔁 CICLO NOTA FISCAL #{n_ciclo}")
                    print(f"{'=' * 70}")

                nome_exibicao = os.path.basename(arquivo) if arquivo else f"(gerado: {step['id']})"
                print(f"\n{'-' * 60}")
                print(f"📄 PASSO: {step['id'].upper()}  —  {nome_exibicao}")
                print(f"{'-' * 60}")

                processadores.processar(self, step, arquivo)

            print("\n" + "=" * 70)
            print("✅ AUTOMAÇÃO CONCLUÍDA!")
            print("=" * 70)
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
# MENU INTERATIVO (uso via terminal, sem GUI)
# =========================================================

def exibir_menu_tipo_processo():
    """Pergunta qual tipo de processo"""
    print("\n" + "=" * 70)
    print("🤖 SEI AUTOMATION - Sistema de Inserção Automática de Documentos")
    print("=" * 70)
    print("\nQual o tipo de processo?\n")
    print("  [1] DMPP (padrão)")
    print("  [2] UFIEC (com memorando)")
    print("  [0] Sair")
    print()

    try:
        opcao = input("Opção: ").strip()

        if opcao == '0':
            print("\n👋 Saindo...")
            return None
        if opcao == '1':
            return 'DMPP'
        if opcao == '2':
            return 'UFIEC'

        print("❌ Opção inválida")
        return exibir_menu_tipo_processo()

    except KeyboardInterrupt:
        print("\n\n👋 Saindo...")
        return None


def exibir_menu(tipo_processo):
    """Exibe menu interativo e retorna as opções selecionadas"""

    print("\n" + "-" * 70)
    print(f"Tipo de processo: {tipo_processo}")
    print("-" * 70)
    print("\nEscolha uma opção:\n")
    print("  [1] Executar do início (todos os documentos)")
    print("  [2] Pular documentos fixos (começar do ciclo 1)")
    print("  [3] Começar de um ciclo específico")
    print("  [4] Começar de um arquivo específico")
    print("  [5] Apenas o Despacho de Aprovação da NE (documento sem arquivo)")
    print("  [0] Sair")
    print()

    try:
        opcao = input("Opção: ").strip()

        if opcao == '0':
            print("\n👋 Saindo...")
            return None

        if opcao == '1':
            return {'pular_docs_fixos': False, 'ciclo_inicial': 1, 'arquivo_inicial': None}

        if opcao == '2':
            return {'pular_docs_fixos': True, 'ciclo_inicial': 1, 'arquivo_inicial': None}

        if opcao == '3':
            print()
            ciclo = input("Qual ciclo? (número): ").strip()
            try:
                ciclo_num = int(ciclo)
                if ciclo_num < 1:
                    print("❌ Número inválido. Usando ciclo 1.")
                    ciclo_num = 1
                return {'pular_docs_fixos': True, 'ciclo_inicial': ciclo_num, 'arquivo_inicial': None}
            except ValueError:
                print("❌ Número inválido. Usando ciclo 1.")
                return {'pular_docs_fixos': True, 'ciclo_inicial': 1, 'arquivo_inicial': None}

        if opcao == '4':
            print()
            arquivo = input("Qual o número do arquivo? (ex: 31): ").strip()
            try:
                arquivo_num = int(arquivo)
                if arquivo_num < 1:
                    print("❌ Número inválido.")
                    return exibir_menu(tipo_processo)
                return {'pular_docs_fixos': True, 'ciclo_inicial': 1, 'arquivo_inicial': arquivo_num}
            except ValueError:
                print("❌ Número inválido.")
                return exibir_menu(tipo_processo)

        if opcao == '5':
            print()
            numero = input("Número da Nota de Empenho: ").strip()
            data_ne = input("Data da Nota de Empenho (DD/MM/AAAA) [Enter = hoje]: ").strip()
            return {
                'pular_docs_fixos': True,
                'ciclo_inicial': 1,
                'arquivo_inicial': None,
                'iniciar_do_despacho_ne': True,
                'despacho_numero_ne': numero or None,
                'despacho_data_ne': data_ne or None,
            }

        print("❌ Opção inválida")
        return exibir_menu(tipo_processo)

    except KeyboardInterrupt:
        print("\n\n👋 Saindo...")
        return None


# =========================================================
# EXECUÇÃO
# =========================================================

if __name__ == "__main__":
    tipo_processo = exibir_menu_tipo_processo()

    if tipo_processo is None:
        exit(0)

    opcoes = exibir_menu(tipo_processo)

    if opcoes is None:
        exit(0)

    print("\n📋 Configuração selecionada:")
    print(f"   Tipo de processo: {tipo_processo}")
    print(f"   Pular docs fixos: {opcoes['pular_docs_fixos']}")
    print(f"   Ciclo inicial:    {opcoes['ciclo_inicial']}")
    if opcoes.get('arquivo_inicial'):
        print(f"   Arquivo inicial:  {opcoes['arquivo_inicial']}")

    automacao = SEIAutomation(
        pular_docs_fixos=opcoes['pular_docs_fixos'],
        ciclo_inicial=opcoes['ciclo_inicial'],
        arquivo_inicial=opcoes.get('arquivo_inicial'),
        tipo_processo=tipo_processo,
        iniciar_do_despacho_ne=opcoes.get('iniciar_do_despacho_ne', False),
        despacho_numero_ne=opcoes.get('despacho_numero_ne'),
        despacho_data_ne=opcoes.get('despacho_data_ne'),
    )

    sucesso = automacao.executar()

    if sucesso:
        print("\n✅ Processo finalizado com sucesso!")
    else:
        print("\n❌ Processo finalizado com erros")

    print("\nPressione ENTER para sair...")
    input()
