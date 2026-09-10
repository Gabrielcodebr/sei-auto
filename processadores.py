"""
processadores.py — as "estratégias" de como inserir cada tipo de
documento no SEI.

Cada função tem a assinatura:

    def _proc_xxx(automacao, step, arquivo):
        ...

- automacao: a instância de SEIAutomation (dá acesso aos helpers de
  clique/espera já existentes e a dados_contexto)
- step:      o passo do pipeline (dict — ver pipeline.py), com os
  campos equivalentes ao antigo config.DOCUMENTOS[chave] em
  step['config_doc']
- arquivo:   caminho do PDF/DOCX (None para passos com origem='gerado')

A lógica de EXTRAÇÃO de cada tipo de documento (datas, números, nomes
de empresa) é mantida quase literal em relação ao código original —
isso é conhecimento de domínio específico de cada formulário do SEI,
não boilerplate, então não foi generalizado. O que mudou é só a forma
como cada função é chamada (via um dicionário de despacho orientado
pelo pipeline, em vez de um método fixo por doc).

Para tipos NOVOS criados pelo usuário sem lógica própria, há
processadores GENÉRICOS no fim do arquivo (_proc_generico_*).
"""

import config
import pdf_utils
import pyautogui


# =====================================================================
# GERADO (sem arquivo) — usado por qualquer passo com origem='gerado',
# tanto os "de fábrica" (despacho de aprovação de NE) quanto novos
# criados pelo usuário.
# =====================================================================

def _proc_despacho_gerado(automacao, step, arquivo=None):
    gc = step.get("gerado_config") or {}
    template = gc.get("template", "")
    campos = gc.get("campos", [])

    valores = {}
    for campo in campos:
        nome_campo = campo["nome"]
        if campo.get("fonte") == "fixo":
            valores[nome_campo] = campo.get("valor", "")
            continue
        chave = campo.get("chave", nome_campo)
        valor = automacao.dados_contexto.get(chave)
        if valor is None:
            valor = f"[{nome_campo.upper()}]"
        elif "data" in nome_campo.lower():
            valor = automacao._data_fallback(valor)
        valores[nome_campo] = valor

    doc_cfg = step.get("config_doc") or {}
    captura_link = bool(gc.get("captura_link"))

    if captura_link:
        placeholder_link = "link_ne" if "{link_ne}" in template else ("link" if "{link}" in template else None)
        if not placeholder_link:
            raise Exception(
                f"Passo '{step['id']}': 'captura_link' está ativado, mas o "
                "template não contém {link_ne} nem {link}."
            )
        coord_por_tipo = gc.get("coord_icone_arvore") or {}
        coord = coord_por_tipo.get(automacao.tipo_processo) if isinstance(coord_por_tipo, dict) else coord_por_tipo
        if not coord:
            raise Exception(
                f"Passo '{step['id']}' pede captura de link, mas não há coordenada "
                f"calibrada para o tipo de processo '{automacao.tipo_processo}'. "
                "Calibre em Configurações → Coordenadas."
            )

        link_valor = automacao.capturar_link_documento_arvore(tuple(coord))

        marcador = "<<<LINK>>>"
        try:
            texto_completo = template.format(**{**valores, placeholder_link: marcador})
        except KeyError as e:
            raise Exception(f"Passo '{step['id']}': placeholder {e} sem valor em 'campos'.")
        partes = texto_completo.split(marcador)
        texto_antes = partes[0]
        texto_depois = partes[1] if len(partes) > 1 else ""

        automacao.clicar_botao_incluir_documento()
        automacao.pesquisar_e_selecionar_tipo_doc(doc_cfg.get("busca", "Despacho"))
        automacao.preencher_formulario_interno(
            doc_cfg.get("descricao", ""), doc_cfg.get("nome_arvore", step["id"])
        )
        automacao.selecionar_nivel_acesso_publico()
        automacao.clicar_salvar()
        automacao.aguardar(config.TEMPOS.get("pos_click_salvar_doc04", 2.0))
        automacao.colar_despacho_com_link(texto_antes, link_valor, texto_depois)
        automacao.clicar_salvar_editor()
    else:
        try:
            texto = template.format(**valores)
        except KeyError as e:
            raise Exception(f"Passo '{step['id']}': placeholder {e} sem valor em 'campos'.")

        automacao.clicar_botao_incluir_documento()
        automacao.pesquisar_e_selecionar_tipo_doc(doc_cfg.get("busca", "Despacho"))
        automacao.preencher_formulario_interno(
            doc_cfg.get("descricao", ""), doc_cfg.get("nome_arvore", step["id"])
        )
        automacao.selecionar_nivel_acesso_publico()
        automacao.clicar_salvar()
        automacao.colar_texto_editor(texto)
        automacao.clicar_salvar_editor()

    print(f"✅ {step['id']} (gerado) inserido!\n")


# =====================================================================
# BESPOKE — porte quase literal da lógica original de cada tipo
# =====================================================================

def _proc_capa_especial(automacao, step, arquivo):
    imagem = pdf_utils.processar_capa_especial(arquivo)
    if not imagem:
        raise Exception("Erro ao processar capa")

    doc_cfg = step["config_doc"]
    automacao.clicar_botao_incluir_documento()
    automacao.pesquisar_e_selecionar_tipo_doc(doc_cfg["busca"])
    automacao.preencher_formulario_interno(doc_cfg["descricao"], doc_cfg["nome_arvore"])
    automacao.selecionar_nivel_acesso_publico()
    automacao.clicar_salvar()
    automacao.colar_imagem_editor(imagem)
    automacao.clicar_salvar_editor()
    print(f"✅ {step['id']} inserida!\n")


def _proc_imagem_pdf_padrao(automacao, step, arquivo):
    imagem = pdf_utils.processar_print_padrao(arquivo)
    if not imagem:
        raise Exception(f"Erro ao renderizar PDF: {arquivo}")

    doc_cfg = step["config_doc"]
    automacao.clicar_botao_incluir_documento()
    automacao.pesquisar_e_selecionar_tipo_doc(doc_cfg["busca"])
    automacao.preencher_formulario_interno(doc_cfg["descricao"], doc_cfg["nome_arvore"])
    automacao.selecionar_nivel_acesso_publico()
    automacao.clicar_salvar()
    automacao.colar_imagem_editor(imagem)
    automacao.clicar_salvar_editor()
    print(f"✅ {step['id']} inserido!\n")


def _proc_nota_empenho(automacao, step, arquivo):
    dados = pdf_utils.extrair_dados_nota_empenho(arquivo)
    if not dados["data"] or not dados["numero"]:
        print("⚠️ ATENÇÃO: Dados não extraídos completamente!")

    automacao.dados_contexto["ne_data"] = automacao._data_fallback(dados["data"])
    automacao.dados_contexto["ne_numero"] = dados["numero"] or "[NÚMERO]"

    doc_cfg = step["config_doc"]
    automacao.clicar_botao_incluir_documento()
    automacao.pesquisar_e_selecionar_tipo_doc(doc_cfg["busca"])
    automacao.aguardar(config.TEMPOS["pos_pesquisa_externo"])

    automacao.selecionar_dropdown_tipo_externo(doc_cfg["tipo_externo"])
    automacao.preencher_campo_clicando(config.COORD_CAMPO_DATA, automacao.dados_contexto["ne_data"])
    automacao.preencher_campo_clicando(config.COORD_CAMPO_NUMERO, dados["numero"])
    automacao.preencher_campo_clicando(config.COORD_CAMPO_NOME_ARVORE, dados["numero"])

    pyautogui.click(config.COORD_RADIO_NATO_DIGITAL)
    automacao.aguardar(0.3)

    automacao.selecionar_nivel_acesso_publico_externo()
    automacao.anexar_arquivo_externo(arquivo)

    print("  📜 Ajustando scroll após upload...")
    for _ in range(3):
        pyautogui.scroll(-400)
        automacao.aguardar(0.2)

    automacao.clicar_salvar()
    automacao.verificar_popup_documento_similar()
    print("✅ NOTA DE EMPENHO inserida!\n")

    print("  ⏳ Aguardando tela principal recarregar...")
    automacao.aguardar(config.TEMPOS["recarregar_tela"])


def _proc_ordem_bancaria(automacao, step, arquivo):
    dados = pdf_utils.extrair_dados_ordem_bancaria(arquivo)
    if not dados["data"] or not dados["numero"]:
        print("⚠️ ATENÇÃO: Dados não extraídos completamente!")

    doc_cfg = step["config_doc"]
    automacao.clicar_botao_incluir_documento()
    automacao.pesquisar_e_selecionar_tipo_doc(doc_cfg["busca"])
    automacao.aguardar(config.TEMPOS["pos_pesquisa_externo"])

    automacao.selecionar_dropdown_tipo_externo(doc_cfg["tipo_externo"])
    automacao.preencher_campo_clicando(config.COORD_CAMPO_DATA, automacao._data_fallback(dados["data"]))
    automacao.preencher_campo_clicando(config.COORD_CAMPO_NUMERO, dados["numero"])
    automacao.preencher_campo_clicando(config.COORD_CAMPO_NOME_ARVORE, dados["numero"])

    pyautogui.click(config.COORD_RADIO_NATO_DIGITAL)
    automacao.aguardar(0.3)

    automacao.selecionar_nivel_acesso_publico_externo()
    automacao.anexar_arquivo_externo(arquivo)

    print("  📜 Ajustando scroll após upload...")
    for _ in range(3):
        pyautogui.scroll(-400)
        automacao.aguardar(0.2)

    automacao.clicar_salvar()
    automacao.verificar_popup_documento_similar()
    print("✅ ORDEM BANCÁRIA inserida!\n")

    print("  ⏳ Aguardando tela principal recarregar...")
    automacao.aguardar(config.TEMPOS["recarregar_tela"])


def _proc_quadro_comparativo(automacao, step, arquivo):
    assinaturas = (step.get("processor_config") or {}).get("assinaturas")
    imagem = pdf_utils.processar_planilha_pesquisa_preco(arquivo, assinaturas=assinaturas)
    if not imagem:
        raise Exception(f"Erro ao renderizar PDF: {arquivo}")

    doc_cfg = step["config_doc"]
    automacao.clicar_botao_incluir_documento()
    automacao.pesquisar_e_selecionar_tipo_doc(doc_cfg["busca"])
    automacao.preencher_formulario_interno(doc_cfg["descricao"], doc_cfg["nome_arvore"])
    automacao.selecionar_nivel_acesso_publico()
    automacao.clicar_salvar()
    automacao.colar_imagem_editor(imagem)
    automacao.clicar_salvar_editor()
    print("✅ QUADRO COMPARATIVO inserido!\n")


def _proc_nota_fiscal(automacao, step, arquivo):
    dados = pdf_utils.extrair_dados_nota_fiscal(arquivo)

    numero_do_nome = automacao.extrair_numero_nota_fiscal_do_nome(arquivo)
    if numero_do_nome:
        dados["numero"] = numero_do_nome

    if not dados["data"] or not dados["numero"]:
        print("⚠️ ATENÇÃO: Dados não extraídos completamente!")

    empresa = automacao.extrair_empresa_do_nome_arquivo(arquivo)

    automacao.dados_contexto["nf_data"] = automacao._data_fallback(dados["data"])
    automacao.dados_contexto["nf_numero"] = dados["numero"] or "[NÚMERO]"
    automacao.dados_contexto["nf_empresa"] = empresa

    doc_cfg = step["config_doc"]
    automacao.clicar_botao_incluir_documento()
    automacao.pesquisar_e_selecionar_tipo_doc(doc_cfg["busca"])
    automacao.aguardar(config.TEMPOS["pos_pesquisa_externo"])

    automacao.selecionar_dropdown_tipo_externo(doc_cfg["tipo_externo"])
    automacao.preencher_campo_clicando(config.COORD_CAMPO_DATA, automacao.dados_contexto["nf_data"])
    automacao.preencher_campo_clicando(config.COORD_CAMPO_NUMERO, dados["numero"])
    automacao.preencher_campo_clicando(config.COORD_CAMPO_NOME_ARVORE, automacao.dados_contexto["nf_empresa"])

    pyautogui.click(config.COORD_RADIO_NATO_DIGITAL)
    automacao.aguardar(0.3)

    automacao.selecionar_nivel_acesso_publico_externo()
    automacao.anexar_arquivo_externo(arquivo)

    print("  📜 Ajustando scroll após upload...")
    for _ in range(3):
        pyautogui.scroll(-400)
        automacao.aguardar(0.2)

    automacao.clicar_salvar()
    automacao.verificar_popup_documento_similar()
    print("✅ NOTA FISCAL inserida!\n")

    print("  ⏳ Aguardando tela principal recarregar...")
    automacao.aguardar(config.TEMPOS["recarregar_tela"])


def _proc_comprovante_fiscal(automacao, step, arquivo):
    data = automacao._data_fallback(automacao.dados_contexto.get("nf_data"))
    numero = automacao.dados_contexto.get("nf_numero", "[NÚMERO]")
    empresa = automacao.dados_contexto.get("nf_empresa", "[EMPRESA]")

    doc_cfg = step["config_doc"]
    automacao.clicar_botao_incluir_documento()
    automacao.pesquisar_e_selecionar_tipo_doc(doc_cfg["busca"])
    automacao.aguardar(config.TEMPOS["pos_pesquisa_externo"])

    automacao.selecionar_dropdown_tipo_externo(doc_cfg["tipo_externo"])
    automacao.preencher_campo_clicando(config.COORD_CAMPO_DATA, data)
    automacao.preencher_campo_clicando(config.COORD_CAMPO_NUMERO, numero)
    automacao.preencher_campo_clicando(config.COORD_CAMPO_NOME_ARVORE, empresa)

    pyautogui.click(config.COORD_RADIO_DIGITALIZADO)
    automacao.aguardar(0.5)

    automacao.selecionar_tipo_conferencia("Cópia Autenticada Administrativamente")
    automacao.selecionar_nivel_acesso_publico_externo()
    automacao.anexar_arquivo_externo(arquivo)

    print("  📜 Ajustando scroll após upload...")
    for _ in range(3):
        pyautogui.scroll(-400)
        automacao.aguardar(0.2)

    automacao.clicar_salvar()
    automacao.verificar_popup_documento_similar()
    print("✅ COMPROVANTE FISCAL inserido!\n")

    print("  ⏳ Aguardando tela principal recarregar...")
    automacao.aguardar(config.TEMPOS["recarregar_tela"])


def _proc_declaracao_recebimento(automacao, step, arquivo):
    imagem = pdf_utils.renderizar_docx_como_imagem(arquivo)
    if not imagem:
        raise Exception(
            "Erro ao renderizar .docx da declaração.\n"
            "O Microsoft Word precisa estar instalado (a conversão usa win32com)."
        )

    empresa = automacao.extrair_empresa_do_nome_arquivo(arquivo)
    if empresa == "[EMPRESA]":
        empresa_ctx = automacao.dados_contexto.get("nf_empresa", "")
        if empresa_ctx:
            empresa = empresa_ctx
            print(f"  ℹ️ Empresa vinda do contexto (fallback): '{empresa}'")

    doc_cfg = step["config_doc"]
    automacao.clicar_botao_incluir_documento()
    automacao.pesquisar_e_selecionar_tipo_doc(doc_cfg["busca"])
    automacao.preencher_formulario_interno(doc_cfg["descricao"], empresa)
    automacao.selecionar_nivel_acesso_publico()
    automacao.clicar_salvar()
    automacao.colar_imagem_editor(imagem)
    automacao.clicar_salvar_editor()
    print("✅ DECLARAÇÃO DE RECEBIMENTO inserida!\n")


def _proc_consulta_optante(automacao, step, arquivo):
    dados = pdf_utils.extrair_dados_consulta(arquivo)
    empresa = automacao.extrair_empresa_do_nome_arquivo(arquivo)

    automacao.dados_contexto["consulta_cnpj"] = dados["numero"]

    doc_cfg = step["config_doc"]
    automacao.clicar_botao_incluir_documento()
    automacao.pesquisar_e_selecionar_tipo_doc(doc_cfg["busca"])
    automacao.aguardar(config.TEMPOS["pos_pesquisa_externo"])

    automacao.selecionar_dropdown_tipo_externo(doc_cfg["tipo_externo"])
    automacao.preencher_campo_clicando(config.COORD_CAMPO_DATA, automacao._data_fallback(dados["data"]))
    automacao.preencher_campo_clicando(config.COORD_CAMPO_NUMERO, dados["numero"] or "[CNPJ]")
    automacao.preencher_campo_clicando(config.COORD_CAMPO_NOME_ARVORE, empresa)

    pyautogui.click(config.COORD_RADIO_NATO_DIGITAL)
    automacao.aguardar(0.3)

    automacao.selecionar_nivel_acesso_publico_externo()
    automacao.anexar_arquivo_externo(arquivo)

    print("  📜 Ajustando scroll após upload...")
    for _ in range(3):
        pyautogui.scroll(-400)
        automacao.aguardar(0.2)

    automacao.clicar_salvar()
    automacao.verificar_popup_documento_similar()
    print("✅ CONSULTA DE OPTANTE inserida!\n")

    print("  ⏳ Aguardando tela principal recarregar...")
    automacao.aguardar(config.TEMPOS["recarregar_tela"])


def _proc_cnpj(automacao, step, arquivo):
    dados = pdf_utils.extrair_dados_cnpj(arquivo)
    empresa = automacao.extrair_empresa_do_nome_arquivo(arquivo)

    cnpj = automacao.dados_contexto.get("consulta_cnpj")
    if cnpj:
        print(f"  ✅ CNPJ reutilizado da Consulta Optante: {cnpj}")
    else:
        cnpj = dados["numero"]
        print(f"  ⚠️ CNPJ da consulta não disponível — extraindo do PDF: {cnpj}")
    if not cnpj:
        cnpj = "[CNPJ]"
        print("  ❌ CNPJ não encontrado em nenhuma fonte!")

    doc_cfg = step["config_doc"]
    automacao.clicar_botao_incluir_documento()
    automacao.pesquisar_e_selecionar_tipo_doc(doc_cfg["busca"])
    automacao.aguardar(config.TEMPOS["pos_pesquisa_externo"])

    automacao.selecionar_dropdown_tipo_externo(doc_cfg["tipo_externo"])
    automacao.preencher_campo_clicando(config.COORD_CAMPO_DATA, automacao._data_fallback(dados["data"]))
    automacao.preencher_campo_clicando(config.COORD_CAMPO_NUMERO, cnpj)
    automacao.preencher_campo_clicando(config.COORD_CAMPO_NOME_ARVORE, empresa)

    pyautogui.click(config.COORD_RADIO_NATO_DIGITAL)
    automacao.aguardar(0.3)

    automacao.selecionar_nivel_acesso_publico_externo()
    automacao.anexar_arquivo_externo(arquivo)

    print("  📜 Ajustando scroll após upload...")
    for _ in range(3):
        pyautogui.scroll(-400)
        automacao.aguardar(0.2)

    automacao.clicar_salvar()
    automacao.verificar_popup_documento_similar()
    print("✅ CNPJ inserido!\n")

    print("  ⏳ Aguardando tela principal recarregar...")
    automacao.aguardar(config.TEMPOS["recarregar_tela"])


def _proc_guia_iss(automacao, step, arquivo):
    dados = pdf_utils.extrair_dados_guia_iss(arquivo)

    automacao.dados_contexto["iss_data"] = automacao._data_fallback(dados["data"])
    automacao.dados_contexto["iss_numero"] = dados["numero"] or "[NÚMERO]"

    doc_cfg = step["config_doc"]
    automacao.clicar_botao_incluir_documento()
    automacao.pesquisar_e_selecionar_tipo_doc(doc_cfg["busca"])
    automacao.aguardar(config.TEMPOS["pos_pesquisa_externo"])

    automacao.selecionar_dropdown_tipo_externo(doc_cfg["tipo_externo"])
    automacao.preencher_campo_clicando(config.COORD_CAMPO_DATA, automacao.dados_contexto["iss_data"])
    automacao.preencher_campo_clicando(config.COORD_CAMPO_NUMERO, automacao.dados_contexto["iss_numero"])
    automacao.preencher_campo_clicando(config.COORD_CAMPO_NOME_ARVORE, automacao.dados_contexto["iss_numero"])

    pyautogui.click(config.COORD_RADIO_NATO_DIGITAL)
    automacao.aguardar(0.3)

    automacao.selecionar_nivel_acesso_publico_externo()
    automacao.anexar_arquivo_externo(arquivo)

    print("  📜 Ajustando scroll após upload...")
    for _ in range(3):
        pyautogui.scroll(-400)
        automacao.aguardar(0.2)

    automacao.clicar_salvar()
    automacao.verificar_popup_documento_similar()
    print("✅ GUIA DE RECOLHIMENTO DO ISS inserida!\n")

    print("  ⏳ Aguardando tela principal recarregar...")
    automacao.aguardar(config.TEMPOS["recarregar_tela"])


def _proc_comprovante_iss(automacao, step, arquivo):
    data = automacao.dados_contexto.get("iss_data")
    numero = automacao.dados_contexto.get("iss_numero")

    if not data or not numero or numero == "[NÚMERO]":
        print("  ⚠️ Dados ISS não encontrados no contexto — extraindo do arquivo...")
        dados = pdf_utils.extrair_dados_guia_iss(arquivo)
        data = automacao._data_fallback(dados["data"])
        numero = dados["numero"] or "[NÚMERO]"
    else:
        data = automacao._data_fallback(data)

    empresa = automacao.dados_contexto.get("nf_empresa", "")
    if not empresa:
        empresa = automacao.extrair_empresa_do_nome_arquivo(arquivo)

    doc_cfg = step["config_doc"]
    automacao.clicar_botao_incluir_documento()
    automacao.pesquisar_e_selecionar_tipo_doc(doc_cfg["busca"])
    automacao.aguardar(config.TEMPOS["pos_pesquisa_externo"])

    automacao.selecionar_dropdown_tipo_externo(doc_cfg["tipo_externo"])
    automacao.preencher_campo_clicando(config.COORD_CAMPO_DATA, data)
    automacao.preencher_campo_clicando(config.COORD_CAMPO_NUMERO, numero)
    automacao.preencher_campo_clicando(config.COORD_CAMPO_NOME_ARVORE, empresa)

    pyautogui.click(config.COORD_RADIO_DIGITALIZADO)
    automacao.aguardar(0.5)

    automacao.selecionar_tipo_conferencia("Cópia Autenticada Administrativamente")
    automacao.selecionar_nivel_acesso_publico_externo()
    automacao.anexar_arquivo_externo(arquivo)

    print("  📜 Ajustando scroll após upload...")
    for _ in range(3):
        pyautogui.scroll(-400)
        automacao.aguardar(0.2)

    automacao.clicar_salvar()
    automacao.verificar_popup_documento_similar()
    print("✅ COMPROVANTE DE ISS inserido!\n")

    print("  ⏳ Aguardando tela principal recarregar...")
    automacao.aguardar(config.TEMPOS["recarregar_tela"])


def _proc_extrato_bancario(automacao, step, arquivo):
    data = pdf_utils.extrair_data_extrato(arquivo)

    doc_cfg = step["config_doc"]
    automacao.clicar_botao_incluir_documento()
    automacao.pesquisar_e_selecionar_tipo_doc(doc_cfg["busca"])
    automacao.aguardar(config.TEMPOS["pos_pesquisa_externo"])

    automacao.selecionar_dropdown_tipo_externo(doc_cfg["tipo_externo"])
    automacao.preencher_campo_clicando(config.COORD_CAMPO_DATA, automacao._data_fallback(data))
    automacao.preencher_campo_clicando(config.COORD_CAMPO_NOME_ARVORE, doc_cfg.get("nome_arvore_fixo", ""))

    pyautogui.click(config.COORD_RADIO_NATO_DIGITAL)
    automacao.aguardar(0.3)

    automacao.selecionar_nivel_acesso_publico_externo()
    automacao.anexar_arquivo_externo(arquivo)

    print("  📜 Ajustando scroll após upload...")
    for _ in range(3):
        pyautogui.scroll(-400)
        automacao.aguardar(0.2)

    automacao.clicar_salvar()
    automacao.verificar_popup_documento_similar()
    print("✅ EXTRATO BANCÁRIO inserido!\n")

    print("  ⏳ Aguardando tela principal recarregar...")
    automacao.aguardar(config.TEMPOS["recarregar_tela"])


# =====================================================================
# GENÉRICOS — usados por tipos NOVOS criados pelo usuário sem
# lógica de extração própria.
# =====================================================================

def _proc_generico_imagem_pdf(automacao, step, arquivo):
    """Tipo novo, origem=arquivo, modo=interno: renderiza a 1ª página e cola."""
    imagem = pdf_utils.processar_print_padrao(arquivo)
    if not imagem:
        raise Exception(f"Erro ao renderizar PDF: {arquivo}")

    doc_cfg = step["config_doc"]
    automacao.clicar_botao_incluir_documento()
    automacao.pesquisar_e_selecionar_tipo_doc(doc_cfg["busca"])
    automacao.preencher_formulario_interno(
        doc_cfg.get("descricao", ""), doc_cfg.get("nome_arvore", step["id"])
    )
    automacao.selecionar_nivel_acesso_publico()
    automacao.clicar_salvar()
    automacao.colar_imagem_editor(imagem)
    automacao.clicar_salvar_editor()
    print(f"✅ {step['id']} inserido (processador genérico)!\n")


def _proc_generico_upload_externo(automacao, step, arquivo):
    """
    Tipo novo, origem=arquivo, modo=externo: extrai só a DATA (de forma
    genérica, sem regra específica de onde ela aparece no documento) e
    faz upload. Número fica em branco — edite manualmente no SEI se
    esse tipo de documento tiver um número relevante, ou peça pra eu
    escrever uma extração específica pra ele.
    """
    texto = pdf_utils.extrair_texto_completo_pdf(arquivo) if arquivo.lower().endswith(".pdf") else ""
    import ocr_utils
    data = ocr_utils.extrair_data(texto) if texto else None

    doc_cfg = step["config_doc"]
    automacao.clicar_botao_incluir_documento()
    automacao.pesquisar_e_selecionar_tipo_doc(doc_cfg["busca"])
    automacao.aguardar(config.TEMPOS["pos_pesquisa_externo"])

    automacao.selecionar_dropdown_tipo_externo(doc_cfg.get("tipo_externo", ""))
    automacao.preencher_campo_clicando(config.COORD_CAMPO_DATA, automacao._data_fallback(data))
    automacao.preencher_campo_clicando(
        config.COORD_CAMPO_NOME_ARVORE, doc_cfg.get("nome_arvore_fixo") or step["id"]
    )

    pyautogui.click(config.COORD_RADIO_NATO_DIGITAL)
    automacao.aguardar(0.3)

    automacao.selecionar_nivel_acesso_publico_externo()
    automacao.anexar_arquivo_externo(arquivo)

    print("  📜 Ajustando scroll após upload...")
    for _ in range(3):
        pyautogui.scroll(-400)
        automacao.aguardar(0.2)

    automacao.clicar_salvar()
    automacao.verificar_popup_documento_similar()
    print(f"✅ {step['id']} inserido (processador genérico)!\n")

    print("  ⏳ Aguardando tela principal recarregar...")
    automacao.aguardar(config.TEMPOS["recarregar_tela"])


# =====================================================================
# DESPACHO
# =====================================================================

PROCESSADORES = {
    "capa_especial": _proc_capa_especial,
    "imagem_pdf_padrao": _proc_imagem_pdf_padrao,
    "nota_empenho": _proc_nota_empenho,
    "despacho_gerado": _proc_despacho_gerado,
    "ordem_bancaria": _proc_ordem_bancaria,
    "quadro_comparativo": _proc_quadro_comparativo,
    "nota_fiscal": _proc_nota_fiscal,
    "comprovante_fiscal": _proc_comprovante_fiscal,
    "declaracao_recebimento": _proc_declaracao_recebimento,
    "consulta_optante": _proc_consulta_optante,
    "cnpj": _proc_cnpj,
    "guia_iss": _proc_guia_iss,
    "comprovante_iss": _proc_comprovante_iss,
    "extrato_bancario": _proc_extrato_bancario,
    "generico_imagem_pdf": _proc_generico_imagem_pdf,
    "generico_upload_externo": _proc_generico_upload_externo,
}

# Processador usado quando step['processor'] não está no dicionário
# acima (ex: id digitado errado) — cai pro genérico apropriado ao modo.
PROCESSADOR_GENERICO_POR_MODO = {
    "interno": _proc_generico_imagem_pdf,
    "externo": _proc_generico_upload_externo,
}


def processar(automacao, step, arquivo):
    """Ponto de entrada único: despacha para a função certa."""
    if step.get("origem") == "gerado":
        return _proc_despacho_gerado(automacao, step, arquivo)

    nome_processor = step.get("processor")
    func = PROCESSADORES.get(nome_processor)
    if func is None:
        modo = step.get("modo", "externo")
        func = PROCESSADOR_GENERICO_POR_MODO[modo]
        print(f"  ℹ️ Passo '{step['id']}' usa processador genérico ({modo}).")

    return func(automacao, step, arquivo)
