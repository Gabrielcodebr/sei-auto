"""
Calibração para DOCUMENTOS INTERNOS
(Formulário de Informação, Despacho, Solicitação, etc.)
"""
import pyautogui
import time

print("="*70)
print("🎯 CALIBRAÇÃO - DOCUMENTOS INTERNOS")
print("="*70)
print()
print("Vamos calibrar os campos do formulário de DOCUMENTO INTERNO.")
print()
print("PREPARAÇÃO:")
print("  1. Abra o Firefox com o SEI")
print("  2. Abra um processo qualquer")
print("  3. Clique em 'Incluir Documento'")
print("  4. Selecione um tipo interno (ex: 'Informação')")
print("  5. Aguarde o formulário abrir completamente")
print()
input("Pressione ENTER quando o formulário estiver aberto...")


def capturar_posicao(nome_elemento):
    print(f"\n📍 Posicione o mouse sobre: {nome_elemento}")
    print("   Aguardando 5 segundos...")
    for i in range(5, 0, -1):
        print(f"   {i}...", end='\r')
        time.sleep(1)
    pos = pyautogui.position()
    print(f"   ✅ Posição capturada: X={pos.x}, Y={pos.y}")
    return pos


coordenadas = {}

# 1. Campo Descrição
coordenadas['campo_descricao_interno'] = capturar_posicao(
    "CAMPO 'Descrição' (caixa de texto)"
)

# 2. Campo Nome na Árvore
input("\nPressione ENTER para próximo...")
coordenadas['campo_nome_arvore_interno'] = capturar_posicao(
    "CAMPO 'Nome na Árvore' (caixa de texto)"
)

# 3. Nível de acesso - Radio Público
print("\nRole a página até ver a seção 'Nível de Acesso'")
input("Pressione ENTER quando estiver vendo o radio 'Público'...")
coordenadas['radio_publico'] = capturar_posicao(
    "RADIO BUTTON 'Público'"
)

# 4. Botão Salvar do formulário
print("\nRole até o final para ver o botão 'Salvar'")
input("Pressione ENTER quando estiver vendo o botão 'Salvar'...")
coordenadas['btn_salvar_form'] = capturar_posicao(
    "BOTÃO 'Salvar' (do formulário, não do editor)"
)

# Exibe resumo
print("\n" + "="*70)
print("✅ CALIBRAÇÃO CONCLUÍDA!")
print("="*70)
print("\nCoordenadas capturadas:")
print("-" * 70)
for nome, pos in coordenadas.items():
    print(f"{nome:35} → X={pos.x:4}, Y={pos.y:4}")

# Salva em arquivo
print("\n💾 Salvando em 'coordenadas_interno.txt'...")
with open('coordenadas_interno.txt', 'w', encoding='utf-8') as f:
    f.write("# Coordenadas para DOCUMENTOS INTERNOS\n")
    f.write(f"# Resolução: {pyautogui.size()}\n")
    f.write(f"# Data: {time.strftime('%d/%m/%Y %H:%M:%S')}\n\n")
    for nome, pos in coordenadas.items():
        f.write(f"{nome} = ({pos.x}, {pos.y})\n")
print("✅ Coordenadas salvas!")

# Gera código Python
print("\n" + "="*70)
print("📋 ATUALIZE NO sei_automation.py (classe SEIAutomation):")
print("="*70)
print()
print(f"COORD_CAMPO_DESCRICAO_INTERNO   = ({coordenadas['campo_descricao_interno'].x}, {coordenadas['campo_descricao_interno'].y})")
print(f"COORD_CAMPO_NOME_ARVORE_INTERNO = ({coordenadas['campo_nome_arvore_interno'].x}, {coordenadas['campo_nome_arvore_interno'].y})")
print(f"COORD_RADIO_PUBLICO             = ({coordenadas['radio_publico'].x}, {coordenadas['radio_publico'].y})")
print(f"COORD_BTN_SALVAR_FORM           = ({coordenadas['btn_salvar_form'].x}, {coordenadas['btn_salvar_form'].y})")
print()
print("="*70)
input("\nPressione ENTER para sair...")