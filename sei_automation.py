"""
Script de automação para inserção de documentos no SEI (SP)
NAVEGADOR: Firefox

VERSÃO 2.0 - Correções:
- Número da Nota Fiscal extraído do nome do arquivo (mais confiável que OCR)
- Menu interativo para iniciar de um ponto específico
- Guia de Recolhimento do ISS com nome correto
"""

import os
import re
import time
from datetime import date
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
    """Classe principal para automação do SEI.

    Todas as coordenadas, tempos e textos editáveis vivem em config.py.
    """

    def __init__(self, pasta_documentos=None, pular_primeiros=0, ciclo_inicial=1, pular_docs_fixos=False, arquivo_inicial=None, tipo_processo='DMPP',
             apenas_despacho_ne=False, despacho_numero_ne=None, despacho_data_ne=None):
        """
        Args:
            pasta_documentos:   Caminho da pasta com documentos
            pular_primeiros:    Número de documentos para pular (já inseridos)
            ciclo_inicial:      Número do ciclo de NF para iniciar (1 = primeiro ciclo)
            pular_docs_fixos:   Se True, pula docs fixos iniciais
            arquivo_inicial:    Número do arquivo para iniciar (ex: 31 para começar no arquivo 31)
            tipo_processo:      'DMPP' (padrão) ou 'UFIEC' (com memorando)
            apenas_despacho_ne: Se True, executa SÓ o Despacho de Aprovação da NE
            despacho_numero_ne: Número da NE (usado quando apenas_despacho_ne=True)
            despacho_data_ne:   Data da NE (usado quando apenas_despacho_ne=True)
        """
        self.pasta_documentos  = pasta_documentos or config.DOCUMENTOS_DIR
        self.pular_primeiros   = pular_primeiros
        self.ciclo_inicial     = ciclo_inicial
        self.pular_docs_fixos  = pular_docs_fixos
        self.arquivo_inicial   = arquivo_inicial
        self.tipo_processo     = tipo_processo
        self.apenas_despacho_ne = apenas_despacho_ne
        self.despacho_numero_ne = despacho_numero_ne
        self.despacho_data_ne   = despacho_data_ne
        self.documentos        = []
        self.dados_contexto    = {}  # Dados compartilhados entre documentos

    # =========================================================
    # UTILITÁRIOS
    # =========================================================

    def aguardar(self, segundos=None):
        if segundos is None:
            segundos = config.WAIT_FOR_ELEMENT
        time.sleep(segundos)

    def _data_fallback(self, data):
        """Retorna a data fornecida ou a data de hoje como último recurso (formato DD/MM/YYYY)"""
        if data:
            return data
        hoje = date.today().strftime('%d/%m/%Y')
        print(f"  ⚠️ Data não encontrada — usando data de hoje como fallback: {hoje}")
        return hoje

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
    # FUNÇÕES DE EXTRAÇÃO DO NOME DO ARQUIVO
    # =========================================================

    def identificar_tipo_documento_ciclo(self, filepath):
        nome = os.path.basename(filepath).lower()

        # ISS primeiro (mais específico)
        if 'iss' in nome:
            # Verifica se 'comprovante' aparece ANTES de 'iss' no nome
            pos_iss = nome.find('iss')
            pos_comp = nome.find('comprovante')
            if pos_comp != -1 and pos_comp < pos_iss:
                return 'comprov_iss'  # ex: "COMPROVANTE ISS..."
            elif 'comprovante' in nome:
                return 'guia_iss_com_comprovante'  # ex: "GUIA ISS E COMPROVANTE..."
            else:
                return 'guia_iss'

        if 'quadro' in nome or 'planilha' in nome or 'comparativo' in nome:
            return 'quadro'

        pos_nf   = nome.find('nota fiscal') if 'nota fiscal' in nome else (
                nome.find('nf ') if 'nf ' in nome else (
                nome.find('nf-') if 'nf-' in nome else -1))
        pos_comp = nome.find('comprovante') if 'comprovante' in nome else -1

        if pos_nf != -1 and pos_comp != -1:
            if pos_comp < pos_nf:
                return 'comprovante'  # "COMPROVANTE PAGAMENTO NOTA FISCAL..." → só comprovante
            else:
                return 'nota_fiscal_com_comprovante'  # NF vem antes → arquivo duplo
        if pos_nf != -1:
            return 'nota_fiscal'
        if pos_comp != -1:
            return 'comprovante'

        if 'declaracao' in nome or 'declaração' in nome or filepath.lower().endswith('.docx'):
            return 'declaracao'
        if 'cnpj' in nome or 'cadastro' in nome:
            return 'cnpj'
        if 'consulta' in nome or 'optante' in nome:
            return 'consulta'

        return None

    def agrupar_ciclos(self, docs_ciclo):
        """
        Agrupa os documentos de ciclo em ciclos individuais baseado no tipo
        detectado pelo nome do arquivo. Cada ciclo começa com um 'quadro'.

        Returns:
            list de listas, cada sublista = [(filepath, tipo, indice_original), ...]
        """
        # Tagueia cada arquivo com seu tipo
        tagged = []
        for i, doc in enumerate(docs_ciclo):
            tipo = self.identificar_tipo_documento_ciclo(doc)
            tagged.append((doc, tipo, i))

        # Agrupa: cada ciclo começa num 'quadro'
        ciclos = []
        ciclo_atual = None

        for doc, tipo, orig_idx in tagged:
            if tipo == 'quadro':
                if ciclo_atual is not None:
                    ciclos.append(ciclo_atual)
                ciclo_atual = [(doc, tipo, orig_idx)]
            else:
                if ciclo_atual is None:
                    print(f"  ⚠️ Arquivo antes do primeiro quadro comparativo, ignorando: {os.path.basename(doc)}")
                    continue
                ciclo_atual.append((doc, tipo, orig_idx))

        if ciclo_atual is not None:
            ciclos.append(ciclo_atual)

        return ciclos

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
        
        # Remove prefixo numérico (ordem): "37-" ou "7-"
        nome_sem_ordem = re.sub(r'^\d+[-\s]*', '', nome_sem_ext)
        
        # Encontra todos os números restantes
        numeros = re.findall(r'\d+', nome_sem_ordem)
        
        if numeros:
            # O primeiro número após remover a ordem é o número da nota
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

        # Estratégia 1: separador " - " explícito no nome
        # Ex: "DECLARAÇÃO DE RECEBIMENTO - EMPRESA XYZ"
        #     "CONSULTA OPTANTE - EMPRESA XYZ"
        #     "NOTA FISCAL 1939 - EMPRESA XYZ" (alguns arquivos usam esse padrão)
        if ' - ' in nome:
            # Pega tudo após o ÚLTIMO " - " que precede o nome da empresa
            # Mas pode haver " - " dentro do nome da empresa, então pega após o PRIMEIRO
            # que ocorre depois de palavras-chave conhecidas de tipo de documento
            partes = nome.split(' - ', 1)  # divide no primeiro traço apenas
            candidato = partes[1].strip() if len(partes) > 1 else ''
            # Remove "Copia"/"Cópia" no final (Windows duplica arquivos assim)
            candidato = re.sub(r'\s*-\s*C[oó]pia\s*$', '', candidato, flags=re.IGNORECASE).strip()
            # Remove número solto no início (ex: "2 EMPRESA XYZ" → "EMPRESA XYZ")
            candidato = re.sub(r'^\d+\s*', '', candidato).strip()
            if candidato:
                print(f"  🏢 Empresa extraída (separador ' - '): '{candidato}'")
                return candidato

        # Estratégia 2: remove bloco de palavras maiúsculas do início até o número
        # Ex: "NOTA FISCAL 1939 EMPRESA XYZ" → remove "NOTA FISCAL 1939" → "EMPRESA XYZ"
        # Ex: "ISS Empresa - GAMA FILTROS..." → já tratado acima pelo ' - '
        #
        # Detecta sequência: PALAVRAS_MAIÚSCULAS + possível número → resto é empresa
        match = re.match(
            r'^[A-ZÀÁÂÃÇÉÊÍÓÔÕÚÜ\s]+\d+\s+(.*)',  # "TIPO ... NÚMERO EMPRESA"
            nome
        )
        if match:
            candidato = match.group(1).strip()
            candidato = re.sub(r'^\d+\s*', '', candidato).strip()
            candidato = re.sub(r'\s*-\s*C[oó]pia\s*$', '', candidato, flags=re.IGNORECASE).strip()
            if candidato:
                print(f"  🏢 Empresa extraída (após número): '{candidato}'")
                return candidato

        # Estratégia 3: fallback com keywords explícitas (mantido como última saída)
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
            r'DECLARA[CÇ][AÃ]O\s+[^-]*',  # qualquer "DECLARAÇÃO DE ..." genérico
        ]
        for kw in keywords:
            nome = re.sub(kw, '', nome, flags=re.IGNORECASE).strip()

        nome = re.sub(r'^[\d\s\-–—]+', '', nome).strip()
        nome = re.sub(r'\s*-\s*C[oó]pia\s*$', '', nome, flags=re.IGNORECASE).strip()

        print(f"  🏢 Empresa extraída (fallback keywords): '{nome}'")
        return nome or '[EMPRESA]'

    # =========================================================
    # AÇÕES BÁSICAS
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

        # Clica UMA vez para focar o editor e não toca mais no mouse
        pyautogui.click(config.COORD_AREA_EDICAO)
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
        pyautogui.click(*config.COORD_REFOCO_EDITOR)
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

        doc_cfg = config.DOCUMENTOS['capa']
        self.clicar_botao_incluir_documento()
        self.pesquisar_e_selecionar_tipo_doc(doc_cfg['busca'])
        self.preencher_formulario_interno(doc_cfg['descricao'], doc_cfg['nome_arvore'])
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

        doc_cfg = config.DOCUMENTOS['solicitacao']
        self.clicar_botao_incluir_documento()
        self.pesquisar_e_selecionar_tipo_doc(doc_cfg['busca'])
        self.preencher_formulario_interno(doc_cfg['descricao'], doc_cfg['nome_arvore'])
        self.selecionar_nivel_acesso_publico()
        self.clicar_salvar()
        self.colar_imagem_editor(imagem)
        self.clicar_salvar_editor()

        print("✅ SOLICITAÇÃO inserida!\n")

    def processar_documento_02b_memorando_justificativa(self, pdf_path):
        """02b. MEMORANDO/JUSTIFICATIVA (somente UFIEC)"""
        print("\n" + "="*60)
        print("📄 DOCUMENTO 02b: MEMORANDO/JUSTIFICATIVA")
        print("="*60)

        imagem = pdf_utils.processar_print_padrao(pdf_path)
        if not imagem:
            raise Exception("Erro ao renderizar PDF")

        doc_cfg = config.DOCUMENTOS['memorando_justificativa']
        self.clicar_botao_incluir_documento()
        self.pesquisar_e_selecionar_tipo_doc(doc_cfg['busca'])
        self.preencher_formulario_interno(doc_cfg['descricao'], doc_cfg['nome_arvore'])
        self.selecionar_nivel_acesso_publico()
        self.clicar_salvar()
        self.colar_imagem_editor(imagem)
        self.clicar_salvar_editor()

        print("✅ MEMORANDO/JUSTIFICATIVA inserido!\n")

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
        self.dados_contexto['ne_data']   = self._data_fallback(dados['data'])
        self.dados_contexto['ne_numero'] = dados['numero'] or '[NÚMERO]'

        doc_cfg = config.DOCUMENTOS['nota_empenho']
        self.clicar_botao_incluir_documento()
        self.pesquisar_e_selecionar_tipo_doc(doc_cfg['busca'])
        self.aguardar(config.TEMPOS['pos_pesquisa_externo'])

        self.selecionar_dropdown_tipo_externo(doc_cfg['tipo_externo'])
        self.preencher_campo_clicando(config.COORD_CAMPO_DATA,         self.dados_contexto['ne_data'])
        self.preencher_campo_clicando(config.COORD_CAMPO_NUMERO,       dados['numero'])
        self.preencher_campo_clicando(config.COORD_CAMPO_NOME_ARVORE,  dados['numero'])

        pyautogui.click(config.COORD_RADIO_NATO_DIGITAL)
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
        self.aguardar(config.TEMPOS['recarregar_tela'])

    def processar_documento_04_despacho_ne(self):
        """04. DESPACHO DE APROVAÇÃO DA NOTA DE EMPENHO"""
        print("\n" + "="*60)
        print("📄 DOCUMENTO 04: DESPACHO DE APROVAÇÃO DA NE")
        print("="*60)

        # Captura o link da NE — usa coordenada diferente para UFIEC
        if self.tipo_processo == 'UFIEC':
            coord_ne = config.COORD_ICONE_NE_ARVORE_UFIEC
        else:
            coord_ne = config.COORD_ICONE_NE_ARVORE_DMPP
        
        link_ne = self.capturar_link_documento_arvore(coord_ne)

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

        doc_cfg = config.DOCUMENTOS['despacho_aprovacao_ne']
        self.clicar_botao_incluir_documento()
        self.pesquisar_e_selecionar_tipo_doc(doc_cfg['busca'])
        self.preencher_formulario_interno(doc_cfg['descricao'], doc_cfg['nome_arvore'])
        self.selecionar_nivel_acesso_publico()
        self.clicar_salvar()
        self.aguardar(config.TEMPOS['pos_click_salvar_doc04'])

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

        doc_cfg = config.DOCUMENTOS['ordem_bancaria']
        self.clicar_botao_incluir_documento()
        self.pesquisar_e_selecionar_tipo_doc(doc_cfg['busca'])
        self.aguardar(config.TEMPOS['pos_pesquisa_externo'])

        self.selecionar_dropdown_tipo_externo(doc_cfg['tipo_externo'])
        self.preencher_campo_clicando(config.COORD_CAMPO_DATA,        self._data_fallback(dados['data']))
        self.preencher_campo_clicando(config.COORD_CAMPO_NUMERO,      dados['numero'])
        self.preencher_campo_clicando(config.COORD_CAMPO_NOME_ARVORE, dados['numero'])

        pyautogui.click(config.COORD_RADIO_NATO_DIGITAL)
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
        self.aguardar(config.TEMPOS['recarregar_tela'])

    def processar_documento_06_quadro_comparativo(self, pdf_path):
        """06. QUADRO COMPARATIVO DE PREÇOS (Planilha de Pesquisa de Preço)"""
        print("\n" + "="*60)
        print("📄 DOCUMENTO 06: QUADRO COMPARATIVO DE PREÇOS")
        print("="*60)

        imagem = pdf_utils.processar_planilha_pesquisa_preco(pdf_path)
        if not imagem:
            raise Exception("Erro ao renderizar PDF")

        doc_cfg = config.DOCUMENTOS['quadro_comparativo']
        self.clicar_botao_incluir_documento()
        self.pesquisar_e_selecionar_tipo_doc(doc_cfg['busca'])
        self.preencher_formulario_interno(doc_cfg['descricao'], doc_cfg['nome_arvore'])
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
        pyautogui.click(config.COORD_DROPDOWN_TIPO_CONFERENCIA)
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

        # NÚMERO: Pega do nome do arquivo (mais confiável que OCR!)
        numero_do_nome = self.extrair_numero_nota_fiscal_do_nome(pdf_path)
        if numero_do_nome:
            dados['numero'] = numero_do_nome
        
        if not dados['data'] or not dados['numero']:
            print("⚠️ ATENÇÃO: Dados não extraídos completamente!")
            print(f"  Data:    '{dados.get('data', '')}'")
            print(f"  Número:  '{dados.get('numero', '')}'")

        # Empresa vem do nome do arquivo (mais confiável que OCR)
        empresa = self.extrair_empresa_do_nome_arquivo(pdf_path)

        # Guarda no contexto — comprovante reutiliza
        self.dados_contexto['nf_data']    = self._data_fallback(dados['data'])
        self.dados_contexto['nf_numero']  = dados['numero'] or '[NÚMERO]'
        self.dados_contexto['nf_empresa'] = empresa

        doc_cfg = config.DOCUMENTOS['nota_fiscal']
        self.clicar_botao_incluir_documento()
        self.pesquisar_e_selecionar_tipo_doc(doc_cfg['busca'])
        self.aguardar(config.TEMPOS['pos_pesquisa_externo'])

        self.selecionar_dropdown_tipo_externo(doc_cfg['tipo_externo'])
        self.preencher_campo_clicando(config.COORD_CAMPO_DATA,        self.dados_contexto['nf_data'])
        self.preencher_campo_clicando(config.COORD_CAMPO_NUMERO,      dados['numero'])
        # Nome na árvore: nome da empresa
        self.preencher_campo_clicando(config.COORD_CAMPO_NOME_ARVORE, self.dados_contexto['nf_empresa'])

        pyautogui.click(config.COORD_RADIO_NATO_DIGITAL)
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
        self.aguardar(config.TEMPOS['recarregar_tela'])

    def processar_documento_08_comprovante_fiscal(self, pdf_path):
        """08. COMPROVANTE DA NOTA FISCAL (digitalizado)"""
        print("\n" + "="*60)
        print("📄 DOCUMENTO 08: COMPROVANTE DA NOTA FISCAL")
        print("="*60)

        # Reutiliza os dados da NF já extraída (inclusive empresa do nome do arquivo)
        data    = self.dados_contexto.get('nf_data',    '[DATA]')
        numero  = self.dados_contexto.get('nf_numero',  '[NÚMERO]')
        empresa = self.dados_contexto.get('nf_empresa', '[EMPRESA]')

        doc_cfg = config.DOCUMENTOS['comprovante_fiscal']
        self.clicar_botao_incluir_documento()
        self.pesquisar_e_selecionar_tipo_doc(doc_cfg['busca'])
        self.aguardar(config.TEMPOS['pos_pesquisa_externo'])

        self.selecionar_dropdown_tipo_externo(doc_cfg['tipo_externo'])
        self.preencher_campo_clicando(config.COORD_CAMPO_DATA,        data)
        self.preencher_campo_clicando(config.COORD_CAMPO_NUMERO,      numero)
        self.preencher_campo_clicando(config.COORD_CAMPO_NOME_ARVORE, empresa)

        # Digitalizado → habilita dropdown de tipo de conferência
        pyautogui.click(config.COORD_RADIO_DIGITALIZADO)
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
        self.aguardar(config.TEMPOS['recarregar_tela'])

    def processar_documento_09_declaracao_recebimento(self, docx_path):
        """09. DECLARAÇÃO DE RECEBIMENTO (interno - print da primeira página do .docx)"""
        print("\n" + "="*60)
        print("📄 DOCUMENTO 09: DECLARAÇÃO DE RECEBIMENTO")
        print("="*60)

        imagem = pdf_utils.renderizar_docx_como_imagem(docx_path)
        if not imagem:
            raise Exception(
                "Erro ao renderizar .docx da declaração.\n"
                "O Microsoft Word precisa estar instalado (a conversão usa win32com).\n"
                "Verifique se o Word está instalado e acessível na máquina."
            )

        # Fonte 1: nome do arquivo (sempre disponível, independe de contexto)
        empresa = self.extrair_empresa_do_nome_arquivo(docx_path)

        # Fonte 2: contexto como validação — se o arquivo não deu empresa mas o
        # contexto tem, usa o contexto; se ambos têm, prefere o do arquivo
        if empresa == '[EMPRESA]':
            empresa_ctx = self.dados_contexto.get('nf_empresa', '')
            if empresa_ctx:
                empresa = empresa_ctx
                print(f"  ℹ️ Empresa vinda do contexto (fallback): '{empresa}'")

        doc_cfg = config.DOCUMENTOS['declaracao_recebimento']
        self.clicar_botao_incluir_documento()
        self.pesquisar_e_selecionar_tipo_doc(doc_cfg['busca'])
        self.preencher_formulario_interno(doc_cfg['descricao'], empresa)
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

        doc_cfg = config.DOCUMENTOS['consulta_optante']
        self.clicar_botao_incluir_documento()
        self.pesquisar_e_selecionar_tipo_doc(doc_cfg['busca'])
        self.aguardar(config.TEMPOS['pos_pesquisa_externo'])

        self.selecionar_dropdown_tipo_externo(doc_cfg['tipo_externo'])
        self.preencher_campo_clicando(config.COORD_CAMPO_DATA,        self._data_fallback(dados['data']))
        self.preencher_campo_clicando(config.COORD_CAMPO_NUMERO,      dados['numero'] or '[CNPJ]')
        self.preencher_campo_clicando(config.COORD_CAMPO_NOME_ARVORE, empresa)

        pyautogui.click(config.COORD_RADIO_NATO_DIGITAL)
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
        self.aguardar(config.TEMPOS['recarregar_tela'])

    def processar_documento_11_cnpj(self, pdf_path):
        """11. CNPJ (documento externo)"""
        print("\n" + "="*60)
        print("📄 DOCUMENTO 11: CNPJ")
        print("="*60)

        dados   = pdf_utils.extrair_dados_cnpj(pdf_path)
        empresa = self.extrair_empresa_do_nome_arquivo(pdf_path)

        # CNPJ: usa sempre o do documento de Consulta Optante (mais confiável)
        cnpj = self.dados_contexto.get('consulta_cnpj')
        if cnpj:
            print(f"  ✅ CNPJ reutilizado da Consulta Optante: {cnpj}")
        else:
            cnpj = dados['numero']
            print(f"  ⚠️ CNPJ da consulta não disponível — extraindo do PDF: {cnpj}")
        if not cnpj:
            cnpj = '[CNPJ]'
            print("  ❌ CNPJ não encontrado em nenhuma fonte!")

        doc_cfg = config.DOCUMENTOS['cnpj']
        self.clicar_botao_incluir_documento()
        self.pesquisar_e_selecionar_tipo_doc(doc_cfg['busca'])
        self.aguardar(config.TEMPOS['pos_pesquisa_externo'])

        self.selecionar_dropdown_tipo_externo(doc_cfg['tipo_externo'])
        self.preencher_campo_clicando(config.COORD_CAMPO_DATA,        self._data_fallback(dados['data']))
        self.preencher_campo_clicando(config.COORD_CAMPO_NUMERO,      cnpj)
        self.preencher_campo_clicando(config.COORD_CAMPO_NOME_ARVORE, empresa)

        pyautogui.click(config.COORD_RADIO_NATO_DIGITAL)
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
        self.aguardar(config.TEMPOS['recarregar_tela'])

    def processar_documento_12_guia_iss(self, pdf_path):
        """12. GUIA DE RECOLHIMENTO DO ISS (documento externo, opcional)"""
        print("\n" + "="*60)
        print("📄 DOCUMENTO 12: GUIA DE RECOLHIMENTO DO ISS")
        print("="*60)

        dados = pdf_utils.extrair_dados_guia_iss(pdf_path)

        # Guarda no contexto para o comprovante ISS reutilizar
        self.dados_contexto['iss_data']   = self._data_fallback(dados['data'])
        self.dados_contexto['iss_numero'] = dados['numero'] or '[NÚMERO]'

        doc_cfg = config.DOCUMENTOS['guia_iss']
        self.clicar_botao_incluir_documento()
        self.pesquisar_e_selecionar_tipo_doc(doc_cfg['busca'])
        self.aguardar(config.TEMPOS['pos_pesquisa_externo'])

        self.selecionar_dropdown_tipo_externo(doc_cfg['tipo_externo'])
        self.preencher_campo_clicando(config.COORD_CAMPO_DATA,        self.dados_contexto['iss_data'])
        self.preencher_campo_clicando(config.COORD_CAMPO_NUMERO,      self.dados_contexto['iss_numero'])
        self.preencher_campo_clicando(config.COORD_CAMPO_NOME_ARVORE, self.dados_contexto['iss_numero'])

        pyautogui.click(config.COORD_RADIO_NATO_DIGITAL)
        self.aguardar(0.3)

        self.selecionar_nivel_acesso_publico_externo()
        self.anexar_arquivo_externo(pdf_path)

        print("  📜 Ajustando scroll após upload...")
        for _ in range(3):
            pyautogui.scroll(-400)
            self.aguardar(0.2)

        self.clicar_salvar()
        self.verificar_popup_documento_similar()

        print("✅ GUIA DE RECOLHIMENTO DO ISS inserida!\n")

        print("  ⏳ Aguardando tela principal recarregar...")
        self.aguardar(config.TEMPOS['recarregar_tela'])

    def processar_documento_13_comprovante_iss(self, pdf_path):
        """13. COMPROVANTE DE ISS (documento externo, opcional)"""
        print("\n" + "="*60)
        print("📄 DOCUMENTO 13: COMPROVANTE DE ISS")
        print("="*60)

        # Reutiliza dados da guia ISS já extraída — igual ao comprovante fiscal com a NF
        data   = self.dados_contexto.get('iss_data')
        numero = self.dados_contexto.get('iss_numero')

        # Fallback: extrai do arquivo caso venha de um ponto de retomada (opção 4 do menu)
        if not data or not numero or numero == '[NÚMERO]':
            print("  ⚠️ Dados ISS não encontrados no contexto — extraindo do arquivo...")
            dados  = pdf_utils.extrair_dados_guia_iss(pdf_path)
            data   = self._data_fallback(dados['data'])
            numero = dados['numero'] or '[NÚMERO]'

        # Empresa: do contexto se disponível, senão do nome do arquivo
        empresa = self.dados_contexto.get('nf_empresa', '')
        if not empresa:
            empresa = self.extrair_empresa_do_nome_arquivo(pdf_path)

        doc_cfg = config.DOCUMENTOS['comprovante_iss']
        self.clicar_botao_incluir_documento()
        self.pesquisar_e_selecionar_tipo_doc(doc_cfg['busca'])
        self.aguardar(config.TEMPOS['pos_pesquisa_externo'])

        self.selecionar_dropdown_tipo_externo(doc_cfg['tipo_externo'])
        self.preencher_campo_clicando(config.COORD_CAMPO_DATA,        data)
        self.preencher_campo_clicando(config.COORD_CAMPO_NUMERO,      numero)
        self.preencher_campo_clicando(config.COORD_CAMPO_NOME_ARVORE, empresa)

        pyautogui.click(config.COORD_RADIO_DIGITALIZADO)
        self.aguardar(0.5)

        self.selecionar_tipo_conferencia("Cópia Autenticada Administrativamente")

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
        self.aguardar(config.TEMPOS['recarregar_tela'])

    def processar_documento_14_balancete(self, pdf_path):
        """14. BALANCETE DE DESPESAS COM ADIANTAMENTO (interno)"""
        print("\n" + "="*60)
        print("📄 DOCUMENTO 14: BALANCETE")
        print("="*60)

        imagem = pdf_utils.processar_print_padrao(pdf_path)
        if not imagem:
            raise Exception("Erro ao renderizar PDF do balancete")

        doc_cfg = config.DOCUMENTOS['balancete']
        self.clicar_botao_incluir_documento()
        self.pesquisar_e_selecionar_tipo_doc(doc_cfg['busca'])
        self.preencher_formulario_interno(doc_cfg['descricao'], doc_cfg['nome_arvore'])
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

        doc_cfg = config.DOCUMENTOS['extrato_bancario']
        self.clicar_botao_incluir_documento()
        self.pesquisar_e_selecionar_tipo_doc(doc_cfg['busca'])
        self.aguardar(config.TEMPOS['pos_pesquisa_externo'])

        self.selecionar_dropdown_tipo_externo(doc_cfg['tipo_externo'])
        self.preencher_campo_clicando(config.COORD_CAMPO_DATA,        self._data_fallback(data))
        self.preencher_campo_clicando(config.COORD_CAMPO_NOME_ARVORE, doc_cfg['nome_arvore_fixo'])

        pyautogui.click(config.COORD_RADIO_NATO_DIGITAL)
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
        self.aguardar(config.TEMPOS['recarregar_tela'])

    def processar_documento_16_conciliacao_contabil(self, pdf_path):
        """16. RELATÓRIO DE CONCILIAÇÃO CONTÁBIL (interno)"""
        print("\n" + "="*60)
        print("📄 DOCUMENTO 16: CONCILIAÇÃO CONTÁBIL")
        print("="*60)

        imagem = pdf_utils.processar_print_padrao(pdf_path)
        if not imagem:
            raise Exception("Erro ao renderizar PDF da conciliação")

        doc_cfg = config.DOCUMENTOS['conciliacao_contabil']
        self.clicar_botao_incluir_documento()
        self.pesquisar_e_selecionar_tipo_doc(doc_cfg['busca'])
        self.preencher_formulario_interno(doc_cfg['descricao'], doc_cfg['nome_arvore'])
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

        doc_cfg = config.DOCUMENTOS['declaracao_encerramento']
        self.clicar_botao_incluir_documento()
        self.pesquisar_e_selecionar_tipo_doc(doc_cfg['busca'])
        self.preencher_formulario_interno(doc_cfg['descricao'], doc_cfg['nome_arvore'])
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

        # Índice onde começam os ciclos (DMPP=4, UFIEC=5 por ter o memorando)
        inicio_ciclos = 5 if self.tipo_processo == 'UFIEC' else 4

        if idx_balancete is not None:
            docs_ciclo   = self.documentos[inicio_ciclos:idx_balancete]
            docs_finais  = self.documentos[idx_balancete:]
            print(f"\n📊 Balancete encontrado na posição {idx_balancete + 1}")
            print(f"   Arquivos nos ciclos: {len(docs_ciclo)}")
            print(f"   Arquivos finais:     {len(docs_finais)}")
        else:
            docs_ciclo  = self.documentos[inicio_ciclos:]
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

        # Mostra informações sobre ponto de início
        if self.pular_docs_fixos:
            print("\n⏭️  MODO: Pulando documentos fixos (1-5)")
        if self.ciclo_inicial > 1:
            print(f"\n⏭️  MODO: Iniciando do ciclo {self.ciclo_inicial}")
        if self.arquivo_inicial:
            print(f"\n⏭️  MODO: Iniciando do arquivo {self.arquivo_inicial}")

        print("\n⏳ Iniciando em 10 segundos... (Ctrl+C para cancelar)")
        try:
            for i in range(10, 0, -1):
                print(f"   {i}...", end='\r')
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\n❌ Cancelado pelo usuário")
            return False

        print("\n\n🚀 INICIANDO AUTOMAÇÃO...\n")
        
        # ── Atalho: apenas o Despacho de Aprovação da NE ────────────
        if self.apenas_despacho_ne:
            print("\n" + "="*60)
            print("📄 MODO: Apenas Despacho de Aprovação da NE")
            print("="*60)
            self.dados_contexto['ne_numero'] = self.despacho_numero_ne or '[NÚMERO]'
            self.dados_contexto['ne_data']   = self._data_fallback(self.despacho_data_ne)
            try:
                self.processar_documento_04_despacho_ne()
                print("\n" + "="*70)
                print("✅ DESPACHO DE APROVAÇÃO DA NE INSERIDO!")
                print("="*70)
                return True
            except Exception as e:
                print(f"\n\n❌ ERRO DURANTE EXECUÇÃO: {e}")
                import traceback
                traceback.print_exc()
                return False

        try:
            # ── Encontra posição do arquivo inicial (antes de processar qualquer seção) ──
            docs_iniciais = self.documentos[:inicio_ciclos]
            arquivo_inicial_idx_iniciais = None
            arquivo_inicial_idx = None
            tipo_arquivo_inicial = None
            arquivo_inicial_idx_finais = None

            if self.arquivo_inicial:
                # 1) Procura nos documentos iniciais (fixos)
                for i, doc in enumerate(docs_iniciais):
                    nome = os.path.basename(doc)
                    match = re.match(r'^(\d+)', nome)
                    if match and int(match.group(1)) == self.arquivo_inicial:
                        arquivo_inicial_idx_iniciais = i
                        print(f"\n📄 Arquivo {self.arquivo_inicial} encontrado nos documentos iniciais: {nome}")
                        break

                # 2) Procura nos ciclos
                if arquivo_inicial_idx_iniciais is None:
                    for i, doc in enumerate(docs_ciclo):
                        nome = os.path.basename(doc)
                        match = re.match(r'^(\d+)', nome)
                        if match and int(match.group(1)) == self.arquivo_inicial:
                            arquivo_inicial_idx = i
                            tipo_arquivo_inicial = self.identificar_tipo_documento_ciclo(doc)
                            print(f"\n📄 Arquivo {self.arquivo_inicial} encontrado nos ciclos: {nome}")
                            print(f"   Tipo identificado: {tipo_arquivo_inicial}")
                            break

                # 3) Procura nos documentos finais
                if arquivo_inicial_idx_iniciais is None and arquivo_inicial_idx is None:
                    for i, doc in enumerate(docs_finais):
                        nome = os.path.basename(doc)
                        match = re.match(r'^(\d+)', nome)
                        if match and int(match.group(1)) == self.arquivo_inicial:
                            arquivo_inicial_idx_finais = i
                            print(f"\n📄 Arquivo {self.arquivo_inicial} encontrado nos documentos finais: {nome}")
                            break

                if arquivo_inicial_idx_iniciais is None and arquivo_inicial_idx is None and arquivo_inicial_idx_finais is None:
                    print(f"\n⚠️ Arquivo {self.arquivo_inicial} não encontrado em nenhuma seção!")
                    print("   Começando do primeiro ciclo...")

            # ── Documentos fixos (pula se solicitado) ───────────────────
            if arquivo_inicial_idx_iniciais is not None or (not self.pular_docs_fixos and self.ciclo_inicial == 1 and not self.arquivo_inicial):
                inicio_iniciais = arquivo_inicial_idx_iniciais if arquivo_inicial_idx_iniciais is not None else 0

                if self.tipo_processo == 'UFIEC':
                    # UFIEC: Capa(0) → Memorando(1) → Solicitação(2) → NE(3) → Despacho → OB(4)
                    print("\n📋 Processo UFIEC - Com Memorando/Justificativa")

                    if inicio_iniciais <= 0 and len(self.documentos) >= 1:
                        self.processar_documento_01_capa(self.documentos[0])

                    if inicio_iniciais <= 1 and len(self.documentos) >= 2:
                        self.processar_documento_02b_memorando_justificativa(self.documentos[1])

                    if inicio_iniciais <= 2 and len(self.documentos) >= 3:
                        self.processar_documento_02_solicitacao(self.documentos[2])

                    if inicio_iniciais <= 3 and len(self.documentos) >= 4:
                        self.processar_documento_03_nota_empenho(self.documentos[3])

                    if inicio_iniciais <= 3:
                        self.processar_documento_04_despacho_ne()

                    if inicio_iniciais <= 4 and len(self.documentos) >= 5:
                        self.processar_documento_05_ordem_bancaria(self.documentos[4])
                else:
                    # DMPP (padrão): Capa(0) → Solicitação(1) → NE(2) → Despacho → OB(3)
                    print("\n📋 Processo DMPP - Padrão")

                    if inicio_iniciais <= 0 and len(self.documentos) >= 1:
                        self.processar_documento_01_capa(self.documentos[0])

                    if inicio_iniciais <= 1 and len(self.documentos) >= 2:
                        self.processar_documento_02_solicitacao(self.documentos[1])

                    if inicio_iniciais <= 2 and len(self.documentos) >= 3:
                        self.processar_documento_03_nota_empenho(self.documentos[2])

                    if inicio_iniciais <= 2:
                        self.processar_documento_04_despacho_ne()

                    if inicio_iniciais <= 3 and len(self.documentos) >= 4:
                        self.processar_documento_05_ordem_bancaria(self.documentos[3])
            else:
                print("\n⏭️  Pulando documentos fixos...")

            # ── Ciclos de Notas Fiscais ─────────────────────────────────
            # Agrupa por tipo detectado no nome do arquivo (não mais por posição fixa)
            ciclos = self.agrupar_ciclos(docs_ciclo)
            print(f"\n📊 {len(ciclos)} ciclo(s) detectado(s) nos documentos")
            for i, ciclo in enumerate(ciclos, 1):
                tipos = [t for _, t, _ in ciclo]
                print(f"   Ciclo {i}: {len(ciclo)} arquivo(s) — tipos: {tipos}")

            num_nf = 1

            # Se o arquivo inicial está nos finais, pula todos os ciclos
            if arquivo_inicial_idx_finais is not None:
                ciclos = []

            # Pula ciclos se necessário (opção 3 do menu)
            if self.ciclo_inicial > 1 and not self.arquivo_inicial:
                ciclos_a_pular = self.ciclo_inicial - 1
                print(f"\n⏭️  Pulando {ciclos_a_pular} ciclo(s)...")
                ciclos = ciclos[ciclos_a_pular:]
                num_nf = self.ciclo_inicial

            # Tabela de despacho: tipo → handler
            handler_map = {
                'quadro':       self.processar_documento_06_quadro_comparativo,
                'nota_fiscal':  self.processar_documento_07_nota_fiscal,
                'comprovante':  self.processar_documento_08_comprovante_fiscal,
                'declaracao':   self.processar_documento_09_declaracao_recebimento,
                'consulta':     self.processar_documento_10_consulta_optante,
                'cnpj':         self.processar_documento_11_cnpj,
                'guia_iss':     self.processar_documento_12_guia_iss,
                'comprov_iss':  self.processar_documento_13_comprovante_iss,
            }

            for ciclo in ciclos:
                print(f"\n{'='*70}")
                print(f"🔁 CICLO NOTA FISCAL #{num_nf}")
                print(f"{'='*70}")

                for filepath, tipo, orig_idx in ciclo:
                    # Skip arquivo_inicial
                    if arquivo_inicial_idx is not None:
                        if orig_idx < arquivo_inicial_idx:
                            print(f"  ⏭️ Pulando: {os.path.basename(filepath)}")
                            continue
                        elif orig_idx == arquivo_inicial_idx:
                            arquivo_inicial_idx = None  # Encontrou, para de pular

                    # Caso especial: NF + Comprovante combinados → upload duplo
                    if tipo == 'nota_fiscal_com_comprovante':
                        self.processar_documento_07_nota_fiscal(filepath)
                        self.processar_documento_08_comprovante_fiscal(filepath)
                        continue
                    
                    if tipo == 'guia_iss_com_comprovante':
                        self.processar_documento_12_guia_iss(filepath)
                        self.processar_documento_13_comprovante_iss(filepath)
                        continue

                    # Despacho normal por tipo
                    handler = handler_map.get(tipo)
                    if handler:
                        handler(filepath)
                    else:
                        print(f"  ⚠️ Tipo desconhecido '{tipo}' para: {os.path.basename(filepath)}")

                num_nf += 1

            # ── Documentos finais (após todos os ciclos) ────────────────
            inicio_finais = arquivo_inicial_idx_finais if arquivo_inicial_idx_finais is not None else 0
            if inicio_finais <= 0 and len(docs_finais) >= 1:
                self.processar_documento_14_balancete(docs_finais[0])

            if inicio_finais <= 1 and len(docs_finais) >= 2:
                self.processar_documento_15_extrato_bancario(docs_finais[1])

            if inicio_finais <= 2 and len(docs_finais) >= 3:
                self.processar_documento_16_conciliacao_contabil(docs_finais[2])

            if inicio_finais <= 3 and len(docs_finais) >= 4:
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
# MENU INTERATIVO
# =========================================================

def exibir_menu_tipo_processo():
    """Pergunta qual tipo de processo"""
    print("\n" + "="*70)
    print("🤖 SEI AUTOMATION - Sistema de Inserção Automática de Documentos")
    print("="*70)
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
    
    # Define quantidade de docs fixos baseado no tipo
    docs_fixos = "1-6" if tipo_processo == 'UFIEC' else "1-5"
    
    print("\n" + "-"*70)
    print(f"Tipo de processo: {tipo_processo}")
    print("-"*70)
    print("\nEscolha uma opção:\n")
    print(f"  [1] Executar do início (todos os documentos)")
    print(f"  [2] Pular documentos fixos (começar do ciclo 1)")
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
                'pular_docs_fixos':   True,
                'ciclo_inicial':      1,
                'arquivo_inicial':    None,
                'apenas_despacho_ne': True,
                'despacho_numero_ne': numero or None,
                'despacho_data_ne':   data_ne or None,
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
    # Primeiro menu: tipo de processo
    tipo_processo = exibir_menu_tipo_processo()
    
    if tipo_processo is None:
        exit(0)
    
    # Segundo menu: opções de execução
    opcoes = exibir_menu(tipo_processo)
    
    if opcoes is None:
        exit(0)
    
    print(f"\n📋 Configuração selecionada:")
    print(f"   Tipo de processo: {tipo_processo}")
    print(f"   Pular docs fixos: {opcoes['pular_docs_fixos']}")
    print(f"   Ciclo inicial:    {opcoes['ciclo_inicial']}")
    if opcoes.get('arquivo_inicial'):
        print(f"   Arquivo inicial:  {opcoes['arquivo_inicial']}")
    
    # Cria instância com as opções selecionadas
    automacao = SEIAutomation(
        pular_docs_fixos=opcoes['pular_docs_fixos'],
        ciclo_inicial=opcoes['ciclo_inicial'],
        arquivo_inicial=opcoes.get('arquivo_inicial'),
        tipo_processo=tipo_processo,
        apenas_despacho_ne=opcoes.get('apenas_despacho_ne', False),
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