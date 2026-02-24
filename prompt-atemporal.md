# PROMPT PARA CONTINUAÇÃO DO PROJETO: AUTOMAÇÃO SEI-SP

## 📌 CONTEXTO DO PROJETO

Este é um projeto de **automação RPA (Robotic Process Automation)** para inserção de documentos no **SEI (Sistema Eletrônico de Informações)** do Governo do Estado de São Paulo. O sistema automatiza um processo manual repetitivo de prestação de contas de adiantamento, reduzindo o tempo de trabalho de horas para minutos.

### Objetivo Principal
Automatizar a inserção de 16 tipos diferentes de documentos em processos já abertos no SEI, seguindo uma ordem específica e preenchendo formulários com dados extraídos via OCR.

---

## 🖥️ AMBIENTE TÉCNICO

### Sistema Operacional
- **Windows 10 ou superior**
- Resolução de tela: **1600x900 pixels** (CRÍTICO - coordenadas calibradas para esta resolução)
- Dois monitores (SEI deve estar no monitor principal)

### Navegador
- **Mozilla Firefox** (maximizado, não fullscreen F11)
- Zoom: **100%**

### Linguagem e Ferramentas
- **Python 3.10+**
- IDE: Visual Studio Code
- Terminal: Git Bash
- Ambiente virtual: venv

### Bibliotecas Python
```
pyautogui         # Automação de mouse/teclado
pynput            # Eventos de input
pillow            # Manipulação de imagens
pytesseract       # OCR (reconhecimento de texto)
PyMuPDF (fitz)    # Renderização de PDF (substitui pdf2image/poppler)
pyperclip         # Clipboard
python-docx       # Leitura de arquivos .docx
pywin32           # Clipboard de imagens no Windows
```

### Dependências Externas
- **Tesseract OCR** instalado em: `C:\Users\Gabriel Fatec Itu\AppData\Local\Programs\Tesseract-OCR\tesseract.exe`
- **Poppler NÃO é mais necessário** (substituído por PyMuPDF)

---

## 📁 ESTRUTURA DO PROJETO

```
sei-auto/
├── venv/                           # Ambiente virtual Python
├── documentos/                     # PDFs numerados em ordem
│   ├── 1-CAPA DE ADIANTAMENTO.pdf
│   ├── 2-SOLICITAÇÃO DE ADIANTAMENTO.pdf
│   ├── 3-NOTA DE EMPENHO.pdf
│   └── ... (demais documentos)
├── .gitignore
├── README.md
├── config.py                       # Configurações e caminhos
├── ocr_utils.py                    # Funções de OCR
├── pdf_utils.py                    # Manipulação de PDF (usa PyMuPDF)
├── sei_automation.py               # Script principal
├── calibracao.py                   # Calibração de coordenadas
├── calibracao_externo.py           # Calibração doc. externos
├── calibracao_conferencia.py       # Calibração dropdown conferência
├── coordenadas.txt                 # Coordenadas salvas
└── coordenadas_externo.txt         # Coordenadas externas salvas
```

---

## 🎯 COORDENADAS CALIBRADAS (1600x900)

### Tela Principal do SEI
```python
COORD_BTN_INCLUIR_DOC = (354, 180)      # Botão "Incluir Documento"
COORD_BARRA_PESQUISA = (761, 380)       # Barra de pesquisa de tipos
COORD_BTN_SALVAR_FORM = (1466, 751)     # Botão "Salvar" formulário
COORD_RADIO_PUBLICO = (1122, 667)       # Radio button "Público"
COORD_AREA_EDICAO = (817, 589)          # Área do editor (popup maximizado)
```

### Formulário Documento Externo
```python
COORD_DROPDOWN_TIPO_EXTERNO = (672, 353)          # Dropdown tipo documento
COORD_CAMPO_DATA = (1044, 353)                    # Campo "Data"
COORD_CAMPO_NUMERO = (395, 418)                   # Campo "Número"
COORD_CAMPO_NOME_ARVORE = (595, 411)              # Campo "Nome na Árvore"
COORD_RADIO_NATO_DIGITAL = (413, 479)             # Radio "Nato-digital"
COORD_RADIO_DIGITALIZADO = (414, 507)             # Radio "Digitalizado"
COORD_DROPDOWN_TIPO_CONFERENCIA = (1056, 478)    # Dropdown "Tipo Conferência"
COORD_BTN_ANEXAR_ARQUIVO = (405, 603)             # Botão "Anexar Arquivo"
```

**IMPORTANTE:** Estas coordenadas são para resolução 1600x900. Se a resolução mudar, é necessário recalibrar usando os scripts `calibracao.py`.

---

## 📋 OS 16 TIPOS DE DOCUMENTOS (EM ORDEM)

### DOCUMENTOS INTERNOS (print de PDF ou texto)
1. **CAPA** - Print de PDF com corte especial
2. **SOLICITAÇÃO DE ADIANTAMENTO** - Print de PDF
3. ~~(Nota de Empenho é externa)~~
4. **DESPACHO DE APROVAÇÃO DA NE** - Texto fixo com link capturado
5. ~~(Ordem Bancária é externa)~~
6. **QUADRO COMPARATIVO DE PREÇOS** - Print de PDF
7. ~~(Ciclo de Notas Fiscais - externas e internas)~~
13. **BALANCETE** - Print de PDF
14. ~~(Extrato Bancário é externo)~~
15. **CONCILIAÇÃO CONTÁBIL** - Print de PDF
16. **DECLARAÇÃO DE ENCERRAMENTO** - Print de PDF

### DOCUMENTOS EXTERNOS (upload de PDF)
3. **NOTA DE EMPENHO** - Upload PDF, extrai data/número via OCR
5. **ORDEM BANCÁRIA** - Upload PDF, extrai data/número via OCR
7. **NOTA FISCAL** - Upload PDF, extrai data/número/empresa via OCR
8. **COMPROVANTE DA NOTA FISCAL** - Upload PDF
9. **DECLARAÇÃO DE RECEBIMENTO** - Texto copiado de arquivo .DOCX
10. **CONSULTA DE OPTANTE** - Upload PDF
11. **CNPJ** - Upload PDF, extrai CNPJ via OCR
12. **GUIA DE ISS** (quando houver) - Upload PDF, extrai data/número
13. **COMPROVANTE ISS** (quando houver) - Upload PDF
14. **EXTRATO BANCÁRIO** - Upload PDF, extrai data via OCR

**CICLO:** Documentos 7-12 se repetem para cada nota fiscal no processo.

---

## 🔄 FLUXO DE AUTOMAÇÃO

### Documento INTERNO (com print de PDF)
1. Clica botão "Incluir Documento"
2. Pesquisa tipo (ex: "Informação")
3. Aguarda formulário carregar (3 segundos)
4. Preenche "Descrição" e "Nome na Árvore" (usando `Ctrl+A` + `Ctrl+V`)
5. Rola até "Nível de Acesso" → seleciona "Público"
6. Clica "Salvar" → popup do editor abre
7. **Maximiza popup:** `Alt+Espaço` → `X`
8. Clica na área de edição
9. Seleciona tudo: `Ctrl+A`
10. Cola imagem: `Ctrl+V`
11. Salva: `Ctrl+Alt+S`
12. Fecha popup: `Ctrl+W`

### Documento EXTERNO (com upload de PDF)
1. Clica botão "Incluir Documento"
2. Seleciona "Externo"
3. Seleciona tipo no dropdown (ex: "Nota de empenho")
4. Preenche campos usando coordenadas calibradas:
   - Data (clica coord → digita)
   - Número (clica coord → digita)
   - Nome na Árvore (clica coord → digita)
5. Seleciona formato (Nato-digital OU Digitalizado)
   - Se Digitalizado: seleciona "Cópia Autenticada Administrativamente"
6. **Rola até "Nível de Acesso"** → seleciona "Público"
7. **Rola até botão "Anexar Arquivo"**
8. Clica "Anexar Arquivo" → janela Windows abre
9. Digita caminho completo do PDF → `Enter`
10. Aguarda upload (5 segundos)
11. **Rola novamente** até o final (layout muda após upload)
12. Clica "Salvar"

---

## 🔍 REGRAS DE OCR

### Dados Extraídos
- **Datas:** Formato DD/MM/YYYY
- **Números de documento:** Padrão `2025NE03848` ou `Nº 123456`
- **CNPJ:** 14 dígitos formatados `00.000.000/0000-00`
- **Nome de empresa:** Regex para LTDA, ME, EPP, S.A.
- **Número de Guia ISS:** Remove zeros à esquerda

### Processamento de PDF
- **PyMuPDF (fitz)** para renderizar primeira página em imagem
- DPI: 200
- OCR com Tesseract (idioma: português)
- Pré-processamento: escala de cinza, contraste aumentado

### Regra Especial: CAPA
1. Renderiza primeira página do PDF
2. Executa OCR para localizar texto: `"Tribunal de Contas do Estado de São Paulo"`
3. Obtém coordenada Y do texto
4. Corta imagem removendo tudo ACIMA dessa linha
5. Mantém o texto localizado e todo conteúdo abaixo

---

## ⚙️ CONFIGURAÇÕES IMPORTANTES

### Tempos de Espera
```python
PAUSE_BETWEEN_ACTIONS = 0.5      # Entre ações do pyautogui
WAIT_FOR_ELEMENT = 1.0           # Para elementos carregarem
MAX_UPLOAD_WAIT = 10             # Upload de arquivos
```

### Atalhos de Teclado do SEI
- **Salvar documento:** `Ctrl+Alt+S`
- **Fechar popup:** `Ctrl+W`
- **Maximizar janela:** `Alt+Espaço` → `X`

### Texto Fixo: Despacho de Aprovação
```
Aprova-se Nota de Empenho {numero_ne}, documento: {link_ne}

São Paulo, {data_ne}

WILLIAN DE OLIVEIRA SALAZAR
Coordenador de Departamento de Orçamento e Finanças – COF
```

---

## ⚠️ PROBLEMAS CONHECIDOS E SOLUÇÕES

### 1. Campos não preenchem texto
**Causa:** `pyautogui.write()` não suporta acentos  
**Solução:** Usar `pyperclip.copy()` + `Ctrl+V`

### 2. Layout muda após upload
**Causa:** Arquivo anexado expande UI  
**Solução:** Selecionar "Público" ANTES de anexar, rolar novamente após upload

### 3. Popup abre em posição diferente
**Causa:** Firefox pode variar posição  
**Solução:** Sempre maximizar popup com `Alt+Espaço` → `X`

### 4. Formulário não carrega a tempo
**Causa:** SEI pode estar lento  
**Solução:** Aumentar tempo de espera para 3 segundos após selecionar tipo

### 5. Campo sobrescreve parcialmente
**Causa:** Texto anterior não foi limpo  
**Solução:** Sempre usar `Ctrl+A` antes de `Ctrl+V`

---

## 🚀 STATUS ATUAL DE IMPLEMENTAÇÃO

### ✅ IMPLEMENTADO (funcionando)
- Documento 01: CAPA
- Documento 02: SOLICITAÇÃO DE ADIANTAMENTO
- Documento 03: NOTA DE EMPENHO
- Documento 04: DESPACHO (parcial - link manual)

### ⏳ PENDENTE DE IMPLEMENTAÇÃO
- Documento 05: ORDEM BANCÁRIA
- Documento 06: QUADRO COMPARATIVO
- Documento 07-13: CICLO DE NOTAS FISCAIS
- Documento 14: EXTRATO BANCÁRIO
- Documento 15: CONCILIAÇÃO CONTÁBIL
- Documento 16: DECLARAÇÃO DE ENCERRAMENTO

### 🔧 MELHORIAS NECESSÁRIAS
- Captura automática de link do documento na árvore (item 04)
- Detecção de ciclos de notas fiscais (quantidade variável)
- Tratamento robusto de erros de OCR
- Validação de dados extraídos antes de preencher
- Log detalhado de operações
- Modo de teste/debug sem inserir de fato

---

## 📝 CONSIDERAÇÕES PARA CONTINUAÇÃO

### Ao Implementar Novos Documentos
1. Seguir o padrão de função `processar_documento_XX_nome()`
2. Adicionar logs com `print()` para acompanhamento
3. Usar delays adequados entre ações
4. Sempre limpar campos com `Ctrl+A` antes de colar
5. Validar dados de OCR antes de preencher
6. Tratar casos onde OCR falha (usar placeholders)

### Ao Trabalhar com Coordenadas
1. Lembrar que são para resolução 1600x900
2. Usar scripts de calibração se mudar resolução
3. Preferir atalhos de teclado quando possível
4. Documentar coordenadas novas no código

### Ao Fazer OCR
1. Testar com documentos reais variados
2. Ajustar regex se padrões mudarem
3. Adicionar fallbacks quando OCR falhar
4. Considerar pre-processamento adicional se precisão for baixa

### Arquitetura do Código
- `config.py`: Configurações globais, caminhos, textos fixos
- `ocr_utils.py`: Funções de extração de texto/dados
- `pdf_utils.py`: Renderização e processamento de PDF
- `sei_automation.py`: Lógica principal, funções de cada documento

---

## 🎓 CONTEXTO DE USO

Este sistema é usado para prestação de contas de **adiantamentos** (recursos antecipados) ao Tribunal de Contas do Estado de São Paulo. O processo envolve:

1. Solicitação inicial de adiantamento
2. Emissão de nota de empenho e ordem bancária
3. Realização de compras/serviços (múltiplas notas fiscais)
4. Prestação de contas com todos os documentos comprobatórios
5. Conciliação contábil e encerramento

O sistema atual automatiza **apenas a inserção** dos documentos em processos já abertos. Não automatiza:
- Login no SEI
- Criação de processos
- Validação financeira
- Assinatura digital

---

## 🔗 PRÓXIMOS PASSOS SUGERIDOS

1. **Testar e ajustar** documentos 01-04 até funcionarem 100%
2. **Implementar documento 05** (Ordem Bancária - similar à NE)
3. **Implementar documento 06** (Quadro Comparativo - print de PDF)
4. **Implementar ciclo completo** de uma nota fiscal (docs 07-12)
5. **Adicionar lógica** para detectar múltiplas notas na pasta
6. **Implementar documentos finais** (13-16)
7. **Adicionar tratamento de erros** robusto
8. **Criar modo de teste** (dry-run sem inserir)
9. **Documentar edge cases** encontrados

---

## 📞 INFORMAÇÕES DE SUPORTE

- Projeto desenvolvido para resolução específica: **1600x900**
- Testado em: **Windows 10**, **Firefox**, **Python 3.10+**
- OCR configurado para: **Português (por)**
- Sistema alvo: **SEI-SP** (versão do Governo do Estado de São Paulo)

**LEMBRE-SE:** Este é um sistema de automação de interface (RPA). Qualquer mudança na UI do SEI pode quebrar o funcionamento. As coordenadas são sensíveis à resolução de tela.