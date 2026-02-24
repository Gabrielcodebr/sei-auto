"""
CALIBRAÇÃO COMPLETA - Roda tudo de uma vez
Ao final gera o bloco de coordenadas pronto para colar no sei_automation.py
"""
import pyautogui
import time
import os

print("="*70)
print("🎯 CALIBRAÇÃO COMPLETA - SEI AUTOMATION")
print("="*70)
print()
print("Este script calibra TODAS as coordenadas de uma vez.")
print("Ao final, gera o código pronto para colar no sei_automation.py")
print()
print("Você passará por 4 etapas:")
print("  1️⃣  Tela principal (botão Incluir Documento + barra de pesquisa)")
print("  2️⃣  Formulário interno (Descrição, Nome na Árvore, Nível, Salvar)")
print("  3️⃣  Formulário externo (todos os campos)")
print("  4️⃣  Popup do editor (área de edição maximizada)")
print()
input("Pressione ENTER para começar...")

coordenadas = {}


def capturar_posicao(nome_elemento, instrucao_extra=None):
    if instrucao_extra:
        print(f"\n  ℹ️  {instrucao_extra}")
    print(f"\n📍 Posicione o mouse sobre: {nome_elemento}")
    print("   Aguardando 5 segundos...")
    for i in range(5, 0, -1):
        print(f"   {i}...", end='\r')
        time.sleep(1)
    pos = pyautogui.position()
    print(f"   ✅  X={pos.x}, Y={pos.y}     ")
    return pos


def secao(titulo):
    print()
    print("─"*70)
    print(f"  {titulo}")
    print("─"*70)


# ─────────────────────────────────────────────────────────────
# ETAPA 1 — TELA PRINCIPAL
# ─────────────────────────────────────────────────────────────
secao("1️⃣  TELA PRINCIPAL")
print()
print("Certifique-se de que o SEI está aberto com um processo visível.")
input("Pressione ENTER quando estiver pronto...")

coordenadas['btn_incluir_doc'] = capturar_posicao(
    "BOTÃO 'Incluir Documento' (ícone de página com tracejado)",
    "Fica no topo da lista de documentos, lado esquerdo"
)

input("\nPressione ENTER para próximo...")
coordenadas['barra_pesquisa'] = capturar_posicao(
    "BARRA DE PESQUISA de tipos de documento",
    "A caixa de busca que aparece depois de clicar em Incluir Documento"
)


# ─────────────────────────────────────────────────────────────
# ETAPA 2 — FORMULÁRIO INTERNO
# ─────────────────────────────────────────────────────────────
secao("2️⃣  FORMULÁRIO DOCUMENTO INTERNO")
print()
print("Agora abra um formulário interno:")
print("  1. Clique em 'Incluir Documento'")
print("  2. Selecione um tipo interno (ex: 'Informação')")
print("  3. Aguarde o formulário abrir")
input("Pressione ENTER quando o formulário estiver aberto...")

coordenadas['campo_descricao_interno'] = capturar_posicao(
    "CAMPO 'Descrição' (caixa de texto livre)"
)

input("\nPressione ENTER para próximo...")
coordenadas['campo_nome_arvore_interno'] = capturar_posicao(
    "CAMPO 'Nome na Árvore' (caixa de texto)"
)

print("\nRole a página para baixo até ver a seção 'Nível de Acesso'")
input("Pressione ENTER quando estiver vendo o radio 'Público'...")
coordenadas['radio_publico'] = capturar_posicao(
    "RADIO BUTTON 'Público'"
)

print("\nRole até o fim — botão 'Salvar'")
input("Pressione ENTER quando estiver vendo o botão 'Salvar'...")
coordenadas['btn_salvar_form'] = capturar_posicao(
    "BOTÃO 'Salvar' (do formulário)"
)


# ─────────────────────────────────────────────────────────────
# ETAPA 3 — FORMULÁRIO EXTERNO
# ─────────────────────────────────────────────────────────────
secao("3️⃣  FORMULÁRIO DOCUMENTO EXTERNO")
print()
print("Agora abra o formulário externo:")
print("  1. Clique em 'Incluir Documento'")
print("  2. Selecione 'Externo'")
print("  3. Aguarde o formulário 'Registrar Documento Externo' abrir")
input("Pressione ENTER quando o formulário estiver aberto...")

coordenadas['dropdown_tipo_externo'] = capturar_posicao(
    "DROPDOWN 'Tipo do Documento' (caixa de seleção)"
)

input("\nPressione ENTER para próximo...")
coordenadas['campo_data'] = capturar_posicao(
    "CAMPO 'Data do Documento'"
)

input("\nPressione ENTER para próximo...")
coordenadas['campo_numero'] = capturar_posicao(
    "CAMPO 'Número'"
)

input("\nPressione ENTER para próximo...")
coordenadas['campo_nome_arvore'] = capturar_posicao(
    "CAMPO 'Nome na Árvore' (externo)"
)

print("\nRole a página até ver os radio buttons de FORMATO")
input("Pressione ENTER quando estiver vendo os radio buttons...")
coordenadas['radio_nato_digital'] = capturar_posicao(
    "RADIO BUTTON 'Nato-digital'"
)

input("\nPressione ENTER para próximo...")
coordenadas['radio_digitalizado'] = capturar_posicao(
    "RADIO BUTTON 'Digitalizado nesta Unidade'"
)

print("\nClique em 'Digitalizado' para aparecer o dropdown de conferência")
input("Pressione ENTER quando o DROPDOWN 'Tipo de Conferência' estiver visível...")
coordenadas['dropdown_tipo_conferencia'] = capturar_posicao(
    "DROPDOWN 'Tipo de Conferência'"
)

print("\nRole mais até ver o botão 'Anexar Arquivo...'")
input("Pressione ENTER quando estiver vendo o botão...")
coordenadas['btn_anexar_arquivo'] = capturar_posicao(
    "BOTÃO 'Anexar Arquivo...'"
)


# ─────────────────────────────────────────────────────────────
# ETAPA 4 — POPUP DO EDITOR
# ─────────────────────────────────────────────────────────────
secao("4️⃣  POPUP DO EDITOR")
print()
print("Agora abra o editor de texto do SEI:")
print("  1. Finalize o formulário de qualquer doc interno clicando em Salvar")
print("  2. Quando o popup abrir, pressione Alt+Espaço → X para maximizar")
input("Pressione ENTER quando o popup estiver MAXIMIZADO...")

coordenadas['area_edicao_max'] = capturar_posicao(
    "CENTRO DA ÁREA DE EDIÇÃO (popup maximizado)"
)


# ─────────────────────────────────────────────────────────────
# RESUMO E GERAÇÃO DE CÓDIGO
# ─────────────────────────────────────────────────────────────
print("\n" + "="*70)
print("✅ CALIBRAÇÃO COMPLETA!")
print("="*70)
print()
print("Coordenadas capturadas:")
print("-"*70)
for nome, pos in coordenadas.items():
    print(f"  {nome:38} → X={pos.x:4}, Y={pos.y:4}")

# Salva arquivo de texto com todas as coordenadas
arquivo_saida = 'coordenadas_completas.txt'
print(f"\n💾 Salvando em '{arquivo_saida}'...")
with open(arquivo_saida, 'w', encoding='utf-8') as f:
    f.write("# Coordenadas completas - SEI Automation\n")
    f.write(f"# Resolução: {pyautogui.size()}\n")
    f.write(f"# Data: {time.strftime('%d/%m/%Y %H:%M:%S')}\n\n")
    for nome, pos in coordenadas.items():
        f.write(f"{nome} = ({pos.x}, {pos.y})\n")
print("✅ Salvo!")

# ─── Bloco pronto para colar no sei_automation.py ───
bloco = f"""
    # =========================================================
    # COORDENADAS - TELA PRINCIPAL
    # =========================================================
    COORD_BTN_INCLUIR_DOC   = ({coordenadas['btn_incluir_doc'].x}, {coordenadas['btn_incluir_doc'].y})
    COORD_BARRA_PESQUISA    = ({coordenadas['barra_pesquisa'].x}, {coordenadas['barra_pesquisa'].y})

    # =========================================================
    # COORDENADAS - FORMULÁRIO DOCUMENTO INTERNO
    # =========================================================
    COORD_CAMPO_DESCRICAO_INTERNO   = ({coordenadas['campo_descricao_interno'].x}, {coordenadas['campo_descricao_interno'].y})
    COORD_CAMPO_NOME_ARVORE_INTERNO = ({coordenadas['campo_nome_arvore_interno'].x}, {coordenadas['campo_nome_arvore_interno'].y})
    COORD_RADIO_PUBLICO             = ({coordenadas['radio_publico'].x}, {coordenadas['radio_publico'].y})
    COORD_BTN_SALVAR_FORM           = ({coordenadas['btn_salvar_form'].x}, {coordenadas['btn_salvar_form'].y})

    # =========================================================
    # COORDENADAS - FORMULÁRIO DOCUMENTO EXTERNO
    # =========================================================
    COORD_DROPDOWN_TIPO_EXTERNO      = ({coordenadas['dropdown_tipo_externo'].x}, {coordenadas['dropdown_tipo_externo'].y})
    COORD_CAMPO_DATA                 = ({coordenadas['campo_data'].x}, {coordenadas['campo_data'].y})
    COORD_CAMPO_NUMERO               = ({coordenadas['campo_numero'].x}, {coordenadas['campo_numero'].y})
    COORD_CAMPO_NOME_ARVORE          = ({coordenadas['campo_nome_arvore'].x}, {coordenadas['campo_nome_arvore'].y})
    COORD_RADIO_NATO_DIGITAL         = ({coordenadas['radio_nato_digital'].x}, {coordenadas['radio_nato_digital'].y})
    COORD_RADIO_DIGITALIZADO         = ({coordenadas['radio_digitalizado'].x}, {coordenadas['radio_digitalizado'].y})
    COORD_DROPDOWN_TIPO_CONFERENCIA  = ({coordenadas['dropdown_tipo_conferencia'].x}, {coordenadas['dropdown_tipo_conferencia'].y})
    COORD_BTN_ANEXAR_ARQUIVO         = ({coordenadas['btn_anexar_arquivo'].x}, {coordenadas['btn_anexar_arquivo'].y})

    # =========================================================
    # COORDENADAS - POPUP DO EDITOR
    # =========================================================
    COORD_AREA_EDICAO = ({coordenadas['area_edicao_max'].x}, {coordenadas['area_edicao_max'].y})
"""

print()
print("="*70)
print("📋 COPIE O BLOCO ABAIXO E SUBSTITUA AS COORDENADAS NO sei_automation.py:")
print("="*70)
print(bloco)
print("="*70)

# Salva também em arquivo .py para facilitar
arquivo_py = 'coordenadas_geradas.py'
with open(arquivo_py, 'w', encoding='utf-8') as f:
    f.write(f"# Gerado automaticamente em {time.strftime('%d/%m/%Y %H:%M:%S')}\n")
    f.write(f"# Resolução: {pyautogui.size()}\n")
    f.write("# Cole o conteúdo abaixo dentro da classe SEIAutomation\n\n")
    f.write(bloco)
print(f"\n💾 Bloco também salvo em '{arquivo_py}' para fácil cópia!")
print("="*70)
input("\nPressione ENTER para sair...")