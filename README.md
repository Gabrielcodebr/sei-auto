# sei-auto

Script de automação para inserção de documentos no SEI-SP (Sistema Eletrônico de Informações do Governo do Estado de São Paulo). Automatiza a prestação de contas de adiantamentos, inserindo os documentos comprobatórios num processo já aberto.

O script assume que o usuário fez login, abriu o processo correto e está com o Firefox na tela. A partir daí, controla mouse e teclado para inserir os documentos na sequência correta.

---

## Requisitos

### Sistema

- Windows 10 ou superior
- Resolução de tela: **1600x900** — as coordenadas de clique são fixas para essa resolução
- Firefox maximizado (não fullscreen), com zoom em 100%

### Programas

**Python 3.10+**
Baixe em [python.org](https://www.python.org/downloads/). Durante a instalação, marque "Add Python to PATH".

**Tesseract OCR**
Usado para extrair datas e números dos PDFs. Baixe o instalador Windows em [github.com/UB-Mannheim/tesseract](https://github.com/UB-Mannheim/tesseract/wiki).

Após instalar, edite `config.py` e ajuste `TESSERACT_PATH` para o caminho do executável na sua máquina:

```python
TESSERACT_PATH = r"C:\Users\SeuUsuario\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"
```

**Microsoft Word**
Necessário para converter o arquivo `.docx` da Declaração de Recebimento em imagem. O script abre o Word via automação COM (`win32com`), converte o arquivo para PDF e renderiza a primeira página. O Word precisa estar instalado na máquina.

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

## Organização dos documentos

Crie uma pasta `documentos/` na raiz do projeto e coloque os arquivos com prefixo numérico para definir a ordem de inserção. O número do prefixo não precisa ser consecutivo — o script ordena numericamente.

### Processo DMPP (padrão)

```
1-CAPA.pdf
2-SOLICITAÇÃO DE ADIANTAMENTO.pdf
3-NOTA DE EMPENHO.pdf
4-ORDEM BANCÁRIA.pdf

-- início dos ciclos (repete para cada nota fiscal) --

5-QUADRO COMPARATIVO.pdf
6-NOTA FISCAL 1234 NOME DA EMPRESA.pdf
7-COMPROVANTE DE PAGAMENTO NF 1234 NOME DA EMPRESA.pdf
8-DECLARAÇÃO DE RECEBIMENTO - NOME DA EMPRESA.docx
9-CONSULTA OPTANTE NOME DA EMPRESA.pdf
10-CONSULTA CNPJ NOME DA EMPRESA.pdf
11-ISS Empresa - NOME DA EMPRESA.pdf          (opcional)
12-ISS Comprovante - NOME DA EMPRESA.pdf      (opcional)

-- próximo ciclo começa com outro quadro comparativo --

25-BALANCETE.pdf
26-EXTRATO BANCÁRIO.pdf
27-CONCILIAÇÃO CONTÁBIL.pdf
28-DECLARAÇÃO DE ENCERRAMENTO.pdf
```

### Processo UFIEC

Adicione o Memorando/Justificativa como segundo arquivo:

```
1-CAPA.pdf
2-MEMORANDO.pdf
3-SOLICITAÇÃO DE ADIANTAMENTO.pdf
4-NOTA DE EMPENHO.pdf
5-ORDEM BANCÁRIA.pdf
-- ciclos e documentos finais na mesma sequência --
```

### Regras de nomenclatura

- O número antes do hífen define a ordem de inserção
- O arquivo com "balancete" no nome delimita o fim dos ciclos de nota fiscal
- Arquivos de ISS devem conter "ISS" no nome
- Arquivos de comprovante de ISS devem conter "ISS" e "comprovante" no nome
- Para notas fiscais, o número da NF e o nome da empresa são extraídos do próprio nome do arquivo — siga o padrão `NOTA FISCAL NNNN NOME DA EMPRESA.pdf`

---

## Execução

Com o Firefox aberto, processo no SEI visível na tela:

```
venv\Scripts\activate
python sei_automation.py
```

O script exibe dois menus:

1. **Tipo de processo**: DMPP ou UFIEC
2. **Ponto de início**:
   - Do início (todos os documentos)
   - Pular documentos fixos (começa do primeiro ciclo de NF)
   - Começar de um ciclo específico
   - Começar de um arquivo específico pelo número prefixo

Após a seleção, o script aguarda 10 segundos antes de iniciar. Use esse tempo para garantir que a tela está na posição correta.

Para cancelar durante a execução, mova o mouse para o **canto superior esquerdo** da tela.

---

## Resolução de problemas

| Problema | Causa provável | Solução |
|---|---|---|
| Cliques no lugar errado | Resolução diferente de 1600x900 ou Firefox não maximizado | Ajuste a resolução e maximize o Firefox |
| Tesseract não encontrado | Caminho incorreto em `config.py` | Corrija `TESSERACT_PATH` |
| Erro ao converter .docx | Microsoft Word não instalado ou inacessível | Verifique se o Word está instalado |
| Link da NE não capturado | Ícone da NE na árvore em posição diferente | Execute com UFIEC/DMPP correto; ajuste `COORD_ICONE_NE_ARVORE_*` se necessário |
| Script para sozinho | Erro no terminal | Leia a mensagem de erro; o pyautogui cancela se o mouse for para o canto superior esquerdo |

### Recalibrar coordenadas

Se a resolução ou o layout do SEI mudarem, use os scripts na pasta `calibracao/` para mapear as novas posições dos elementos na tela.
