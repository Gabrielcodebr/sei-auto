"""
Detecção e resolução de conflitos de numeração na pasta de documentos.

Um "conflito" acontece quando dois (ou mais) arquivos começam com o
MESMO número de prefixo — ex: "6-NOTA FISCAL 2420...pdf" e
"6.QUADRO COMPARATIVO DE PREÇOS...pdf". Nesse caso a ordem entre eles
é ambígua: carregar_documentos() ordena só pelo número, então o
desempate dependeria da ordem que o sistema de arquivos devolve (não
confiável), podendo fazer o bot processar a Nota Fiscal como se fosse
o Quadro Comparativo do ciclo (ou vice-versa).

Este módulo NUNCA renomeia arquivos em disco. Em vez disso, guarda a
ordem escolhida pelo usuário em um arquivo separado, ordem_manual.json,
na raiz do projeto (config.BASE_DIR).

Não depende de Qt — pode ser usado tanto pelo core (sei_automation.py)
quanto pela GUI (gui/tab_arquivos.py, gui/dialog_resolver_ordem.py).
"""

import os
import re
import json
from pathlib import Path

NOME_ARQUIVO_ORDEM = "ordem_manual.json"


def _numero_prefixo(nome):
    m = re.match(r'^(\d+)', nome)
    return int(m.group(1)) if m else None


def listar_documentos(pasta_documentos):
    """Lista os nomes (não caminhos completos) dos .pdf/.docx da pasta."""
    if not os.path.isdir(pasta_documentos):
        return []
    return [f for f in os.listdir(pasta_documentos) if f.lower().endswith(('.pdf', '.docx'))]


def detectar_conflitos(pasta_documentos):
    """
    Agrupa os arquivos por número de prefixo e retorna apenas os
    grupos com 2+ arquivos (numeração ambígua).

    Returns:
        list[list[str]] — cada item é uma lista de nomes de arquivo
        (ordenados alfabeticamente) que compartilham o mesmo número.
    """
    grupos = {}
    for nome in listar_documentos(pasta_documentos):
        n = _numero_prefixo(nome)
        if n is None:
            continue
        grupos.setdefault(n, []).append(nome)

    return [sorted(v) for _, v in sorted(grupos.items()) if len(v) > 1]


def chave_grupo(grupo):
    """Chave estável para identificar um grupo de conflito no JSON."""
    return "|".join(sorted(grupo))


def _path_ordem(base_dir):
    return Path(base_dir) / NOME_ARQUIVO_ORDEM


def carregar_ordem_manual(base_dir):
    """Lê ordem_manual.json. Formato: {chave_grupo: [nomes na ordem certa]}."""
    p = _path_ordem(base_dir)
    if not p.exists():
        return {}
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"[doc_ordem] Erro ao ler {p}: {e}")
        return {}


def salvar_ordem_manual(base_dir, ordem):
    p = _path_ordem(base_dir)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(ordem, f, indent=2, ensure_ascii=False)


def resolver_conflito(base_dir, grupo, ordem_escolhida):
    """
    Salva a ordem escolhida pelo usuário para um grupo de arquivos
    conflitantes. NÃO renomeia nada em disco.

    Args:
        base_dir:         pasta onde fica ordem_manual.json (config.BASE_DIR)
        grupo:             lista original de nomes em conflito
        ordem_escolhida:   os mesmos nomes, na ordem correta de processamento
    """
    if sorted(ordem_escolhida) != sorted(grupo):
        raise ValueError("ordem_escolhida precisa conter exatamente os mesmos arquivos do grupo")

    ordem_salva = carregar_ordem_manual(base_dir)
    ordem_salva[chave_grupo(grupo)] = list(ordem_escolhida)
    salvar_ordem_manual(base_dir, ordem_salva)


def conflitos_pendentes(pasta_documentos, base_dir):
    """Conflitos detectados na pasta que AINDA não têm resolução salva."""
    ordem_salva = carregar_ordem_manual(base_dir)
    return [
        grupo for grupo in detectar_conflitos(pasta_documentos)
        if chave_grupo(grupo) not in ordem_salva
    ]


def chave_ordenacao(nome, base_dir, cache_ordem=None):
    """
    Chave de ordenação (numero, desempate, nome) para usar em sorted().

    Usa a resolução manual salva para desempatar arquivos com o mesmo
    número. Se não houver resolução para esse arquivo (conflito ainda
    pendente — o que a validação em SEIAutomation.executar() deveria
    impedir de chegar até aqui), desempata por ordem alfabética.
    """
    n = _numero_prefixo(nome)
    if n is None:
        return (9999, 0, nome)

    if cache_ordem is None:
        cache_ordem = carregar_ordem_manual(base_dir)

    for ordem in cache_ordem.values():
        if nome in ordem:
            return (n, ordem.index(nome), nome)

    return (n, 0, nome)
