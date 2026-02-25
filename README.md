# SEI Automation

Script de automação para inserção de documentos no SEI-SP (Sistema Eletrônico de Informações do Estado de São Paulo).

## Pré-requisitos

### 1. Python 3.10+
Baixe em: https://www.python.org/downloads/

Durante a instalação, marque a opção **"Add Python to PATH"**.

### 2. Tesseract OCR
Baixe o instalador em: https://github.com/UB-Mannheim/tesseract/wiki

Instale no caminho padrão: `C:\Program Files\Tesseract-OCR`

### 3. Microsoft Word
Necessário para converter os arquivos `.docx` da Declaração de Recebimento em imagem.

### 4. Firefox
Navegador utilizado para acessar o SEI. Deve estar aberto e maximizado na resolução **1600x900** antes de rodar o script.

---

## Instalação

Clone o repositório e entre na pasta:

```
git clone <url-do-repositorio>
cd sei-auto
```

Crie e ative o ambiente virtual:

```
python -m venv venv
venv\Scripts\activate
```

Instale as dependências:

```
pip install -r requirements.txt
```

---

## Configuração

Edite o arquivo `config.py` e ajuste:

- `DOCUMENTOS_DIR` — caminho da pasta com os documentos a inserir
- `TESSERACT_CMD` — caminho do executável do Tesseract (se necessário)
- `PDF_DPI` — resolução para renderização dos PDFs (padrão: 150)

---

## Organização dos documentos

Coloque todos os arquivos na pasta configurada em `DOCUMENTOS_DIR`, nomeados com prefixo numérico para definir a ordem:

```
1-CAPA.pdf
2-SOLICITAÇÃO DE ADIANTAMENTO.pdf
3-NOTA DE EMPENHO.pdf
4-ORDEM BANCÁRIA.pdf

--- início dos ciclos (um por nota fiscal) ---

5-QUADRO COMPARATIVO DE PREÇOS.pdf
6-NOTA FISCAL 1234 NOME DA EMPRESA.pdf
7-COMPROVANTE DE PAGAMENTO NF 1234 NOME DA EMPRESA.pdf
8-DECLARAÇÃO DE RECEBIMENTO - NOME DA EMPRESA.docx
9-CONSULTA OPTANTE NOME DA EMPRESA.pdf
10-CONSULTA CNPJ NOME DA EMPRESA.pdf
11-ISS Empresa - NOME DA EMPRESA.pdf          (opcional)
12-ISS Comprovante - NOME DA EMPRESA.pdf      (opcional)

--- fim do ciclo, próximo começa com outro quadro comparativo ---

XX-BALANCETE.pdf
XX-EXTRATO BANCÁRIO.pdf
XX-CONCILIAÇÃO CONTÁBIL.pdf
XX-DECLARAÇÃO DE ENCERRAMENTO.pdf
```

**Regras de nomenclatura:**
- O número do prefixo define a ordem de inserção
- Os números não precisam ser consecutivos (ex: 1, 4, 10 funciona)
- Arquivos de ISS devem conter `ISS` no nome
- Arquivos de comprovante de ISS devem conter `ISS` e `comprovante` no nome
- O balancete deve conter `balancete` no nome — ele delimita o fim dos ciclos

---

## Execução

Com o Firefox aberto no SEI, processo aberto na tela e resolução em **1600x900**:

```
venv\Scripts\activate
python sei_automation.py
```

O script aguarda 10 segundos antes de iniciar — use esse tempo para garantir que a tela está correta.

Para cancelar durante a execução, mova o mouse para o **canto superior esquerdo** da tela.

### Retomar de onde parou

Se o script parar no meio, você pode pular os documentos já inseridos:

```python
# Em sei_automation.py, na última linha antes do executar():
automacao = SEIAutomation(pular_primeiros=5)  # pula os 5 primeiros
```

---

## Resolução de problemas

| Problema | Solução |
|---|---|
| Cliques no lugar errado | Verifique se a resolução está em 1600x900 e o Firefox está maximizado |
| Tesseract não encontrado | Verifique o caminho em `config.py` |
| Erro ao converter .docx | Verifique se o Word está instalado |
| Script para sozinho | Verifique o log no terminal para identificar o erro |