"""
pipeline.py — modelo de dados e lógica do "pipeline" de documentos.

Substitui a antiga lógica posicional (docs 1-5 = fixos por índice,
docs 14-17 = finais por índice) por um sistema DECLARATIVO: cada tipo
de documento é um "passo" (step) com:

    id            chave interna estável (não muda mesmo se o rótulo mudar)
    categoria     'fixo_inicial' | 'ciclo' | 'fixo_final'
    origem        'arquivo' (vem de um PDF/DOCX na pasta) | 'gerado' (o bot
                   monta o texto sozinho, sem arquivo — ex: despachos)
    modo          'interno' | 'externo' (só relevante para origem='arquivo';
                   'gerado' é sempre tratado como interno)
    ativo         bool — desabilita o passo sem apagar a configuração
    ordem         int — ordem de execução DENTRO da categoria (isso é o que
                   a interface deixa arrastar)
    aplica_a      lista de tipos de processo em que esse passo entra
                   (['DMPP','UFIEC'] por padrão)
    ancora_ciclo  bool — só usado em categoria='ciclo'; marca o tipo que
                   inicia um novo ciclo de Nota Fiscal (ver agrupar_ciclos)
    deteccao      regra p/ reconhecer o tipo pelo NOME do arquivo (só usada
                   como fallback — ver classificar_arquivo)
    config_doc    campos equivalentes ao antigo config.DOCUMENTOS[chave]
    processor_config  config extra específica do processador (ex: lista de
                   assinaturas da planilha de preço)
    gerado_config  só para origem='gerado': template, campos e (opcional)
                   captura de link

Este módulo NÃO depende de Qt nem de pyautogui — pode ser testado com
dados sintéticos, o que é importante dado o que ele controla (inserção
de documentos oficiais no SEI).
"""

import os
import re
import json
from pathlib import Path
from copy import deepcopy

import doc_ordem

NOME_ARQUIVO_PIPELINE = "pipeline_config.json"

CATEGORIAS = ("fixo_inicial", "ciclo", "fixo_final")


# =====================================================================
# PIPELINE PADRÃO — replica EXATAMENTE o comportamento anterior
# (posicional/hardcoded) para não regredir nada que já funcionava.
# =====================================================================

def _pipeline_padrao():
    return [
        # ---------------- FIXOS INICIAIS ----------------
        {
            "id": "capa", "categoria": "fixo_inicial", "ordem": 10,
            "origem": "arquivo", "modo": "interno", "ativo": True,
            "aplica_a": ["DMPP", "UFIEC"],
            "deteccao": {"contains_any": ["capa"]},
            "processor": "capa_especial",
            "config_doc": {
                "busca": "Informacao",
                "descricao": "Capa padrão imprensa oficial",
                "nome_arvore": "Capa",
            },
        },
        {
            "id": "memorando_justificativa", "categoria": "fixo_inicial", "ordem": 20,
            "origem": "arquivo", "modo": "interno", "ativo": True,
            "aplica_a": ["UFIEC"],
            "deteccao": {"contains_any": ["memorando", "justificativ"]},
            "processor": "imagem_pdf_padrao",
            "config_doc": {
                "busca": "Memorando",
                "descricao": "Memorando/Justificativa",
                "nome_arvore": "Justificativa",
            },
        },
        {
            "id": "solicitacao", "categoria": "fixo_inicial", "ordem": 30,
            "origem": "arquivo", "modo": "interno", "ativo": True,
            "aplica_a": ["DMPP", "UFIEC"],
            "deteccao": {"contains_any": ["solicita"]},
            "processor": "imagem_pdf_padrao",
            "config_doc": {
                "busca": "Solicitacao",
                "descricao": "Solicitação de adiantamento",
                "nome_arvore": "adiantamento",
            },
        },
        {
            "id": "nota_empenho", "categoria": "fixo_inicial", "ordem": 40,
            "origem": "arquivo", "modo": "externo", "ativo": True,
            "aplica_a": ["DMPP", "UFIEC"],
            "deteccao": {"contains_any": ["empenho"]},
            "processor": "nota_empenho",
            "config_doc": {"busca": "Externo", "tipo_externo": "Nota de empenho"},
        },
        {
            "id": "despacho_aprovacao_ne", "categoria": "fixo_inicial", "ordem": 50,
            "origem": "gerado", "modo": "interno", "ativo": True,
            "aplica_a": ["DMPP", "UFIEC"],
            "deteccao": None,
            "processor": "despacho_gerado",
            "config_doc": {
                "busca": "Despacho",
                "descricao": "Aprovação de NE",
                "nome_arvore": "Aprovação de NE",
            },
            "gerado_config": {
                "template": (
                    "Aprova-se Nota de Empenho {numero_ne}, documento: {link_ne}\n\n"
                    "São Paulo, {data_ne}\n\n"
                    "WILLIAN DE OLIVEIRA SALAZAR\n"
                    "Coordenador de Departamento de Orçamento e Finanças – COF"
                ),
                "campos": [
                    {"nome": "numero_ne", "fonte": "contexto", "chave": "ne_numero"},
                    {"nome": "data_ne", "fonte": "contexto", "chave": "ne_data"},
                ],
                "captura_link": True,
                "link_step_alvo": "nota_empenho",
                # Coordenadas calibradas manualmente (uma por tipo de
                # processo, porque a árvore tem profundidades diferentes).
                "coord_icone_arvore": {
                    "DMPP": [49, 246],
                    "UFIEC": [48, 304],
                },
            },
        },
        {
            "id": "ordem_bancaria", "categoria": "fixo_inicial", "ordem": 60,
            "origem": "arquivo", "modo": "externo", "ativo": True,
            "aplica_a": ["DMPP", "UFIEC"],
            "deteccao": {"contains_all": ["ordem", "banc"]},
            "processor": "ordem_bancaria",
            "config_doc": {"busca": "Externo", "tipo_externo": "Ordem bancaria"},
        },

        # ---------------- CICLO (por Nota Fiscal) ----------------
        {
            "id": "quadro_comparativo", "categoria": "ciclo", "ordem": 10,
            "origem": "arquivo", "modo": "interno", "ativo": True,
            "aplica_a": ["DMPP", "UFIEC"],
            "ancora_ciclo": True,
            "deteccao": {"contains_any": ["quadro", "planilha", "comparativ"]},
            "processor": "quadro_comparativo",
            "config_doc": {
                "busca": "Planilha",
                "descricao": "Quadro comparativo",
                "nome_arvore": "Quadro comparativo",
            },
            "processor_config": {
                "assinaturas": [
                    ["RODRIGO BARBIERI", "230599118-51"],
                    ["ROSANA METZNER", "066313968-67"],
                ],
            },
        },
        {
            "id": "nota_fiscal", "categoria": "ciclo", "ordem": 20,
            "origem": "arquivo", "modo": "externo", "ativo": True,
            "aplica_a": ["DMPP", "UFIEC"],
            "deteccao": {"contains_any": ["nota fiscal", "nf "]},
            "processor": "nota_fiscal",
            "config_doc": {"busca": "Externo", "tipo_externo": "Nota Fiscal"},
        },
        {
            "id": "comprovante_fiscal", "categoria": "ciclo", "ordem": 30,
            "origem": "arquivo", "modo": "externo", "ativo": True,
            "aplica_a": ["DMPP", "UFIEC"],
            "deteccao": {"contains_any": ["comprovante"]},
            "processor": "comprovante_fiscal",
            "config_doc": {"busca": "Externo", "tipo_externo": "Comprovante"},
        },
        {
            "id": "declaracao_recebimento", "categoria": "ciclo", "ordem": 40,
            "origem": "arquivo", "modo": "interno", "ativo": True,
            "aplica_a": ["DMPP", "UFIEC"],
            "deteccao": {"contains_all": ["declara", "recebimento"]},
            "processor": "declaracao_recebimento",
            "config_doc": {
                "busca": "Declaracao",
                "descricao": "Declaração de Recebimento, Conformidade e Destinação",
            },
        },
        {
            "id": "consulta_optante", "categoria": "ciclo", "ordem": 50,
            "origem": "arquivo", "modo": "externo", "ativo": True,
            "aplica_a": ["DMPP", "UFIEC"],
            "deteccao": {"contains_any": ["consulta", "optante"]},
            "processor": "consulta_optante",
            "config_doc": {"busca": "Externo", "tipo_externo": "Consulta"},
        },
        {
            "id": "cnpj", "categoria": "ciclo", "ordem": 60,
            "origem": "arquivo", "modo": "externo", "ativo": True,
            "aplica_a": ["DMPP", "UFIEC"],
            "deteccao": {"contains_any": ["cnpj", "cadastro"]},
            "processor": "cnpj",
            "config_doc": {"busca": "Externo", "tipo_externo": "Cadastro Nacional De Pessoa Jurídica"},
        },
        {
            "id": "guia_iss", "categoria": "ciclo", "ordem": 70,
            "origem": "arquivo", "modo": "externo", "ativo": True,
            "aplica_a": ["DMPP", "UFIEC"],
            "deteccao": {"contains_all": ["iss"]},
            "processor": "guia_iss",
            "config_doc": {"busca": "Externo", "tipo_externo": "Guia de recolhimento"},
        },
        {
            "id": "comprovante_iss", "categoria": "ciclo", "ordem": 80,
            "origem": "arquivo", "modo": "externo", "ativo": True,
            "aplica_a": ["DMPP", "UFIEC"],
            "deteccao": {"contains_all": ["iss", "comprovante"]},
            "processor": "comprovante_iss",
            "config_doc": {"busca": "Externo", "tipo_externo": "Comprovante"},
        },

        # ---------------- FIXOS FINAIS ----------------
        {
            "id": "balancete", "categoria": "fixo_final", "ordem": 10,
            "origem": "arquivo", "modo": "interno", "ativo": True,
            "aplica_a": ["DMPP", "UFIEC"],
            "deteccao": {"contains_any": ["balancete"]},
            "processor": "imagem_pdf_padrao",
            "config_doc": {"busca": "Balancete", "descricao": "", "nome_arvore": ""},
        },
        {
            "id": "extrato_bancario", "categoria": "fixo_final", "ordem": 20,
            "origem": "arquivo", "modo": "externo", "ativo": True,
            "aplica_a": ["DMPP", "UFIEC"],
            "deteccao": {"contains_any": ["extrato"]},
            "processor": "extrato_bancario",
            "config_doc": {"busca": "Externo", "tipo_externo": "Extrato", "nome_arvore_fixo": "Bancário"},
        },
        {
            "id": "conciliacao_contabil", "categoria": "fixo_final", "ordem": 30,
            "origem": "arquivo", "modo": "interno", "ativo": True,
            "aplica_a": ["DMPP", "UFIEC"],
            "deteccao": {"contains_any": ["concilia"]},
            "processor": "imagem_pdf_padrao",
            "config_doc": {
                "busca": "Conciliacao",
                "descricao": "Conciliação bancária",
                "nome_arvore": "Conciliação bancária",
            },
        },
        {
            "id": "declaracao_encerramento", "categoria": "fixo_final", "ordem": 40,
            "origem": "arquivo", "modo": "interno", "ativo": True,
            "aplica_a": ["DMPP", "UFIEC"],
            "deteccao": {"contains_all": ["declara", "encerramento"]},
            "processor": "imagem_pdf_padrao",
            "config_doc": {
                "busca": "Declaracao",
                "descricao": "Declaração de encerramento",
                "nome_arvore": "Encerramento",
            },
        },
    ]


# =====================================================================
# CARREGAR / SALVAR (pipeline_config.json)
# =====================================================================

def _path_pipeline(base_dir):
    return Path(base_dir) / NOME_ARQUIVO_PIPELINE


def carregar_pipeline(base_dir):
    """Lê pipeline_config.json; se não existir, retorna o padrão (cópia)."""
    p = _path_pipeline(base_dir)
    if not p.exists():
        return _pipeline_padrao()
    try:
        with open(p, "r", encoding="utf-8") as f:
            passos = json.load(f)
        if not isinstance(passos, list) or not passos:
            raise ValueError("pipeline_config.json vazio ou em formato inválido")
        return passos
    except (json.JSONDecodeError, OSError, ValueError) as e:
        print(f"[pipeline] Erro ao ler {p}: {e} — usando pipeline padrão")
        return _pipeline_padrao()


def salvar_pipeline(base_dir, passos):
    erros = validar_pipeline(passos)
    if erros:
        raise ValueError("Pipeline inválido:\n" + "\n".join(erros))
    p = _path_pipeline(base_dir)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(passos, f, indent=2, ensure_ascii=False)


def restaurar_pipeline_padrao(base_dir):
    p = _path_pipeline(base_dir)
    if p.exists():
        os.remove(p)


def pipeline_customizado(base_dir):
    """True se existir um pipeline_config.json (usuário já editou o pipeline)."""
    return _path_pipeline(base_dir).exists()


def novo_passo_id(prefixo, passos):
    """Gera um id único (slug) a partir de um prefixo (ex: nome digitado)."""
    slug = re.sub(r"[^a-z0-9_]+", "_", prefixo.strip().lower()).strip("_") or "passo"
    ids_existentes = {p["id"] for p in passos}
    candidato = slug
    i = 2
    while candidato in ids_existentes:
        candidato = f"{slug}_{i}"
        i += 1
    return candidato


# =====================================================================
# VALIDAÇÃO
# =====================================================================

def validar_pipeline(passos):
    """Retorna lista de mensagens de erro (vazia = válido)."""
    erros = []
    ids = [p.get("id") for p in passos]
    if len(ids) != len(set(ids)):
        erros.append("Há ids de passo duplicados.")

    for p in passos:
        if p.get("categoria") not in CATEGORIAS:
            erros.append(f"'{p.get('id')}': categoria inválida.")
        if p.get("origem") not in ("arquivo", "gerado"):
            erros.append(f"'{p.get('id')}': origem inválida.")
        if p.get("origem") == "gerado" and p.get("categoria") == "ciclo":
            gc = p.get("gerado_config") or {}
            if gc.get("captura_link"):
                erros.append(
                    f"'{p.get('id')}': captura de link não é suportada em passos "
                    "GERADOS de categoria 'ciclo' (a posição do item na árvore muda "
                    "a cada ciclo — não dá pra calibrar uma coordenada fixa com "
                    "segurança). Desative 'captura_link' ou mude a categoria."
                )

    return erros


# =====================================================================
# CLASSIFICAÇÃO DE ARQUIVOS
# =====================================================================

def _bate_deteccao(nome_lower, regra):
    if not regra:
        return False
    if "contains_all" in regra:
        if not all(kw.lower() in nome_lower for kw in regra["contains_all"]):
            return False
    if "contains_any" in regra:
        if not any(kw.lower() in nome_lower for kw in regra["contains_any"]):
            return False
    # Se só contains_all foi dado (sem contains_any), já retornou True acima
    return "contains_all" in regra or "contains_any" in regra


# ---- Detecção "legada" dos tipos de ciclo — portada quase literalmente
# da função identificar_tipo_documento_ciclo() original, mantida à parte
# da detecção declarativa por ser mais robusta pros 8 tipos já testados
# em produção (inclusive os dois casos de ARQUIVO COMBINADO: nota fiscal
# + comprovante no mesmo PDF, e guia ISS + comprovante no mesmo PDF).
def _classificar_ciclo_legado(nome):
    nome = nome.lower()

    if 'iss' in nome:
        pos_iss = nome.find('iss')
        pos_comp = nome.find('comprovante')
        if pos_comp != -1 and pos_comp < pos_iss:
            return ['comprovante_iss']
        elif 'comprovante' in nome:
            return ['guia_iss', 'comprovante_iss']  # arquivo combinado
        else:
            return ['guia_iss']

    if 'quadro' in nome or 'planilha' in nome or 'comparativo' in nome:
        return ['quadro_comparativo']

    pos_nf = nome.find('nota fiscal') if 'nota fiscal' in nome else (
        nome.find('nf ') if 'nf ' in nome else (
            nome.find('nf-') if 'nf-' in nome else -1))
    pos_comp = nome.find('comprovante') if 'comprovante' in nome else -1

    if pos_nf != -1 and pos_comp != -1:
        if pos_comp < pos_nf:
            return ['comprovante_fiscal']
        else:
            return ['nota_fiscal', 'comprovante_fiscal']  # arquivo combinado
    if pos_nf != -1:
        return ['nota_fiscal']
    if pos_comp != -1:
        return ['comprovante_fiscal']

    if ('declaracao' in nome or 'declaração' in nome or nome.endswith('.docx')) and 'encerramento' not in nome:
        return ['declaracao_recebimento']
    if 'cnpj' in nome or 'cadastro' in nome:
        return ['cnpj']
    if 'consulta' in nome or 'optante' in nome:
        return ['consulta_optante']

    return None


def classificar_arquivo(nome, tipo_processo, passos):
    """
    Retorna uma lista de step-ids para o arquivo `nome` (normalmente 1,
    mas pode ser 2 no caso de arquivo combinado NF+comprovante ou
    guia ISS+comprovante), ou None se nenhum passo ATIVO reconhecer o
    arquivo.

    Só considera passos com origem='arquivo' e aplica_a compatível com
    tipo_processo.
    """
    candidatos = {
        p["id"]: p for p in passos
        if p.get("origem") == "arquivo"
        and p.get("ativo", True)
        and tipo_processo in p.get("aplica_a", ["DMPP", "UFIEC"])
    }

    # 1) tenta a detecção legada de ciclo primeiro (mais testada)
    legado = _classificar_ciclo_legado(nome)
    if legado:
        ids_validos = [i for i in legado if i in candidatos]
        if ids_validos:
            return ids_validos

    # 2) fallback declarativo — cobre tipos fixos e tipos novos
    #    adicionados pelo usuário sem lógica bespoke.
    nome_lower = nome.lower()
    for step_id, p in candidatos.items():
        if _bate_deteccao(nome_lower, p.get("deteccao")):
            return [step_id]

    return None


def listar_e_classificar(pasta_documentos, base_dir, tipo_processo, passos=None):
    """
    Lê a pasta, ordena pelo número (com desempate via doc_ordem quando
    houver conflito resolvido) e classifica cada arquivo.

    Returns:
        (classificados, nao_classificados)
        classificados: list[dict] — {"nome", "caminho", "step_ids"}
        nao_classificados: list[str] — nomes que não bateram com nada
    """
    if passos is None:
        passos = carregar_pipeline(base_dir)

    cache_ordem = doc_ordem.carregar_ordem_manual(base_dir)
    nomes = sorted(
        doc_ordem.listar_documentos(pasta_documentos),
        key=lambda n: doc_ordem.chave_ordenacao(n, base_dir, cache_ordem),
    )

    classificados = []
    nao_classificados = []
    for nome in nomes:
        step_ids = classificar_arquivo(nome, tipo_processo, passos)
        caminho = os.path.join(pasta_documentos, nome)
        if step_ids is None:
            nao_classificados.append(nome)
        else:
            classificados.append({"nome": nome, "caminho": caminho, "step_ids": step_ids})

    return classificados, nao_classificados


def nao_classificados(pasta_documentos, base_dir, tipo_processo, passos=None):
    """Atalho: só a lista de arquivos que não bateram com nenhum tipo ativo."""
    _, faltantes = listar_e_classificar(pasta_documentos, base_dir, tipo_processo, passos)
    return faltantes


# =====================================================================
# MONTAGEM DA SEQUÊNCIA DE EXECUÇÃO
# =====================================================================

def _passos_por_categoria(passos, categoria, tipo_processo):
    ativos = [
        p for p in passos
        if p["categoria"] == categoria
        and p.get("ativo", True)
        and tipo_processo in p.get("aplica_a", ["DMPP", "UFIEC"])
    ]
    return sorted(ativos, key=lambda p: p.get("ordem", 0))


def _agrupar_ciclos(itens_ciclo, passos_ciclo):
    """
    itens_ciclo: list[dict] {"nome","caminho","step_ids"} já filtrados
    pra categoria='ciclo', na ordem dos arquivos (numeração).

    Agrupa em ciclos usando o(s) passo(s) marcado(s) como ancora_ciclo.
    Se a âncora configurada não aparecer em nenhum arquivo (ex: foi
    desativada e a pasta não tem esse tipo), cai automaticamente para
    detecção por REPETIÇÃO: um tipo que já apareceu no ciclo atual
    sinaliza que um novo ciclo começou.
    """
    ids_ancora = {p["id"] for p in passos_ciclo if p.get("ancora_ciclo")}

    ciclos = []
    ciclo_atual = []
    tipos_no_ciclo_atual = set()

    usa_ancora = bool(ids_ancora) and any(
        ids_ancora & set(item["step_ids"]) for item in itens_ciclo
    )
    if not usa_ancora and itens_ciclo:
        print("  ℹ️ Nenhum arquivo do tipo-âncora encontrado — agrupando ciclos "
              "por repetição de tipo (funciona, mas é menos confiável; considere "
              "reativar um tipo-âncora se possível).")

    for item in itens_ciclo:
        eh_ancora = usa_ancora and (ids_ancora & set(item["step_ids"]))
        eh_repeticao = (not usa_ancora) and any(sid in tipos_no_ciclo_atual for sid in item["step_ids"])
        eh_primeiro_item = not ciclos and not ciclo_atual

        if eh_ancora or eh_repeticao or eh_primeiro_item:
            if ciclo_atual:
                ciclos.append(ciclo_atual)
            ciclo_atual = [item]
            tipos_no_ciclo_atual = set(item["step_ids"])
        else:
            if not ciclo_atual:
                print(f"  ⚠️ Arquivo antes do início do primeiro ciclo, ignorando: {item['nome']}")
                continue
            ciclo_atual.append(item)
            tipos_no_ciclo_atual.update(item["step_ids"])

    if ciclo_atual:
        ciclos.append(ciclo_atual)

    return ciclos


def montar_tarefas(pasta_documentos, base_dir, tipo_processo, passos=None):
    """
    Monta a lista FINAL e ORDENADA de tarefas a executar, já
    interleaving arquivos + passos gerados, respeitando 'ordem' e
    'ativo' de cada categoria.

    Cada tarefa: {
        "step": <dict do passo>,
        "arquivo": <caminho ou None>,
        "numero_ciclo": <int ou None>,
    }
    """
    if passos is None:
        passos = carregar_pipeline(base_dir)

    erros = validar_pipeline(passos)
    if erros:
        raise ValueError("Pipeline inválido:\n" + "\n".join(erros))

    classificados, faltantes = listar_e_classificar(pasta_documentos, base_dir, tipo_processo, passos)
    if faltantes:
        print("\n⚠️ Arquivos não reconhecidos por nenhum tipo ativo (ignorados):")
        for nome in faltantes:
            print(f"   - {nome}")

    por_id = {p["id"]: p for p in passos}

    def arquivo_para(step_id, pool):
        for item in pool:
            if step_id in item["step_ids"]:
                return item
        return None

    tarefas = []

    # ---------------- FIXO INICIAL ----------------
    passos_fi = _passos_por_categoria(passos, "fixo_inicial", tipo_processo)
    itens_fi = [c for c in classificados if any(
        s in [p["id"] for p in passos_fi] for s in c["step_ids"])]
    usados = set()
    for step in passos_fi:
        if step["origem"] == "gerado":
            tarefas.append({"step": step, "arquivo": None, "numero_ciclo": None})
            continue
        item = arquivo_para(step["id"], itens_fi)
        if item and id(item) not in usados:
            tarefas.append({"step": step, "arquivo": item["caminho"], "numero_ciclo": None})
            usados.add(id(item))

    # ---------------- CICLO ----------------
    passos_ciclo = _passos_por_categoria(passos, "ciclo", tipo_processo)
    ids_ciclo = {p["id"] for p in passos_ciclo}
    itens_ciclo = [c for c in classificados if set(c["step_ids"]) & ids_ciclo]
    ciclos = _agrupar_ciclos(itens_ciclo, passos_ciclo)

    for n_ciclo, ciclo in enumerate(ciclos, start=1):
        for step in passos_ciclo:
            if step["origem"] == "gerado":
                tarefas.append({"step": step, "arquivo": None, "numero_ciclo": n_ciclo})
                continue
            item = arquivo_para(step["id"], ciclo)
            if item:
                tarefas.append({"step": step, "arquivo": item["caminho"], "numero_ciclo": n_ciclo})

    # ---------------- FIXO FINAL ----------------
    passos_ff = _passos_por_categoria(passos, "fixo_final", tipo_processo)
    itens_ff = [c for c in classificados if any(
        s in [p["id"] for p in passos_ff] for s in c["step_ids"])]
    for step in passos_ff:
        if step["origem"] == "gerado":
            tarefas.append({"step": step, "arquivo": None, "numero_ciclo": None})
            continue
        item = arquivo_para(step["id"], itens_ff)
        if item:
            tarefas.append({"step": step, "arquivo": item["caminho"], "numero_ciclo": None})

    return tarefas
