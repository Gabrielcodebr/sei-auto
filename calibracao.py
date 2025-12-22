"""
Ferramenta de calibração para descobrir coordenadas na tela
"""

import pyautogui
import time

print("="*70)
print("🎯 FERRAMENTA DE CALIBRAÇÃO - SEI AUTOMATION")
print("="*70)
print()
print("Esta ferramenta vai te ajudar a descobrir as coordenadas corretas")
print("dos elementos na tela do SEI.")
print()
print("INSTRUÇÕES:")
print("  1. Posicione a janela do Firefox com o SEI aberto")
print("  2. MAXIMIZE a janela")
print("  3. Quando solicitado, posicione o mouse sobre o elemento")
print("  4. NÃO clique, apenas posicione o mouse")
print()

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

# Captura coordenadas dos elementos principais
print("\n" + "="*70)
print("Vamos capturar as coordenadas dos elementos:")
print("="*70)

coordenadas = {}

# 1. Botão Incluir Documento
coordenadas['btn_incluir_doc'] = capturar_posicao(
    "BOTÃO 'Incluir Documento' (ícone tracejado amarelo)"
)

# 2. Barra de pesquisa da lista de tipos
input("\nPressione ENTER quando estiver pronto para o próximo...")
print("\nAgora clique MANUALMENTE no botão 'Incluir Documento' para abrir a lista")
input("Pressione ENTER quando a lista estiver aberta...")

coordenadas['barra_pesquisa_lista'] = capturar_posicao(
    "BARRA DE PESQUISA (campo branco no topo da lista)"
)

# 3. Botão Salvar (formulário)
input("\nPressione ENTER quando estiver pronto para o próximo...")
print("\nSelecione MANUALMENTE um tipo de documento interno (ex: Informação)")
input("Pressione ENTER quando o formulário 'Gerar Documento' estiver aberto...")

# Rola até o final
print("\nRole a página até o FINAL (onde está o botão Salvar)")
input("Pressione ENTER quando estiver no final...")

coordenadas['btn_salvar_form'] = capturar_posicao(
    "BOTÃO 'Salvar' (no formulário)"
)

# 4. Radio button Público
print("\nAgora posicione sobre o radio button 'Público'")
coordenadas['radio_publico'] = capturar_posicao(
    "RADIO BUTTON 'Público' (Nível de Acesso)"
)

# 5. Botão Salvar do Editor
input("\nPressione ENTER quando estiver pronto para o próximo...")
print("\nClique MANUALMENTE no botão Salvar do formulário")
input("Pressione ENTER quando o EDITOR DE TEXTO estiver aberto (popup)...")

coordenadas['btn_salvar_editor'] = capturar_posicao(
    "BOTÃO 'Salvar' (no editor/popup)"
)

# 6. Área de edição
coordenadas['area_edicao'] = capturar_posicao(
    "CENTRO DA ÁREA DE EDIÇÃO (onde você digitaria texto)"
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
print("\n💾 Salvando coordenadas em 'coordenadas.txt'...")

with open('coordenadas.txt', 'w', encoding='utf-8') as f:
    f.write("# Coordenadas calibradas para SEI Automation\n")
    f.write(f"# Resolução: {pyautogui.size()}\n")
    f.write(f"# Data: {time.strftime('%d/%m/%Y %H:%M:%S')}\n\n")
    
    for nome, pos in coordenadas.items():
        f.write(f"{nome} = ({pos.x}, {pos.y})\n")

print("✅ Coordenadas salvas!")

# Gera código Python para copiar
print("\n" + "="*70)
print("📋 CÓDIGO PARA USAR NO sei_automation.py:")
print("="*70)
print("\n# Cole isso no início da classe SEIAutomation:")
print("# (Substitua as coordenadas fixas pelas abaixo)\n")

print(f"COORD_BTN_INCLUIR_DOC = ({coordenadas['btn_incluir_doc'].x}, {coordenadas['btn_incluir_doc'].y})")
print(f"COORD_BARRA_PESQUISA = ({coordenadas['barra_pesquisa_lista'].x}, {coordenadas['barra_pesquisa_lista'].y})")
print(f"COORD_BTN_SALVAR_FORM = ({coordenadas['btn_salvar_form'].x}, {coordenadas['btn_salvar_form'].y})")
print(f"COORD_RADIO_PUBLICO = ({coordenadas['radio_publico'].x}, {coordenadas['radio_publico'].y})")
print(f"COORD_BTN_SALVAR_EDITOR = ({coordenadas['btn_salvar_editor'].x}, {coordenadas['btn_salvar_editor'].y})")
print(f"COORD_AREA_EDICAO = ({coordenadas['area_edicao'].x}, {coordenadas['area_edicao'].y})")

print("\n" + "="*70)
print("✅ Processo completo! Use essas coordenadas no script principal.")
print("="*70)

input("\nPressione ENTER para sair...")