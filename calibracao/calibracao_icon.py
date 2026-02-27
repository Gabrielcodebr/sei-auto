"""
Calibração - Ícone da Nota de Empenho na árvore do SEI
"""
import pyautogui
import time

print("="*70)
print("🎯 CALIBRAÇÃO - ÍCONE DA NE NA ÁRVORE")
print("="*70)
print()
print("PREPARAÇÃO:")
print("  1. Insira o documento 03 (Nota de Empenho) normalmente")
print("  2. Volte para a tela principal do processo no SEI")
print("  3. O documento deve estar visível na árvore à esquerda")
print()
input("Pressione ENTER quando o documento estiver visível na árvore...")

print()
print("📍 Posicione o mouse sobre o ÍCONE (PDF vermelho) da Nota de Empenho")
print("   na árvore do SEI")
print("   Aguardando 5 segundos...")
for i in range(5, 0, -1):
    print(f"   {i}...", end='\r')
    time.sleep(1)

pos = pyautogui.position()
print(f"   ✅ Posição capturada: X={pos.x}, Y={pos.y}")

print()
print("="*70)
print("📋 ATUALIZE NO sei_automation.py:")
print("="*70)
print(f"\nCOORD_ICONE_NE_ARVORE = ({pos.x}, {pos.y})")
print()
print("="*70)
input("\nPressione ENTER para sair...")