"""
Script de automação para inserção de documentos no SEI (SP)
NAVEGADOR: Firefox
"""

import os
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
    # COORDENADAS - FORMULÁRIO DOCUMENTO INTERNO
    # (mesma tela para todos os docs tipo "Informação", "Despacho", etc.)
    # ← CALIBRAR: rode o script abaixo no terminal para descobrir:
    #
    #   import pyautogui, time
    #   print("Aponte para DESCRIÇÃO e aguarde 5s...")
    #   time.sleep(5); print(pyautogui.position())
    #   print("Aponte para NOME NA ÁRVORE e aguarde 5s...")
    #   time.sleep(5); print(pyautogui.position())
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
    COORD_DROPDOWN_TIPO_CONFERENCIA  = (1056, 478)  # ← CALIBRAR (só aparece ao clicar Digitalizado)
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
        """Carrega e ordena lista de documentos da pasta"""
        if not os.path.exists(self.pasta_documentos):
            raise Exception(f"Pasta não encontrada: {self.pasta_documentos}")

        arquivos = sorted(os.listdir(self.pasta_documentos))
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
        Reutilizável para todos os documentos internos.
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
        pyautogui.hotkey('ctrl', 'v')   # cola o caminho na janela do Windows
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

        print("✅ NOTA DE EMPENHO inserida!\n")

    def processar_documento_04_despacho_ne(self):
        """04. DESPACHO DE APROVAÇÃO DA NOTA DE EMPENHO"""
        print("\n" + "="*60)
        print("📄 DOCUMENTO 04: DESPACHO DE APROVAÇÃO DA NE")
        print("="*60)

        print("⚠️ ATENÇÃO: Copie o link da NE na árvore do SEI")
        print("   1. Clique com botão direito no ícone da Nota de Empenho")
        print("   2. Selecione a opção de copiar link")
        print("   Pressione ENTER quando o link estiver no clipboard...")
        input()

        link_ne = pyperclip.paste()
        if not link_ne or 'http' not in link_ne.lower():
            link_ne = '[LINK_DO_DOCUMENTO]'
            print("⚠️ Link não detectado. Será usado placeholder.")

        texto = config.DESPACHO_APROVACAO_TEMPLATE.format(
            numero_ne = self.dados_contexto.get('ne_numero', '[NÚMERO]'),
            link_ne   = link_ne,
            data_ne   = self.dados_contexto.get('ne_data', '[DATA]')
        )

        self.clicar_botao_incluir_documento()
        self.pesquisar_e_selecionar_tipo_doc("Despacho")
        self.preencher_formulario_interno("Aprovação de NE", "Aprovação de NE")
        self.selecionar_nivel_acesso_publico()
        self.clicar_salvar()
        self.aguardar(2)
        self.colar_texto_editor(texto)
        self.clicar_salvar_editor()

        print("✅ DESPACHO inserido!\n")

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
            if len(self.documentos) >= 1:
                self.processar_documento_01_capa(self.documentos[0])

            if len(self.documentos) >= 2:
                self.processar_documento_02_solicitacao(self.documentos[1])

            if len(self.documentos) >= 3:
                self.processar_documento_03_nota_empenho(self.documentos[2])

            self.processar_documento_04_despacho_ne()

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