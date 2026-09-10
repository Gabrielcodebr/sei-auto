# sei-auto

Script de automação para inserção de documentos no SEI-SP (Sistema Eletrônico de Informações do Governo do Estado de São Paulo). Automatiza a prestação de contas de adiantamentos, inserindo os documentos comprobatórios num processo já aberto.

O programa assume que o usuário fez login, abriu o processo correto e está com o Firefox na tela. A partir daí, controla mouse e teclado para inserir os documentos na sequência correta.

Oferece dois modos de uso:

- 🖼 **Modo fácil (GUI)** — interface gráfica PySide6 com abas, editor visual de todas as configurações, captura assistida de coordenadas, log ao vivo, hotkey F12 para parar e executável único `SeiAuto.exe`.
- 💻 **Modo desenvolvedor (CLI)** — execução clássica pelo terminal com menus interativos (`python sei_automation.py`).

## 📦 Instalação Rápida (Modo Fácil)

### 1. Pré-requisitos do sistema

- Windows 10+
- Resolução de tela 1600x900 (as coordenadas-padrão assumem essa resolução — mas você pode recalibrar na própria GUI)
- Firefox maximizado com zoom 100%

### 2. Instalar o Tesseract OCR (obrigatório)

O bot usa OCR para ler datas e números dos PDFs. O Tesseract **NÃO** vem embutido no `.exe` — você precisa instalá-lo separadamente.

Baixe e instale pelo instalador oficial do UB-Mannheim:

👉 [github.com/UB-Mannheim/tesseract/wiki](https://github.com/UB-Mannheim/tesseract/wiki)

Durante a instalação, marque o idioma **Português** na lista de idiomas adicionais. Se você já instalou o Tesseract sem português, não precisa reinstalar tudo: baixe só o arquivo de idioma e coloque em `tessdata\`:

- Baixe [`por.traineddata`](https://github.com/tesseract-ocr/tessdata/raw/main/por.traineddata)
- Cole em `C:\Users\SeuUsuario\AppData\Local\Programs\Tesseract-OCR\tessdata\`

### 3. Instalar o Microsoft Word

Necessário para converter arquivos `.docx` (Declaração de Recebimento) em imagem. Qualquer versão do Word 2013+ serve.

### 4. Baixar o projeto

**Opção A — usar o executável pronto (recomendado para leigos):**

1. Baixe `SeiAuto.exe` do último release em [**Releases**](https://github.com/Gabrielcodebr/sei-auto/releases/latest).
2. Coloque o `.exe` em uma pasta comum — Área de Trabalho, Documentos ou Downloads. Evite `C:\Program Files\` (o Windows bloqueia escrita lá).
3. Dê duplo-clique. O bot cria automaticamente a pasta `documentos\` ao lado do executável, na primeira vez que abrir.

**Opção B — clonar o repositório e gerar você mesmo:**

```bash
git clone https://github.com/Gabrielcodebr/sei-auto.git
cd sei-auto
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
build_exe.bat
```

O `build_exe.bat` gera `SeiAuto.exe` na raiz do projeto.

### 5. Abrir

Dê duplo-clique em `SeiAuto.exe`. Na primeira execução, a GUI avisa se o Tesseract não foi encontrado. Vá em **Configurações → 📂 Caminhos & OCR** e aponte para o `tesseract.exe` instalado.

> ⚠️ **Antivírus bloqueando o .exe?** É um falso positivo clássico do PyInstaller — acontece com qualquer programa empacotado com essa ferramenta. Clique em "Mais informações → Executar assim mesmo". Se preferir, rode pelo modo desenvolvedor (`run_gui.bat`) enquanto isso.

## 🎛 Usando a Interface Gráfica

A GUI tem 4 abas:

### ▶ Executar

Substitui os menus antigos do terminal:

1. Escolha o tipo de processo: **DMPP** (padrão) ou **UFIEC** (com memorando)
2. Escolha o modo de execução:
   - Do início (todos os documentos)
   - Pular documentos fixos (começa do ciclo 1)
   - Começar de um ciclo específico (escolha o número)
   - Começar de um arquivo específico (escolha o prefixo)
3. Clique em **▶ INICIAR AUTOMAÇÃO**
4. Você tem 10 segundos para posicionar o Firefox com o SEI visível
5. A automação roda com o log ao vivo aparecendo na parte inferior

**Como parar a automação**

Durante a execução, três formas de parar:

- Tecla **F12** (funciona mesmo sem a janela da GUI em foco) — recomendado
- Botão **STOP** na mini-janela flutuante vermelha que aparece no canto superior direito
- Mouse no canto superior esquerdo da tela (failsafe nativo do pyautogui)

### 📄 Documentos

Mostra a lista de arquivos da pasta `documentos\` com número do prefixo, nome, tipo detectado e tamanho. Use esta aba para conferir se tudo está no lugar antes de executar.

Botões disponíveis:

- **➕ Adicionar arquivos…** — copia PDFs/DOCX escolhidos para a pasta de documentos, sem precisar abrir o Explorer. Se já existir arquivo com o mesmo nome, você escolhe entre sobrescrever ou pular.
- **🗑️ Remover selecionados** — apaga da pasta os arquivos selecionados na tabela (com confirmação).
- **📁 Abrir pasta** — abre a pasta no Explorer.
- **🔄 Recarregar** — relê a pasta.

A tabela também destaca em amarelo arquivos com numeração em conflito (dois arquivos com o mesmo número de prefixo) — um diálogo aparece para você decidir a ordem antes de executar. Arquivos em cinza são aqueles que nenhum tipo ativo do pipeline reconhece e que serão ignorados na execução.

### ⚙ Configurações

Editor visual de tudo que pode ser customizado. Sub-abas:

- **📍 Coordenadas** — posição de cada botão/campo do SEI na tela. Para cada coordenada:
  - 🎯 **Capturar**: clique, posicione o mouse sobre o alvo, aguarde 3 segundos → captura a posição automaticamente
  - 👁 **Ver**: move o cursor para a coordenada atual (para conferência)
- **⏱ Tempos** — delays entre ações. Aumente se o SEI estiver lento.
- **📂 Caminhos & OCR** — caminho do Tesseract, pasta de documentos, idioma, DPI, confiança mínima.
- **🧩 Pipeline de Documentos** — cada tipo de documento é um "passo" com categoria (fixo inicial / ciclo / fixo final), ordem de execução, palavras-chave de detecção pelo nome do arquivo, e se está ativo. Arraste para reordenar dentro de cada seção, desmarque "Ativo" para pular um tipo sem apagar a configuração. Duplo-clique para editar. Passos com 🔒 têm lógica própria de extração de dados (não podem ser removidos, só desativados); passos novos criados por você usam processadores genéricos.
- **📝 Textos & Templates** — assinaturas da Planilha de Pesquisa de Preço (o bot corta as páginas do Quadro Comparativo após encontrá-las). O template do despacho de aprovação de NE e de outros textos gerados agora se edita dentro do próprio passo, na aba 🧩 Pipeline de Documentos.

Tudo que você alterar aqui é salvo em `user_config.json` e `pipeline_config.json` (na pasta do projeto). Esses arquivos sobrescrevem os valores padrão do código, então nunca é preciso mexer em Python pra ajustar comportamento.

Botões do rodapé:

- **💾 Salvar** — grava `user_config.json` e `pipeline_config.json`
- **↺ Restaurar padrões** — apaga os dois arquivos de configuração, voltando a todos os valores originais
- **📁 Abrir pasta de configs** — abre no Explorer a pasta onde ficam os arquivos

### ℹ Sobre

Informações do projeto e atalhos.

## 📁 Organização dos documentos

Coloque os arquivos na pasta `documentos\` (a GUI cria e gerencia essa pasta pra você) com prefixo numérico definindo a ordem. O número do prefixo não precisa ser consecutivo — o bot ordena numericamente.

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

- O número antes do hífen define a ordem de inserção.
- O arquivo com "quadro", "planilha" ou "comparativ" no nome marca o início de um novo ciclo de Nota Fiscal.
- O arquivo com "balancete" no nome geralmente é o primeiro dos documentos finais, mas a separação entre ciclos e finais é pelo próprio pipeline (categoria de cada tipo), não pelo nome do arquivo.
- Arquivos de ISS devem conter "ISS" no nome.
- Arquivos de comprovante de ISS devem conter "ISS" e "comprovante" no nome.
- Para notas fiscais, o número da NF e o nome da empresa são extraídos do próprio nome do arquivo — siga o padrão `NOTA FISCAL NNNN NOME DA EMPRESA.pdf`.

### Arquivos combinados (2 documentos no mesmo PDF)

O bot reconhece dois casos em que um único PDF contém dois documentos do processo, e insere os dois no SEI sem precisar separar o arquivo:

- **Nota Fiscal + Comprovante de Pagamento** no mesmo PDF: o arquivo é inserido duas vezes — uma como Nota Fiscal, outra como Comprovante. O nome do arquivo deve conter tanto "nota fiscal" quanto "comprovante".
- **Guia ISS + Comprovante de ISS** no mesmo PDF: idem. O nome deve conter "ISS" e "comprovante".

Nesses casos, é só um arquivo na pasta — o bot cuida da duplicação internamente.

## 💻 Modo Desenvolvedor (CLI)

Se você prefere o terminal ou precisa debugar a lógica de automação isolada da GUI:

### Instalação

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### Configuração

Edite `config.py` manualmente (ou deixe a GUI gerar o `user_config.json` — ambos funcionam em paralelo).

### Execução

```bash
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
   - Iniciar do Despacho de Aprovação da NE (só insere esse documento)

Após a seleção, o script aguarda 10 segundos antes de iniciar. Para cancelar durante a execução, mova o mouse para o canto superior esquerdo da tela (não tem F12 no modo CLI).

## 🏗 Construindo o executável (.exe)

Com o venv ativado e dependências instaladas:

```bash
build_exe.bat
```

O script usa o `SeiAuto.spec` versionado no repositório, gera o executável e copia `SeiAuto.exe` para a raiz do projeto. É o arquivo que você anexa nos Releases do GitHub.

Tamanho esperado: 150–250 MB (é normal — inclui PySide6, PyMuPDF, Pillow e demais dependências). O Tesseract OCR e o Microsoft Word não são empacotados — o usuário final precisa instalá-los separadamente (ver Pré-requisitos).

## 🚀 Lançando um Release no GitHub

O `.exe` não vai pelo `git push` (é grande, muda a cada build, e não faz sentido versionar binário). Ele é anexado a uma Release:

1. Rode `build_exe.bat` e confirme que `SeiAuto.exe` foi gerado na raiz.
2. Faça commit e push do código normalmente:

   ```bash
   git add .
   git commit -m "Descrição das mudanças"
   git push
   ```

3. No GitHub, acesse a página de Releases do repositório:
   👉 https://github.com/Gabrielcodebr/sei-auto/releases
4. Clique em **"Draft a new release"**.
5. Em **Choose a tag**, digite `v1.0.0` (ou a versão que fizer sentido) e confirme criar a tag ao publicar.
6. **Release title**: algo como `SeiAuto v1.0.0`.
7. **Description**: breve — o que essa versão traz de novo, requisitos.
8. Em **Attach binaries**, arraste o `SeiAuto.exe` para a área de upload.
9. Marque **"Set as the latest release"** e clique em **Publish release**.

O link permanente para a última versão é sempre:

```
https://github.com/Gabrielcodebr/sei-auto/releases/latest
```

Use esse link em qualquer lugar (README, e-mail, etc.) — ele redireciona automaticamente para a release mais recente, sem precisar editar nada quando lançar `v1.1.0` no futuro.

## ❓ Resolução de problemas

| Problema | Causa provável | Solução |
|---|---|---|
| Cliques no lugar errado | Resolução diferente de 1600x900 ou Firefox não maximizado | Ajuste a resolução e maximize o Firefox, ou recalibre na aba Configurações → Coordenadas |
| Tesseract não encontrado | Caminho incorreto | Ajuste em Configurações → 📂 Caminhos & OCR |
| OCR lê números/datas errados | Faltando `por.traineddata` | Baixe de [tessdata](https://github.com/tesseract-ocr/tessdata/raw/main/por.traineddata) e coloque em `tessdata\` |
| Pasta `documentos` não encontrada | Caminho errado | Ajuste em Configurações → 📂 Caminhos & OCR, ou use "➕ Adicionar arquivos…" na aba Documentos |
| Erro ao converter `.docx` | Microsoft Word não instalado | Verifique se o Word está instalado |
| Link da NE não capturado | Ícone da NE na árvore em posição diferente | Edite o passo `despacho_aprovacao_ne` na aba Pipeline de Documentos e recalibre a coordenada |
| F12 não para a execução | Biblioteca `keyboard` precisa de permissão elevada em alguns ambientes | Use o botão STOP da mini-janela flutuante, ou mouse no canto superior esquerdo |
| Windows Defender bloqueia o .exe | Falso positivo comum do PyInstaller | Clique em "Mais informações → Executar assim mesmo". Se preferir, rode em modo desenvolvedor com `run_gui.bat` |
| GUI não abre após instalar | Dependências não instaladas | Rode `pip install -r requirements.txt` no venv ativado |
| Alguma coisa quebrou após editar configurações | Configuração inválida salva no JSON | Abra a aba Configurações e clique em "↺ Restaurar padrões" |
| O .exe não cria a pasta `documentos\` | O exe está em uma pasta sem permissão de escrita (ex: `C:\Program Files\`) | Mova o `SeiAuto.exe` para Área de Trabalho, Documentos ou Downloads |

### Recalibrar coordenadas

Se a resolução ou o layout do SEI mudarem, use a aba **Configurações → 📍 Coordenadas** na GUI — o botão **🎯 Capturar** substitui os antigos scripts em `calibracao/`. Os scripts legados continuam na pasta para referência.