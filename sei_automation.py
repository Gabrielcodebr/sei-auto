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
    
    # Coordenadas calibradas (ajustadas para resolução 1600x900)
    COORD_BTN_INCLUIR_DOC = (354, 180)
    COORD_BARRA_PESQUISA = (761, 380)
    COORD_BTN_SALVAR_FORM = (1466, 751)
    COORD_RADIO_PUBLICO = (1122, 667)
    COORD_BTN_SALVAR_EDITOR = (230, 212)  # Não usado mais (usa Ctrl+Alt+S)
    COORD_AREA_EDICAO = (817, 589)  # Popup maximizado
    
    def __init__(self, pasta_documentos=None, pular_primeiros=0):
        """
        Args:
            pasta_documentos: Caminho da pasta com documentos
            pular_primeiros: Número de documentos para pular (se já foram inseridos)
        """
        self.pasta_documentos = pasta_documentos or config.DOCUMENTOS_DIR
        self.pular_primeiros = pular_primeiros
        self.documentos = []
        self.dados_contexto = {}  # Armazena dados entre documentos (ex: nome empresa, link NE)
        
    def carregar_documentos(self):
        """Carrega lista de documentos da pasta"""
        if not os.path.exists(self.pasta_documentos):
            raise Exception(f"Pasta não encontrada: {self.pasta_documentos}")
        
        # Lista todos os arquivos e ordena
        arquivos = sorted(os.listdir(self.pasta_documentos))
        
        # Filtra apenas PDFs e DOCX
        todos_docs = [
            os.path.join(self.pasta_documentos, f) 
            for f in arquivos 
            if f.lower().endswith(('.pdf', '.docx'))
        ]
        
        # Pula os primeiros se solicitado
        self.documentos = todos_docs[self.pular_primeiros:]
        
        print(f"\n📁 Total de documentos na pasta: {len(todos_docs)}")
        if self.pular_primeiros > 0:
            print(f"⏭️  Pulando os primeiros {self.pular_primeiros}")
        print(f"📄 Documentos a processar: {len(self.documentos)}")
        
        for i, doc in enumerate(self.documentos, self.pular_primeiros + 1):
            print(f"  {i}. {os.path.basename(doc)}")
        
        return self.documentos
    
    def aguardar(self, segundos=None):
        """Aguarda um tempo"""
        if segundos is None:
            segundos = config.WAIT_FOR_ELEMENT
        time.sleep(segundos)
    
    def clicar_botao_incluir_documento(self):
        """Clica no botão de incluir documento (ícone tracejado)"""
        print("\n🖱️ Clicando em 'Incluir Documento'...")
        
        pyautogui.click(self.COORD_BTN_INCLUIR_DOC)
        self.aguardar(1.5)
        
        print("✅ Lista de documentos aberta")
    
    def pesquisar_e_selecionar_tipo_doc(self, texto_busca):
        """
        Pesquisa e seleciona tipo de documento na lista
        Usa a barra de pesquisa do topo
        
        Args:
            texto_busca: Texto a pesquisar (ex: "Informação", "Externo")
        """
        print(f"🔍 Buscando: '{texto_busca}'")
        
        # Clica na barra de pesquisa
        pyautogui.click(self.COORD_BARRA_PESQUISA)
        self.aguardar(0.5)
        
        # Limpa e digita
        pyautogui.hotkey('ctrl', 'a')
        pyautogui.write(texto_busca, interval=0.05)
        self.aguardar(0.8)
        
        # Pressiona seta para baixo e Enter (seleciona primeiro resultado)
        pyautogui.press('down')
        self.aguardar(0.3)
        pyautogui.press('enter')
        self.aguardar(1.5)
        
        print(f"✅ Selecionado: '{texto_busca}'")
    
    def selecionar_dropdown_tipo_externo(self, tipo_documento):
        """
        Seleciona tipo no dropdown gigante de documentos externos
        Usa digitação rápida (padrão de dropdown)
        
        Args:
            tipo_documento: Nome do tipo (ex: "Nota de empenho")
        """
        print(f"📋 Selecionando tipo: '{tipo_documento}'")
        
        # Clica no dropdown
        pyautogui.click(315, 130)
        self.aguardar(0.8)
        
        # Digita rapidamente (dropdown filtra automaticamente)
        # Pega primeiras palavras para acelerar
        palavras = tipo_documento.split()[:3]
        texto_curto = ' '.join(palavras)
        
        pyautogui.write(texto_curto, interval=0.08)
        self.aguardar(1)
        
        # Pressiona Enter
        pyautogui.press('enter')
        self.aguardar(0.5)
        
        print(f"✅ Tipo selecionado")
    
    def preencher_campo(self, texto, tabs_antes=0, limpar=True):
        """
        Preenche campo atual com texto
        
        Args:
            texto: Texto a preencher
            tabs_antes: Número de TABs antes de preencher
            limpar: Se True, limpa o campo antes
        """
        for _ in range(tabs_antes):
            pyautogui.press('tab')
            self.aguardar(0.2)
        
        if limpar:
            # Limpa campo atual
            pyautogui.hotkey('ctrl', 'a')
            pyautogui.press('delete')
            self.aguardar(0.1)
        
        # Digita o texto
        if texto:
            pyautogui.write(str(texto), interval=0.03)
            self.aguardar(0.3)
    
    def selecionar_nivel_acesso_publico(self):
        """Rola até o final e seleciona Nível de Acesso: Público"""
        print("🔓 Selecionando Nível de Acesso: Público")
        
        # Rola para baixo
        for _ in range(6):
            pyautogui.scroll(-400)
            self.aguardar(0.2)
        
        # Clica no radio button Público usando coordenada calibrada
        pyautogui.click(self.COORD_RADIO_PUBLICO)
        self.aguardar(0.3)
        
        print("✅ Público selecionado")
    
    def clicar_salvar(self):
        """Clica no botão Salvar"""
        print("💾 Clicando em Salvar...")
        
        # Usa coordenada calibrada
        pyautogui.click(self.COORD_BTN_SALVAR_FORM)
        
        self.aguardar(2.5)
        
        # Aguarda popup do editor abrir
        print("  ⏳ Aguardando editor abrir...")
        self.aguardar(1)
        
        # Maximiza o popup: Alt+Espaço -> X
        print("  🖼️ Maximizando popup...")
        pyautogui.hotkey('alt', 'space')
        self.aguardar(0.3)
        pyautogui.press('x')
        self.aguardar(0.5)
        
        print("✅ Salvo e editor aberto")
    
    def colar_imagem_editor(self, imagem_obj):
        """
        Cola imagem no editor de texto do SEI
        
        Args:
            imagem_obj: Objeto PIL.Image
        """
        print("📋 Colando imagem no editor...")
        
        try:
            from PIL import Image
            import io
            import win32clipboard
            
            # Converte para formato do clipboard (Windows)
            output = io.BytesIO()
            imagem_obj.convert('RGB').save(output, 'BMP')
            data = output.getvalue()[14:]  # Remove BMP header
            output.close()
            
            # Coloca no clipboard
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
            win32clipboard.CloseClipboard()
            
            self.aguardar(0.5)
            
            # Clica na área de edição usando coordenada calibrada
            pyautogui.click(self.COORD_AREA_EDICAO)
            self.aguardar(0.3)
            
            # IMPORTANTE: Seleciona todo o conteúdo antes de colar
            pyautogui.hotkey('ctrl', 'a')
            self.aguardar(0.2)
            
            # Cola (substitui o conteúdo selecionado)
            pyautogui.hotkey('ctrl', 'v')
            self.aguardar(1.5)
            
            print("✅ Imagem colada")
            
        except Exception as e:
            print(f"❌ Erro ao colar imagem: {e}")
            raise
    
    def colar_texto_editor(self, texto):
        """
        Cola texto no editor
        
        Args:
            texto: Texto a colar
        """
        print("📝 Colando texto no editor...")
        
        # Copia para clipboard
        pyperclip.copy(texto)
        self.aguardar(0.3)
        
        # Clica na área de edição usando coordenada calibrada
        pyautogui.click(self.COORD_AREA_EDICAO)
        self.aguardar(0.3)
        
        # Seleciona tudo e substitui
        pyautogui.hotkey('ctrl', 'a')
        self.aguardar(0.2)
        pyautogui.hotkey('ctrl', 'v')
        self.aguardar(0.8)
        
        print("✅ Texto colado")
    
    def clicar_salvar_editor(self):
        """Salva e fecha o editor (popup)"""
        print("💾 Salvando no editor...")
        
        # Clica na área do editor para garantir que está focado
        pyautogui.click(self.COORD_AREA_EDICAO)
        self.aguardar(0.3)
        
        # Salva usando atalho do SEI: Ctrl+Alt+S
        pyautogui.hotkey('ctrl', 'alt', 's')
        
        # Aguarda o documento ser salvo
        print("  ⏳ Aguardando salvar...")
        self.aguardar(3)
        
        # Fecha o popup: Ctrl+W
        print("  🚪 Fechando popup...")
        pyautogui.hotkey('ctrl', 'w')
        self.aguardar(1.5)
        
        print("✅ Editor salvo e fechado")
    
    def anexar_arquivo_externo(self, arquivo_path):
        """
        Anexa arquivo em documento externo
        Usa janela de upload do Windows
        
        Args:
            arquivo_path: Caminho completo do arquivo PDF
        """
        print(f"📎 Anexando: {os.path.basename(arquivo_path)}")
        
        # Clica no botão "Anexar Arquivo..."
        pyautogui.click(74, 198)
        self.aguardar(2)
        
        # Janela de seleção do Windows abre
        print("  ⏳ Aguardando janela de upload...")
        self.aguardar(1)
        
        # Digita o caminho completo do arquivo
        # IMPORTANTE: Normaliza o caminho para Windows
        caminho_windows = os.path.abspath(arquivo_path)
        pyautogui.write(caminho_windows, interval=0.02)
        self.aguardar(0.5)
        
        # Pressiona Enter para confirmar
        pyautogui.press('enter')
        
        # Aguarda upload processar
        print("  ⏳ Processando upload...")
        self.aguardar(5)
        
        print("✅ Arquivo anexado")
    
    def capturar_link_documento_arvore(self, nome_documento):
        """
        Captura link de documento na árvore
        Clica com botão esquerdo no ícone → seleciona 3ª opção do menu
        
        Args:
            nome_documento: Nome do documento na árvore (para referência)
            
        Returns:
            Link copiado para clipboard
        """
        print(f"🔗 Capturando link: '{nome_documento}'")
        
        # NOTA: Assumindo que o documento está visível na árvore
        # A posição precisa ser ajustada baseado em onde o documento aparece
        
        # Clica no ícone do documento (PDF vermelho na árvore)
        # Posição aproximada - PRECISA AJUSTAR COM TESTE REAL
        pyautogui.click(69, 262)
        self.aguardar(0.8)
        
        # Menu contextual abre
        # Navega até 3ª opção (Copiar Link)
        pyautogui.press('down')
        pyautogui.press('down')
        pyautogui.press('enter')
        
        self.aguardar(0.8)
        
        # Link foi copiado para clipboard
        link = pyperclip.paste()
        print(f"✅ Link capturado: {link[:50]}...")
        
        return link
    
    def ler_texto_docx(self, docx_path):
        """
        Lê todo o texto de um arquivo .docx
        
        Args:
            docx_path: Caminho do arquivo .docx
            
        Returns:
            String com todo o texto
        """
        try:
            doc = DocxDocument(docx_path)
            texto = "\n".join([p.text for p in doc.paragraphs])
            print(f"  ✅ Texto extraído: {len(texto)} caracteres")
            return texto
        except Exception as e:
            print(f"❌ Erro ao ler .docx: {e}")
            return ""
    
    # ===== FUNÇÕES PARA CADA TIPO DE DOCUMENTO =====
    
    def processar_documento_01_capa(self, pdf_path):
        """01. CAPA"""
        print("\n" + "="*60)
        print("📄 DOCUMENTO 01: CAPA")
        print("="*60)
        
        # Processa imagem com regra especial
        imagem = pdf_utils.processar_capa_especial(pdf_path)
        if not imagem:
            raise Exception("Erro ao processar capa")
        
        # Clica em incluir documento
        self.clicar_botao_incluir_documento()
        
        # Seleciona "Informação"
        self.pesquisar_e_selecionar_tipo_doc("Informacao")
        
        # Preenche formulário
        self.aguardar(1)
        pyautogui.press('tab')  # Pula Texto Inicial (já vem Nenhum)
        self.aguardar(0.2)
        
        self.preencher_campo("Capa padrão imprensa oficial")  # Descrição
        pyautogui.press('tab')
        self.aguardar(0.2)
        
        self.preencher_campo("Capa")  # Nome na Árvore
        
        # Nível de acesso e salvar
        self.selecionar_nivel_acesso_publico()
        self.clicar_salvar()
        
        # Aguarda editor abrir
        self.aguardar(2)
        
        # Cola imagem
        self.colar_imagem_editor(imagem)
        
        # Salva editor
        self.clicar_salvar_editor()
        
        print("✅ CAPA inserida!\n")
    
    def processar_documento_02_solicitacao(self, pdf_path):
        """02. SOLICITAÇÃO DE ADIANTAMENTO"""
        print("\n" + "="*60)
        print("📄 DOCUMENTO 02: SOLICITAÇÃO DE ADIANTAMENTO")
        print("="*60)
        
        # Renderiza PDF
        imagem = pdf_utils.processar_print_padrao(pdf_path)
        if not imagem:
            raise Exception("Erro ao renderizar PDF")
        
        self.clicar_botao_incluir_documento()
        self.pesquisar_e_selecionar_tipo_doc("Solicitacao de licitacao")
        
        self.aguardar(1)
        pyautogui.press('tab')
        self.aguardar(0.2)
        
        self.preencher_campo("Solicitação de adiantamento")
        pyautogui.press('tab')
        self.aguardar(0.2)
        
        self.preencher_campo("adiantamento")
        
        self.selecionar_nivel_acesso_publico()
        self.clicar_salvar()
        self.aguardar(2)
        
        self.colar_imagem_editor(imagem)
        self.clicar_salvar_editor()
        
        print("✅ SOLICITAÇÃO inserida!\n")
    
    def processar_documento_03_nota_empenho(self, pdf_path):
        """03. NOTA DE EMPENHO"""
        print("\n" + "="*60)
        print("📄 DOCUMENTO 03: NOTA DE EMPENHO")
        print("="*60)
        
        # Extrai dados via OCR
        dados = pdf_utils.extrair_dados_nota_empenho(pdf_path)
        
        # Valida dados
        if not dados['data'] or not dados['numero']:
            print("⚠️ ATENÇÃO: Dados não extraídos completamente!")
            print("   Você precisará preencher manualmente após a execução")
        
        # Armazena no contexto para usar no despacho
        self.dados_contexto['ne_data'] = dados['data'] or '[DATA]'
        self.dados_contexto['ne_numero'] = dados['numero'] or '[NÚMERO]'
        
        self.clicar_botao_incluir_documento()
        self.pesquisar_e_selecionar_tipo_doc("Externo")
        
        self.aguardar(1.5)
        
        # Seleciona tipo no dropdown
        self.selecionar_dropdown_tipo_externo("Nota de empenho")
        
        # Preenche campos
        pyautogui.press('tab')
        self.aguardar(0.2)
        self.preencher_campo(dados['data'])  # Data
        
        pyautogui.press('tab')
        self.aguardar(0.2)
        self.preencher_campo(dados['numero'])  # Número
        
        pyautogui.press('tab')
        self.aguardar(0.2)
        self.preencher_campo(dados['numero'])  # Nome na Árvore
        
        # Formato: Nato-digital (já vem selecionado - primeiro radio)
        # Apenas avança
        pyautogui.press('tab')
        self.aguardar(0.2)
        
        self.selecionar_nivel_acesso_publico()
        
        # Anexa arquivo
        self.anexar_arquivo_externo(pdf_path)
        
        self.clicar_salvar()
        
        print("✅ NOTA DE EMPENHO inserida!\n")
    
    def processar_documento_04_despacho_ne(self):
        """04. DESPACHO DE APROVAÇÃO DA NOTA DE EMPENHO"""
        print("\n" + "="*60)
        print("📄 DOCUMENTO 04: DESPACHO DE APROVAÇÃO DA NE")
        print("="*60)
        
        print("⚠️ ATENÇÃO: Você precisará capturar o link manualmente")
        print("   1. Clique no ícone PDF da Nota de Empenho na árvore")
        print("   2. Selecione a 3ª opção do menu")
        print("   Pressione ENTER quando estiver pronto...")
        input()
        
        # Captura link da NE da árvore
        # NOTA: Esta função precisa de ajuste de coordenadas no teste real
        link_ne = pyperclip.paste()  # Assume que usuário já copiou
        
        if not link_ne or 'http' not in link_ne.lower():
            link_ne = '[LINK_DO_DOCUMENTO]'
            print("⚠️ Link não capturado. Será inserido placeholder.")
        
        # Monta texto do despacho
        texto = config.DESPACHO_APROVACAO_TEMPLATE.format(
            numero_ne=self.dados_contexto.get('ne_numero', '[NÚMERO]'),
            link_ne=link_ne,
            data_ne=self.dados_contexto.get('ne_data', '[DATA]')
        )
        
        self.clicar_botao_incluir_documento()
        self.pesquisar_e_selecionar_tipo_doc("Despacho")
        
        self.aguardar(1)
        pyautogui.press('tab')
        self.aguardar(0.2)
        
        self.preencher_campo("Aprovação de NE")
        pyautogui.press('tab')
        self.aguardar(0.2)
        
        self.preencher_campo("Aprovação de NE")
        
        self.selecionar_nivel_acesso_publico()
        self.clicar_salvar()
        self.aguardar(2)
        
        self.colar_texto_editor(texto)
        self.clicar_salvar_editor()
        
        print("✅ DESPACHO inserido!\n")
    
    def executar(self):
        """Executa o processo completo de automação"""
        print("\n" + "="*70)
        print("🤖 AUTOMAÇÃO SEI - INSERÇÃO DE DOCUMENTOS")
        print("="*70)
        
        # Validações
        print("\n🔍 Verificando configurações...")
        if not config.validar_configuracoes():
            print("\n❌ Corrija as configurações antes de continuar")
            return False
        
        # Carrega documentos
        self.carregar_documentos()
        
        if not self.documentos:
            print("\n❌ Nenhum documento encontrado!")
            return False
        
        # Instruções ao usuário
        print("\n" + "="*70)
        print("⚠️  INSTRUÇÕES IMPORTANTES:")
        print("="*70)
        print("1. Abra o FIREFOX e acesse o SEI")
        print("2. Abra o processo onde deseja inserir documentos")
        print("3. MAXIMIZE a janela do Firefox")
        print("4. DEIXE o processo VISÍVEL na tela")
        print("5. NÃO mexa no mouse/teclado durante a execução")
        print("6. Para CANCELAR a qualquer momento: mova o mouse para o")
        print("   canto SUPERIOR ESQUERDO da tela")
        print("="*70)
        
        print("\n⏳ Iniciando em 10 segundos...")
        print("   (Pressione Ctrl+C para cancelar agora)")
        
        try:
            for i in range(10, 0, -1):
                print(f"   {i}...", end='\r')
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\n❌ Cancelado pelo usuário")
            return False
        
        print("\n\n🚀 INICIANDO AUTOMAÇÃO...\n")
        
        try:
            # Processa os 4 primeiros documentos
            if len(self.documentos) >= 1:
                self.processar_documento_01_capa(self.documentos[0])
            
            if len(self.documentos) >= 2:
                self.processar_documento_02_solicitacao(self.documentos[1])
            
            if len(self.documentos) >= 3:
                self.processar_documento_03_nota_empenho(self.documentos[2])
            
            # O 4º é gerado automaticamente (despacho)
            self.processar_documento_04_despacho_ne()
            
            print("\n" + "="*70)
            print("✅ AUTOMAÇÃO CONCLUÍDA!")
            print("="*70)
            print("\n⚠️ IMPORTANTE: Verifique todos os documentos inseridos")
            print("   Confira se os dados de OCR estão corretos")
            
            return True
            
        except KeyboardInterrupt:
            print("\n\n⚠️ Automação cancelada pelo usuário")
            return False
        except Exception as e:
            print(f"\n\n❌ ERRO DURANTE EXECUÇÃO:")
            print(f"   {e}")
            print("\nDetalhes técnicos:")
            import traceback
            traceback.print_exc()
            return False


# ===== EXECUÇÃO =====

if __name__ == "__main__":
    print("="*70)
    print("SEI AUTOMATION - Sistema de Inserção Automática de Documentos")
    print("="*70)
    
    # Cria instância
    # Se quiser pular documentos já inseridos: SEIAutomation(pular_primeiros=2)
    automacao = SEIAutomation()
    
    # Executa
    sucesso = automacao.executar()
    
    if sucesso:
        print("\n✅ Processo finalizado com sucesso!")
    else:
        print("\n❌ Processo finalizado com erros")
    
    print("\nPressione ENTER para sair...")
    input()