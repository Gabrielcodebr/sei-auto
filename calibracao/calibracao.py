"""
Ferramenta de calibração para descobrir coordenadas na tela
ATUALIZADO: Foca apenas nas coordenadas do popup maximizado
"""

import pyautogui
import time

print("="*70)
print("🎯 CALIBRAÇÃO - POPUP MAXIMIZADO")
print("="*70)
print()
print("Vamos calibrar apenas as coordenadas do POPUP DO EDITOR.")
print()
print("PREPARAÇÃO:")
print("  1. Abra o Firefox com o SEI")
print("  2. Abra um processo")
print("  3. Clique em 'Incluir Documento'")
print("  4. Selecione um tipo interno (ex: Informação)")
print("  5. Preencha os campos e clique em Salvar")
print("  6. Quando o popup abrir, pressione Alt+Espaço -> X para maximizar")
print()
input("Pressione ENTER quando o popup estiver MAXIMIZADO...")

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

# Área de edição do popup maximizado
coordenadas['area_edicao_max'] = capturar_posicao(
    "CENTRO DA ÁREA DE EDIÇÃO (popup maximizado)"
)

# Exibe resumo
print("\n" + "="*70)
print("✅ CALIBRAÇÃO CONCLUÍDA!")
print("="*70)
print("\nCoordenada capturada:")
print("-" * 70)

for nome, pos in coordenadas.items():
    print(f"{nome:30} → X={pos.x:4}, Y={pos.y:4}")

# Gera código Python
print("\n" + "="*70)
print("📋 ATUALIZE NO sei_automation.py:")
print("="*70)
print("\n# Substitua esta linha na classe SEIAutomation:\n")

print(f"COORD_AREA_EDICAO = ({coordenadas['area_edicao_max'].x}, {coordenadas['area_edicao_max'].y})")

print("\n" + "="*70)
print("✅ Use essa nova coordenada no script principal!")
print("="*70)

input("\nPressione ENTER para sair...")