# Contexto do projeto: sei-auto

## O que é

Automação RPA para inserção de documentos no SEI (Sistema Eletrônico de Informações) do Governo do Estado de São Paulo. O processo automatizado é a prestação de contas de adiantamentos — um servidor público recebe recursos antecipadamente, realiza compras, e precisa inserir dezenas de documentos comprobatórios num processo já aberto no SEI.

Sem a automação, esse processo é repetitivo e sujeito a erros: clicar em "Incluir Documento", pesquisar o tipo, preencher formulário, salvar, colar conteúdo, fechar popup — para cada um dos 17 documentos, alguns deles repetidos por nota fiscal.

O script não faz login, não abre processos, não assina documentos. Ele assume que o usuário já abriu o processo correto no SEI e então executa o restante.

---

## Ambiente técnico

- Windows 10 ou superior
- Resolução de tela: 1600x900 (crítico — as coordenadas de clique são absolutas para essa resolução)
- Firefox maximizado (não fullscreen), zoom em 100%
- SEI deve estar no monitor principal
- Python 3.10+
- Tesseract OCR instalado localmente

Bibliotecas Python (ver `requirements.txt`):

```
pyautogui    — cliques, teclas, scroll
pyperclip    — clipboard de texto
Pillow       — manipulação de imagens
pytesseract  — OCR via Tesseract
PyMuPDF      — renderização de PDF sem Poppler
python-docx  — leitura de .docx (não usado para converter, só para leitura de texto)
pywin32      — clipboard de imagens no Windows (CF_DIB)
```

Para converter .docx em imagem (documento 09), o código usa o Microsoft Word via automação COM (`win32com.client.Dispatch("Word.Application")`): abre o arquivo, salva como PDF temporário (FileFormat=17) e renderiza com PyMuPDF. O Word precisa estar instalado.

---

## Estrutura de arquivos

```
sei-auto/
├── config.py           — caminhos, constantes, template do despacho
├── ocr_utils.py        — extração de texto/dados de imagens
├── pdf_utils.py        — renderização de PDF, extração de dados de cada tipo de documento
├── sei_automation.py   — classe principal SEIAutomation + menu interativo
├── requirements.txt
├── documentos/         — pasta onde o usuário coloca os PDFs numerados
└── calibracao/         — scripts auxiliares para recalibrar coordenadas
    ├── calibracao.py
    ├── calibracao_externo.py
    ├── calibracao_conferencia.py
    ├── calibracao_interno.py
    ├── calibracao_completo.py
    ├── calibracao_icon.py
    ├── coordenadas.txt
    ├── coordenadas_externo.txt
    └── coordenadas_interno.txt
```

---

## Tipos de processo

O script suporta dois tipos de processo, selecionados no menu inicial:

- **DMPP** (padrão): Capa → Solicitação → NE → Despacho → OB → ciclos de NF → documentos finais
- **UFIEC**: Capa → Memorando/Justificativa → Solicitação → NE → Despacho → OB → ciclos de NF → documentos finais

A diferença prática é a posição dos documentos fixos e a coordenada do ícone da NE na árvore (usada para capturar o link para o despacho).

---

## Sequência de documentos

### Documentos fixos (DMPP)

| Pos | Tipo | Documento |
|-----|------|-----------|
| 1 | interno | Capa (print de PDF com corte especial) |
| 2 | interno | Solicitação de Adiantamento (print de PDF) |
| 3 | externo | Nota de Empenho (upload de PDF, extrai data e número via OCR) |
| 4 | interno | Despacho de Aprovação da NE (texto fixo com link capturado da árvore) |
| 5 | externo | Ordem Bancária (upload de PDF, extrai data e número via OCR) |

Para UFIEC, o Memorando/Justificativa entra como documento 2, deslocando os demais.

### Ciclos de nota fiscal (repete para cada NF)

| Pos no ciclo | Tipo | Documento |
|-------------|------|-----------|
| 1 | interno | Quadro Comparativo de Preços (print de PDF) |
| 2 | externo | Nota Fiscal (upload de PDF, extrai data; número e empresa vêm do nome do arquivo) |
| 3 | externo | Comprovante da Nota Fiscal (upload, digitalizado) |
| 4 | interno | Declaração de Recebimento (LibreOffice converte .docx em imagem) |
| 5 | externo | Consulta de Optante (upload, extrai CNPJ via OCR) |
| 6 | externo | CNPJ (upload, reutiliza CNPJ da consulta) |
| 7 | externo | Guia de Recolhimento do ISS (opcional, upload) |
| 8 | externo | Comprovante de ISS (opcional, upload) |

O fim dos ciclos é detectado automaticamente pela presença de um arquivo com "balancete" no nome.

### Documentos finais (após todos os ciclos)

| Pos | Tipo | Documento |
|-----|------|-----------|
| 1 | interno | Balancete de Despesas (print de PDF) |
| 2 | externo | Extrato Bancário (upload, extrai data via OCR) |
| 3 | interno | Relatório de Conciliação Contábil (print de PDF) |
| 4 | interno | Declaração de Encerramento (print de PDF) |

---

## Fluxo de cada tipo de documento

### Documento interno (print de PDF)

1. Clica em "Incluir Documento"
2. Pesquisa o tipo (ex: "Informacao") e seleciona com Down+Enter
3. Aguarda 3s para o formulário carregar
4. Preenche "Descrição" e "Nome na Árvore" via Ctrl+A → Ctrl+V (pyperclip)
5. Rola até "Nível de Acesso" e clica em "Público"
6. Clica em "Salvar" — o popup do editor abre
7. Maximiza o popup: Alt+Espaço → X
8. Clica na área de edição, Ctrl+A, Ctrl+V (imagem via win32clipboard CF_DIB)
9. Salva: Ctrl+Alt+S; fecha: Ctrl+W

### Documento externo (upload de PDF)

1. Clica em "Incluir Documento" → seleciona "Externo"
2. Seleciona tipo no dropdown digitando as primeiras palavras
3. Preenche Data, Número e Nome na Árvore via clique em coordenada + Ctrl+V
4. Seleciona formato: Nato-digital ou Digitalizado
   - Se Digitalizado: seleciona tipo de conferência no dropdown ("Cópia Autenticada Administrativamente")
5. Seleciona "Público" (coordenada diferente da dos internos: `COORD_RADIO_PUBLICO_EXTERNO`)
6. Clica em "Anexar Arquivo", cola o caminho na janela do Windows, Enter
7. Aguarda 5s o upload
8. Rola para baixo (layout muda após upload)
9. Clica em "Salvar" (a janela fecha, não abre editor)
10. Verifica se o SEI exibiu popup de "documento similar" e descarta se necessário

### Capa (caso especial)

Após renderizar o PDF, o código executa OCR para localizar o texto "Tribunal de Contas do Estado de São Paulo" e corta tudo acima dessa linha. O resultado é colado no editor como os demais documentos internos.

### Despacho de aprovação (caso especial)

O despacho contém um link clicável para a NE. O SEI interpreta o formato `#{XXXXX|YYYYY}#` como referência interna quando colado no editor.

O processo é:
1. Capturar o link clicando no ícone da NE na árvore do processo (Tab+Tab+Enter) — o link vai para o clipboard
2. Dividir o template do despacho em texto-antes-do-link e texto-depois-do-link
3. Colar em três partes: texto → link → texto
4. Entre o link e o texto seguinte, pressiona Space+Enter+Enter para o SEI "confirmar" o link

### Declaração de Recebimento (caso especial)

O arquivo é um .docx. O código converte a primeira página para imagem usando o Word via COM:
- `win32com.client.Dispatch("Word.Application")` abre o Word em background
- Salva o .docx como PDF temporário em um diretório temporário (FileFormat=17)
- PyMuPDF renderiza a primeira página do PDF temporário como imagem
- A imagem é colada no editor como qualquer outro documento interno

---

## Extração de dados

### Dados extraídos via OCR

- **Nota de Empenho**: número (padrão `YYYYNE#####`) e data após "Data Emissão"
- **Ordem Bancária**: número e data após "Data Pagamento"
- **Nota Fiscal**: data (o número vem do nome do arquivo)
- **Consulta de Optante**: CNPJ e data
- **CNPJ**: data (o CNPJ é reutilizado da consulta quando possível)
- **Extrato Bancário**: data

### Dados extraídos do nome do arquivo

Para nota fiscal e documentos de ciclo, o número da NF e o nome da empresa são extraídos do nome do arquivo — mais confiável que OCR em documentos de terceiros com layouts variados.

Convenção de nome esperada: `NN-TIPO [NUMERO] NOME DA EMPRESA.pdf`

Exemplos de extração:
- `"37-NOTA FISCAL 17249 ITU LUZ COMÉRCIO.pdf"` → número `"17249"`, empresa `"ITU LUZ COMÉRCIO"`
- `"13-COMPROVANTE DE PAGAMENTO NF 8273 JOSÉ CARLOS ROSATI.pdf"` → empresa `"JOSÉ CARLOS ROSATI"`

A lógica remove o prefixo numérico, palavras-chave conhecidas e o número solto que sobra, deixando o nome da empresa.

---

## Coordenadas de clique

Todas as coordenadas são absolutas para resolução 1600x900 e estão definidas como constantes de classe em `SEIAutomation`. As principais:

```python
# Tela principal
COORD_BTN_INCLUIR_DOC   = (354, 180)
COORD_BARRA_PESQUISA    = (761, 380)
COORD_BTN_SALVAR_FORM   = (1466, 757)
COORD_RADIO_PUBLICO     = (1120, 668)   # formulários internos
COORD_AREA_EDICAO       = (817, 589)    # popup maximizado

# Formulário documento externo
COORD_DROPDOWN_TIPO_EXTERNO     = (451, 351)
COORD_CAMPO_DATA                = (1038, 357)
COORD_CAMPO_NUMERO              = (406, 413)
COORD_CAMPO_NOME_ARVORE         = (616, 413)
COORD_RADIO_NATO_DIGITAL        = (411, 482)
COORD_RADIO_DIGITALIZADO        = (410, 503)
COORD_DROPDOWN_TIPO_CONFERENCIA = (1056, 478)
COORD_BTN_ANEXAR_ARQUIVO        = (406, 608)
COORD_RADIO_PUBLICO_EXTERNO     = (1114, 541)

# Ícones na árvore (para capturar link da NE)
COORD_ICONE_NE_ARVORE_DMPP  = (49, 246)
COORD_ICONE_NE_ARVORE_UFIEC = (48, 304)
```

Se a resolução mudar, use os scripts em `calibracao/` para recalibrar.

---

## Menu interativo

Ao executar `sei_automation.py`, dois menus são exibidos em sequência:

1. **Tipo de processo**: DMPP ou UFIEC
2. **Ponto de início**:
   - Do início (todos os documentos)
   - Pular documentos fixos (começa do ciclo 1)
   - Começar de um ciclo específico (pula N-1 ciclos e reinicia)
   - Começar de um arquivo específico pelo número prefixo (ex: 31)

---

## Padrão para adicionar novos tipos de documento

Métodos de documento interno:
```python
def processar_documento_NN_nome(self, pdf_path):
    imagem = pdf_utils.processar_print_padrao(pdf_path)
    self.clicar_botao_incluir_documento()
    self.pesquisar_e_selecionar_tipo_doc("TipoBuscado")
    self.preencher_formulario_interno("Descrição", "Nome árvore")
    self.selecionar_nivel_acesso_publico()
    self.clicar_salvar()
    self.colar_imagem_editor(imagem)
    self.clicar_salvar_editor()
```

Métodos de documento externo:
```python
def processar_documento_NN_nome(self, pdf_path):
    dados = pdf_utils.extrair_dados_xxx(pdf_path)
    self.clicar_botao_incluir_documento()
    self.pesquisar_e_selecionar_tipo_doc("Externo")
    self.aguardar(1.5)
    self.selecionar_dropdown_tipo_externo("Tipo no dropdown")
    self.preencher_campo_clicando(self.COORD_CAMPO_DATA,        dados['data'])
    self.preencher_campo_clicando(self.COORD_CAMPO_NUMERO,      dados['numero'])
    self.preencher_campo_clicando(self.COORD_CAMPO_NOME_ARVORE, dados['nome'])
    pyautogui.click(self.COORD_RADIO_NATO_DIGITAL)
    self.aguardar(0.3)
    self.selecionar_nivel_acesso_publico_externo()
    self.anexar_arquivo_externo(pdf_path)
    for _ in range(3):
        pyautogui.scroll(-400)
        self.aguardar(0.2)
    self.clicar_salvar()
    self.verificar_popup_documento_similar()
    self.aguardar(2)
```

---

## Problemas conhecidos e soluções

**Campos não preenchem texto com acento**: `pyautogui.write()` não suporta acentos. Solução já implementada: sempre usar `pyperclip.copy()` + `Ctrl+V`.

**Layout muda após upload de arquivo**: O formulário externo expande ao anexar. Solução: selecionar "Público" antes de anexar, rolar novamente após o upload antes de salvar.

**Popup de documento similar**: O SEI pode exibir alerta quando já existe documento do mesmo tipo. `verificar_popup_documento_similar()` tira um screenshot da região central, busca o texto via OCR e clica em OK. Como fallback, pressiona Enter (o botão OK fica focado por padrão no SEI).

**Popup do editor abre em posição variável**: Sempre maximizar com Alt+Espaço → X antes de interagir.

**Link da NE não capturado**: `capturar_link_documento_arvore()` retorna `'[LINK_DO_DOCUMENTO]'` como placeholder quando o clipboard não contém o link esperado. O usuário precisa corrigir manualmente.

---

## Configurações em config.py

```python
TESSERACT_PATH = r"C:\...\Tesseract-OCR\tesseract.exe"  # ajustar para o ambiente
DOCUMENTOS_DIR = os.path.join(BASE_DIR, "documentos")
PAUSE_BETWEEN_ACTIONS = 0.5   # pausa global do pyautogui entre ações
WAIT_FOR_ELEMENT = 1.0        # espera para elementos carregarem
MAX_UPLOAD_WAIT = 10          # tempo máximo para upload de arquivo
PDF_DPI = 200                 # DPI base para renderização (reduzido 20% em pdf_utils)
OCR_LANGUAGE = "por"
DESPACHO_APROVACAO_TEMPLATE = """..."""  # template com {numero_ne}, {link_ne}, {data_ne}
```

---

## Notas sobre o SEI-SP

- O editor de texto do SEI é um popup TinyMCE. O atalho para salvar é Ctrl+Alt+S.
- Links internos usam o formato `#{ID|PROTOCOLO}#` que o editor converte em hiperlink ao ser colado.
- O SEI pode abrir o popup do editor em posições diferentes dependendo do scroll atual da página.
- Qualquer mudança na UI do SEI (versão nova, redesign) pode quebrar as coordenadas ou os seletores de tipo de documento.
