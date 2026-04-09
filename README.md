# sei-auto

Script de automação para inserção de documentos no SEI-SP (Sistema Eletrônico de Informações do Governo do Estado de São Paulo). Automatiza a prestação de contas de adiantamentos, inserindo os documentos comprobatórios num processo já aberto.

O programa assume que o usuário fez login, abriu o processo correto e está com o Firefox na tela. A partir daí, controla mouse e teclado para inserir os documentos na sequência correta.

Oferece **dois modos de uso**:

- 🖼 **Modo fácil (GUI)** — interface gráfica PySide6 com abas, editor visual de todas as configurações, captura assistida de coordenadas, log ao vivo, hotkey F12 para parar e executável único `SeiAuto.exe`.
- 💻 **Modo desenvolvedor (CLI)** — execução clássica pelo terminal com menus interativos (`python sei_automation.py`).

---

## 📦 Instalação Rápida (Modo Fácil)

### 1. Pré-requisitos do sistema

- **Windows 10+**
- **Resolução de tela 1600x900** (as coordenadas-padrão assumem essa resolução — mas você pode recalibrar na própria GUI)
- **Firefox** maximizado com zoom 100%

### 2. Instalar o Tesseract OCR (obrigatório)

O bot usa OCR para ler datas e números dos PDFs. Baixe e instale:

👉 [github.com/UB-Mannheim/tesseract/wiki](https://github.com/UB-Mannheim/tesseract/wiki) (instalador Windows)

Durante a instalação, **marque o idioma Português** na lista de idiomas adicionais. Anote o caminho onde o Tesseract foi instalado (geralmente `C:\Users\SeuUsuario\AppData\Local\Programs\Tesseract-OCR\tesseract.exe`) — você vai informá-lo na primeira execução da GUI.

### 3. Instalar o Microsoft Word

Necessário para converter arquivos `.docx` (Declaração de Recebimento) em imagem. Qualquer versão do Word 2013+ serve.

### 4. Baixar o projeto

**Opção A — usar o executável pronto** (recomendado para leigos):

Baixe `SeiAuto.exe` do último release em [Releases](https://github.com/).
Coloque o `.exe` em uma pasta junto com uma subpasta chamada `documentos/` (onde ficarão seus PDFs).

**Opção B — clonar o repositório e gerar você mesmo**:

```
git clone <url-do-repositorio>
cd sei-auto
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
build_exe.bat
```

O script `build_exe.bat` gera `SeiAuto.exe` na raiz do projeto.

### 5. Abrir

Dê **duplo-clique em `SeiAuto.exe`**. Na primeira execução, a GUI vai avisar se o Tesseract ou a pasta de documentos não forem encontrados. Vá em **Configurações → Caminhos & OCR** e aponte para o executável do Tesseract e para sua pasta de documentos.

---

## 🎛 Usando a Interface Gráfica

A GUI tem 4 abas:

### ▶ Executar

Substitui os menus antigos do terminal:

1. Escolha o **tipo de processo**: DMPP (padrão) ou UFIEC (com memorando)
2. Escolha o **modo de execução**:
   - Do início (todos os documentos)
   - Pular documentos fixos (começa do ciclo 1)
   - Começar de um ciclo específico (escolha o número)
   - Começar de um arquivo específico (escolha o prefixo)
3. Clique em **▶ INICIAR AUTOMAÇÃO**
4. Você tem **10 segundos** para posicionar o Firefox com o SEI visível
5. A automação roda com o log ao vivo aparecendo na parte inferior

#### Como parar a automação

Durante a execução, três formas de parar:

- **Tecla F12** (funciona mesmo sem a janela da GUI em foco) — **recomendado**
- **Botão STOP** na mini-janela flutuante vermelha que aparece no canto superior direito
- **Mouse no canto superior esquerdo** da tela (failsafe nativo do pyautogui)

### 📄 Documentos

Mostra a lista de arquivos da sua pasta `documentos/` com:
- Número do prefixo
- Nome do arquivo
- Tipo detectado automaticamente
- Tamanho

Use esta aba para conferir se todos os documentos estão na pasta **antes** de iniciar a automação.

### ⚙ Configurações

Editor visual de **tudo** que pode ser customizado. Sub-abas:

- **📍 Coordenadas** — posição de cada botão/campo do SEI na tela. Para cada coordenada você tem:
  - 🎯 **Capturar**: clique, posicione o mouse sobre o alvo, aguarde 3 segundos → captura a posição automaticamente
  - 👁 **Ver**: move o cursor para a coordenada atual (para conferência)
- **⏱ Tempos** — delays entre ações. Aumente se o SEI estiver lento.
- **📂 Caminhos & OCR** — caminho do Tesseract, pasta de documentos, idioma, DPI etc.
- **📄 Tipos de Documento** — termos de busca e campos preenchidos para cada tipo (tabela editável)
- **📝 Textos & Templates** — template do despacho de aprovação de NE e lista de assinaturas da planilha de preços

Tudo que você alterar aqui é salvo em `user_config.json` (na pasta do projeto). Este arquivo **sobrescreve** os valores padrão do `config.py`, então nunca mexa no código Python diretamente.

Botões do rodapé:
- 💾 **Salvar** — grava em `user_config.json`
- ↺ **Restaurar padrões** — apaga `user_config.json` (volta aos valores originais)
- 📁 **Abrir JSON** — abre o arquivo no editor padrão

### ℹ Sobre

Informações do projeto e atalhos.

---

## 📁 Organização dos documentos

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

## 💻 Modo Desenvolvedor (CLI)

Se você prefere o terminal ou precisa debugar a lógica de automação isolada da GUI:

### Instalação

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### Configuração

Edite `config.py` manualmente (ou deixe a GUI gerar o `user_config.json` — ambos funcionam em paralelo).

### Execução

```
venv\Scripts\activate
python sei_automation.py
```

O script exibe dois menus no terminal:

1. **Tipo de processo**: DMPP ou UFIEC
2. **Ponto de início**:
   - Do início (todos os documentos)
   - Pular documentos fixos (começa do primeiro ciclo de NF)
   - Começar de um ciclo específico
   - Começar de um arquivo específico pelo número prefixo

Após a seleção, o script aguarda 10 segundos antes de iniciar. Para cancelar durante a execução, mova o mouse para o **canto superior esquerdo** da tela (não tem F12 no modo CLI).

---

## 🏗 Construindo o executável (.exe)

Com o venv ativado e dependências instaladas:

```
build_exe.bat
```

Ou diretamente:

```
pyinstaller SeiAuto.spec --clean --noconfirm
copy dist\SeiAuto.exe SeiAuto.exe
```

O executável fica na raiz do projeto como `SeiAuto.exe` (~150-250 MB, é normal — inclui PySide6 e todas as dependências). Você pode distribuí-lo junto com a pasta `documentos/` e um README pequeno para usuários leigos.

**Importante**: o Tesseract OCR e o Microsoft Word **não** são empacotados no `.exe`. O usuário final precisa instalá-los separadamente.

---

## ❓ Resolução de problemas

| Problema | Causa provável | Solução |
|---|---|---|
| Cliques no lugar errado | Resolução diferente de 1600x900 ou Firefox não maximizado | Ajuste a resolução e maximize o Firefox, ou recalibre na aba Configurações → Coordenadas |
| Tesseract não encontrado | Caminho incorreto | Ajuste em Configurações → Caminhos & OCR |
| Pasta documentos não encontrada | Caminho errado | Ajuste em Configurações → Caminhos & OCR |
| Erro ao converter .docx | Microsoft Word não instalado | Verifique se o Word está instalado |
| Link da NE não capturado | Ícone da NE na árvore em posição diferente | Recapture `COORD_ICONE_NE_ARVORE_*` na aba Coordenadas |
| F12 não para a execução | Biblioteca `keyboard` precisa de permissão elevada em alguns ambientes | Use o botão STOP da mini-janela flutuante, ou mouse no canto superior esquerdo |
| Windows Defender bloqueia o .exe | Falso positivo comum do PyInstaller | Clique em "Mais informações → Executar assim mesmo". Se preferir, rode em modo desenvolvedor com `run_gui.bat` |
| GUI não abre após instalar | Dependências não instaladas | Rode `pip install -r requirements.txt` no venv ativado |
| Alguma coisa quebrou após editar configurações | Configuração inválida salva no JSON | Abra a aba Configurações e clique em "↺ Restaurar padrões" |

### Recalibrar coordenadas

Se a resolução ou o layout do SEI mudarem, **use a aba Configurações → Coordenadas** na GUI — o botão 🎯 Capturar substitui os antigos scripts em `calibracao/`. Os scripts legados continuam na pasta para referência.
