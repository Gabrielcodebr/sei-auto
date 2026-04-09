"""
Gerenciador de configurações do usuário.

Lê/grava user_config.json (arquivo de overrides) e aplica os valores
sobre o módulo config.py sem alterar seus defaults originais.

Chamado em main_gui.py ANTES de importar sei_automation, para garantir
que a automação use os valores editados na GUI.
"""

import json
import os
from pathlib import Path

# Caminho do arquivo de overrides (na raiz do projeto, junto com config.py)
_BASE_DIR = Path(__file__).resolve().parent.parent
USER_CONFIG_PATH = _BASE_DIR / "user_config.json"

# Chaves que podem ser sobrescritas pelo usuário.
# (Nome do atributo em config.py, tipo esperado)
OVERRIDABLE_KEYS = [
    # Caminhos
    "TESSERACT_PATH",
    "DOCUMENTOS_DIR",
    # OCR
    "OCR_LANGUAGE",
    "OCR_MIN_CONFIDENCE",
    "PDF_DPI",
    "IMAGE_FORMAT",
    # Coordenadas
    "COORD_BTN_INCLUIR_DOC",
    "COORD_BARRA_PESQUISA",
    "COORD_BTN_SALVAR_FORM",
    "COORD_AREA_EDICAO",
    "COORD_ICONE_NE_ARVORE_DMPP",
    "COORD_ICONE_NE_ARVORE_UFIEC",
    "COORD_CAMPO_DESCRICAO_INTERNO",
    "COORD_CAMPO_NOME_ARVORE_INTERNO",
    "COORD_RADIO_PUBLICO",
    "COORD_DROPDOWN_TIPO_EXTERNO",
    "COORD_CAMPO_DATA",
    "COORD_CAMPO_NUMERO",
    "COORD_CAMPO_NOME_ARVORE",
    "COORD_RADIO_NATO_DIGITAL",
    "COORD_RADIO_DIGITALIZADO",
    "COORD_DROPDOWN_TIPO_CONFERENCIA",
    "COORD_BTN_ANEXAR_ARQUIVO",
    "COORD_RADIO_PUBLICO_EXTERNO",
    "REGIAO_POPUP_SIMILAR",
    "COORD_POPUP_OK_SIMILAR",
    "COORD_REFOCO_EDITOR",
    # Tempos
    "PAUSE_BETWEEN_ACTIONS",
    "WAIT_FOR_ELEMENT",
    "MAX_UPLOAD_WAIT",
    "TEMPOS",
    # Documentos & textos
    "DOCUMENTOS",
    "ASSINATURAS_PLANILHA_PRECO",
    "DESPACHO_APROVACAO_TEMPLATE",
]


def _load_json():
    """Lê o arquivo user_config.json se existir, senão retorna dict vazio."""
    if not USER_CONFIG_PATH.exists():
        return {}
    try:
        with open(USER_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"[config_manager] Erro ao ler {USER_CONFIG_PATH}: {e}")
        return {}


def _normalize_value(key, value):
    """Converte listas JSON em tuplas quando o config original usa tupla."""
    coord_keys = {k for k in OVERRIDABLE_KEYS if k.startswith("COORD_") or k == "REGIAO_POPUP_SIMILAR"}
    if key in coord_keys and isinstance(value, list):
        return tuple(value)
    if key == "ASSINATURAS_PLANILHA_PRECO" and isinstance(value, list):
        return [tuple(item) if isinstance(item, list) else item for item in value]
    return value


def _apply_overrides(config_globals):
    """Aplica os overrides no dict globals() do config.py.

    Chamado no final do config.py dentro de um try/except.
    """
    overrides = _load_json()
    if not overrides:
        return
    for key, value in overrides.items():
        if key not in OVERRIDABLE_KEYS:
            continue
        config_globals[key] = _normalize_value(key, value)


def load_user_config():
    """Aplica overrides no módulo config já importado.

    Chamado por main_gui.py antes de importar sei_automation.
    """
    import config
    overrides = _load_json()
    if not overrides:
        return
    for key, value in overrides.items():
        if key not in OVERRIDABLE_KEYS:
            continue
        setattr(config, key, _normalize_value(key, value))


def get_current_config():
    """Retorna um dict com todos os valores atuais (defaults + overrides aplicados)."""
    import config
    result = {}
    for key in OVERRIDABLE_KEYS:
        if hasattr(config, key):
            result[key] = getattr(config, key)
    return result


def save_user_config(values: dict):
    """Grava dict de valores no user_config.json.

    Tuplas são convertidas para listas (JSON-friendly).
    """
    serializable = {}
    for key, value in values.items():
        if key not in OVERRIDABLE_KEYS:
            continue
        serializable[key] = _to_json_safe(value)

    with open(USER_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(serializable, f, indent=2, ensure_ascii=False)


def _to_json_safe(value):
    if isinstance(value, tuple):
        return [_to_json_safe(v) for v in value]
    if isinstance(value, list):
        return [_to_json_safe(v) for v in value]
    if isinstance(value, dict):
        return {k: _to_json_safe(v) for k, v in value.items()}
    return value


def reset_to_defaults():
    """Apaga o user_config.json (volta aos defaults do config.py)."""
    if USER_CONFIG_PATH.exists():
        os.remove(USER_CONFIG_PATH)


def user_config_exists():
    return USER_CONFIG_PATH.exists()
