# Automação de Inserção de Documentos no SEI (SP)

Este projeto automatiza a inserção de documentos em processos já abertos no Sistema Eletrônico de Informações (SEI) do Governo de São Paulo.

## ⚠️ IMPORTANTE

- Este script **NÃO** automatiza login nem criação de processos
- O processo deve estar **aberto e visível** na tela antes de executar
- Você deve **acompanhar visualmente** toda a automação
- Os documentos devem estar **numerados na ordem correta** na pasta

---

## 📋 PRÉ-REQUISITOS

### Programas necessários

1. **Python 3.10 ou superior**
   - Download: https://www.python.org/downloads/
   - ⚠️ Durante instalação: marcar **"Add Python to PATH"**

2. **Tesseract OCR**
   - Download: https://github.com/UB-Mannheim/tesseract/wiki
   - Instalar e anotar o caminho (ex: `C:\Program Files\Tesseract-OCR`)

3. **Poppler for Windows**
   - Download: https://github.com/oschwartz10612/poppler-windows/releases/
   - Baixar o arquivo `Release-XX.XX.X-0.zip`
   - Extrair para uma pasta (ex: `C:\poppler`)
   - Anotar o caminho da pasta `bin` (ex: `C:\poppler\Library\bin`)

4. **Visual Studio Code** (recomendado)
   - Download: https://code.visualstudio.com/

5. **Git Bash** (opcional, mas recomendado)
   - Download: https://git-scm.com/downloads

---

## 🛠️ INSTALAÇÃO

### 1. Clone ou baixe este projeto

```bash
# Se usar Git:
git clone <url-do-repositorio>
cd sei-auto

# OU crie manualmente:
mkdir sei-auto
cd sei-auto
```

### 2. Crie um ambiente virtual

```bash
python -m venv venv
```

### 3. Ative o ambiente virtual

**No Git Bash / Linux / Mac:**
```bash
source venv/Scripts/activate
```

**No CMD do Windows:**
```cmd
venv\Scripts\activate
```

**No PowerShell:**
```powershell
.\venv\Scripts\Activate.ps1
```

Você verá `(venv)` no início da linha do terminal.

### 4. Instale as dependências Python

```bash
pip install --upgrade pip
pip install pyautogui pynput opencv-python-headless pillow pytesseract pdf2image pyperclip python-docx
```

### 5. Configure os caminhos no arquivo `config.py`

Edite o arquivo `config.py` e ajuste os caminhos do Tesseract e Poppler:

```python
# Caminho do executável do Tesseract
TESSERACT_PATH = r"C:\Users\SeuUsuario\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"

# Caminho da pasta bin do Poppler
POPPLER_PATH = r"C:\poppler\Library\bin"
```

---

## 📁 ESTRUTURA DE PASTAS

```
sei-auto/
├── venv/                    # Ambiente virtual (criado automaticamente)
├── documentos/              # ⚠️ COLOQUE SEUS PDFs AQUI (numerados em ordem)
│   ├── 01_capa.pdf
│   ├── 02_solicitacao.pdf
│   ├── 03_nota_empenho.pdf
│   └── ...
├── config.py                # Configurações do projeto
├── ocr_utils.py             # Funções de OCR
├── pdf_utils.py             # Funções de manipulação de PDF
├── sei_automation.py        # Script principal
└── README.md                # Este arquivo
```

---

## 📝 PREPARAÇÃO DOS DOCUMENTOS

1. Crie a pasta `documentos/` dentro do projeto
2. Coloque **TODOS** os documentos nesta pasta
3. **Numere os arquivos na ordem exata** de inserção no SEI:
   - `01_capa.pdf`
   - `02_solicitacao_adiantamento.pdf`
   - `03_nota_empenho.pdf`
   - `04_ordem_bancaria.pdf`
   - `05_quadro_comparativo.pdf`
   - `06_nota_fiscal_empresa1.pdf`
   - `07_comprovante_nf_empresa1.pdf`
   - `08_declaracao_recebimento_empresa1.docx` ⚠️ Único arquivo .docx
   - `09_consulta_optante_empresa1.pdf`
   - `10_cnpj_empresa1.pdf`
   - (continua conforme seu processo...)

---

## ▶️ COMO USAR

### 1. Prepare o ambiente

- Abra o processo no SEI
- Deixe a janela do SEI **visível e maximizada**
- **NÃO minimize nem mude de janela** durante a execução

### 2. Execute o script

```bash
# Com o ambiente virtual ativado:
python sei_automation.py
```

### 3. Acompanhe a execução

- O script irá mover o mouse e digitar automaticamente
- **Acompanhe visualmente** para garantir que tudo está correto
- Em caso de erro, pressione `Ctrl+C` para interromper

---

## 🎯 ORDEM DOS DOCUMENTOS NO SEI

O script segue esta ordem exata:

1. **Capa** (interno, print de PDF com corte especial)
2. **Solicitação de Adiantamento** (interno, print de PDF)
3. **Nota de Empenho** (externo, upload PDF)
4. **Despacho de Aprovação da NE** (interno, texto com link)
5. **Ordem Bancária** (externo, upload PDF)
6. **Quadro Comparativo de Preços** (interno, print de PDF)
7. **Nota Fiscal** (externo, upload PDF) - *CICLO INICIA*
8. **Comprovante da NF** (externo, upload PDF)
9. **Declaração de Recebimento** (interno, texto de .docx)
10. **Consulta de Optante** (externo, upload PDF)
11. **CNPJ** (externo, upload PDF)
12. **Guia de ISS** (externo, upload PDF) - *se houver*
13. **Comprovante ISS** (externo, upload PDF) - *se houver*
    
    *O ciclo 7-13 repete para cada nota fiscal*

14. **Balancete** (interno, print de PDF)
15. **Extrato Bancário** (externo, upload PDF)
16. **Conciliação Contábil** (interno, print de PDF)
17. **Declaração de Encerramento** (interno, print de PDF)

---

## 🔧 TROUBLESHOOTING

### Erro: "Tesseract not found"
- Verifique se o Tesseract está instalado
- Confirme o caminho em `config.py`
- Teste no terminal: `tesseract --version`

### Erro: "Unable to get page count"
- Verifique se o Poppler está instalado
- Confirme o caminho em `config.py`

### Script clica no lugar errado
- Verifique se a janela do SEI está maximizada
- Ajuste as coordenadas no código (se necessário)
- Verifique a resolução da sua tela

### OCR não reconhece texto
- Verifique a qualidade do PDF
- O documento pode estar em formato de imagem ruim
- Ajuste as configurações de pré-processamento no código

---

## 📞 SUPORTE

Em caso de dúvidas ou problemas:
1. Verifique se todos os pré-requisitos estão instalados
2. Confirme que os caminhos em `config.py` estão corretos
3. Teste cada documento individualmente
4. Revise os logs de erro no terminal

---

## ⚖️ LICENÇA E RESPONSABILIDADE

Este script é fornecido "como está", sem garantias. O usuário é responsável por:
- Verificar a correção dos dados inseridos
- Acompanhar visualmente toda a automação
- Garantir conformidade com políticas internas

**Uso por sua conta e risco.**