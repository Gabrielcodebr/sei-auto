"""
Calibração para DROPDOWN TIPO DE CONFERÊNCIA
"""

import pyautogui
import time

print("="*70)
print("🎯 CALIBRAÇÃO - DROPDOWN TIPO DE CONFERÊNCIA")
print("="*70)
print()
print("PREPARAÇÃO:")
print("  1. Abra o formulário de Documento Externo")
print("  2. Clique no radio button 'Digitalizado nesta Unidade'")
print("  3. Aguarde o dropdown 'Tipo de Conferência' aparecer")
print()
input("Pressione ENTER quando o dropdown estiver visível...")

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

coordenada = capturar_posicao(
    "DROPDOWN 'Tipo de Conferência' (caixa de seleção)"
)

print("\n" + "="*70)
print("✅ COORDENADA CAPTURADA!")
print("="*70)
print(f"\ndropdown_tipo_conferencia → X={coordenada.x:4}, Y={coordenada.y:4}")

print("\n" + "="*70)
print("📋 ADICIONE NO sei_automation.py:")
print("="*70)
print(f"\nCOORD_DROPDOWN_TIPO_CONFERENCIA = ({coordenada.x}, {coordenada.y})")

print("\n" + "="*70)

input("\nPressione ENTER para sair...")