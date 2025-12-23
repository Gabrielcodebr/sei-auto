"""
Calibração para DOCUMENTOS EXTERNOS
"""

import pyautogui
import time

print("="*70)
print("🎯 CALIBRAÇÃO - DOCUMENTOS EXTERNOS")
print("="*70)
print()
print("Vamos calibrar as coordenadas do formulário de DOCUMENTO EXTERNO.")
print()
print("PREPARAÇÃO:")
print("  1. Abra o Firefox com o SEI")
print("  2. Abra um processo")
print("  3. Clique em 'Incluir Documento'")
print("  4. Selecione 'Externo'")
print("  5. Aguarde o formulário 'Registrar Documento Externo' abrir")
print()
input("Pressione ENTER quando o formulário estiver aberto...")

def capturar_posicao(nome_elemento):
    """Captura a posição do mouse após contagem regressiva"""
    print(f"\n📍 Posicione o mouse sobre: {nome_elemento}")
    print("   Aguardando 5 segundos...")
    
    for i in range(5, 0, -1):
        print(f"   {i}...", end='\r')
        time.sleep(1)
    
    pos = pyautogui.position()
    print(f"   ✅ Posição capturada: X={pos.x}, Y={pos.y}")
    return pos

coordenadas = {}

# 1. Dropdown "Tipo do Documento"
coordenadas['dropdown_tipo_externo'] = capturar_posicao(
    "DROPDOWN 'Tipo do Documento' (caixa de seleção)"
)

# 2. Campo Data
input("\nPressione ENTER para próximo...")
coordenadas['campo_data'] = capturar_posicao(
    "CAMPO 'Data do Documento'"
)

# 3. Campo Número
input("\nPressione ENTER para próximo...")
coordenadas['campo_numero'] = capturar_posicao(
    "CAMPO 'Número'"
)

# 4. Campo Nome na Árvore
input("\nPressione ENTER para próximo...")
coordenadas['campo_nome_arvore'] = capturar_posicao(
    "CAMPO 'Nome na Árvore'"
)

# 5. Radio Nato-digital
print("\nRole a página até ver os radio buttons de FORMATO")
input("Pressione ENTER quando estiver vendo os radio buttons...")
coordenadas['radio_nato_digital'] = capturar_posicao(
    "RADIO BUTTON 'Nato-digital'"
)

# 6. Radio Digitalizado
coordenadas['radio_digitalizado'] = capturar_posicao(
    "RADIO BUTTON 'Digitalizado nesta Unidade'"
)

# 7. Botão Anexar Arquivo
print("\nRole mais um pouco até ver o botão 'Anexar Arquivo...'")
input("Pressione ENTER quando estiver vendo o botão...")
coordenadas['btn_anexar_arquivo'] = capturar_posicao(
    "BOTÃO 'Anexar Arquivo...'"
)

# Exibe resumo
print("\n" + "="*70)
print("✅ CALIBRAÇÃO CONCLUÍDA!")
print("="*70)
print("\nCoordenadas capturadas:")
print("-" * 70)

for nome, pos in coordenadas.items():
    print(f"{nome:30} → X={pos.x:4}, Y={pos.y:4}")

# Salva em arquivo
print("\n💾 Salvando em 'coordenadas_externo.txt'...")

with open('coordenadas_externo.txt', 'w', encoding='utf-8') as f:
    f.write("# Coordenadas para DOCUMENTOS EXTERNOS\n")
    f.write(f"# Resolução: {pyautogui.size()}\n")
    f.write(f"# Data: {time.strftime('%d/%m/%Y %H:%M:%S')}\n\n")
    
    for nome, pos in coordenadas.items():
        f.write(f"{nome} = ({pos.x}, {pos.y})\n")

print("✅ Coordenadas salvas!")

# Gera código Python
print("\n" + "="*70)
print("📋 ADICIONE NO sei_automation.py (classe SEIAutomation):")
print("="*70)
print()

print(f"COORD_DROPDOWN_TIPO_EXTERNO = ({coordenadas['dropdown_tipo_externo'].x}, {coordenadas['dropdown_tipo_externo'].y})")
print(f"COORD_CAMPO_DATA = ({coordenadas['campo_data'].x}, {coordenadas['campo_data'].y})")
print(f"COORD_CAMPO_NUMERO = ({coordenadas['campo_numero'].x}, {coordenadas['campo_numero'].y})")
print(f"COORD_CAMPO_NOME_ARVORE = ({coordenadas['campo_nome_arvore'].x}, {coordenadas['campo_nome_arvore'].y})")
print(f"COORD_RADIO_NATO_DIGITAL = ({coordenadas['radio_nato_digital'].x}, {coordenadas['radio_nato_digital'].y})")
print(f"COORD_RADIO_DIGITALIZADO = ({coordenadas['radio_digitalizado'].x}, {coordenadas['radio_digitalizado'].y})")
print(f"COORD_BTN_ANEXAR_ARQUIVO = ({coordenadas['btn_anexar_arquivo'].x}, {coordenadas['btn_anexar_arquivo'].y})")

print("\n" + "="*70)
print("✅ Copie e cole essas linhas no código!")
print("="*70)

input("\nPressione ENTER para sair...")