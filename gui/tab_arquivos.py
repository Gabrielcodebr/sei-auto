"""
Aba "Documentos" — lista os arquivos da pasta DOCUMENTOS_DIR
com tipo detectado e tamanho, para conferência antes de executar.

Também permite adicionar arquivos (copia para a pasta) e remover
os selecionados, sem precisar abrir o Explorer.
"""

import os
import re
import shutil
import subprocess
import sys
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QFileDialog
)

import config
import doc_ordem
import pipeline
from gui.dialog_resolver_ordem import DialogResolverOrdem


def _formatar_tamanho(bytes_: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if bytes_ < 1024:
            return f"{bytes_:.1f} {unit}"
        bytes_ /= 1024
    return f"{bytes_:.1f} TB"


def _identificar_tipo(nome: str) -> str:
    """Heurística leve (sem depender de instanciar SEIAutomation)."""
    nome_lower = nome.lower()
    if re.search(r"\bcapa\b", nome_lower):
        return "Capa"
    if "solicita" in nome_lower:
        return "Solicitação"
    if "memorando" in nome_lower or "justificativ" in nome_lower:
        return "Memorando/Justificativa"
    if "nota" in nome_lower and "empenho" in nome_lower:
        return "Nota de Empenho"
    if "despacho" in nome_lower:
        return "Despacho"
    if "ordem" in nome_lower and "banc" in nome_lower:
        return "Ordem Bancária"
    if "quadro" in nome_lower or "comparativ" in nome_lower or "planilha" in nome_lower:
        return "Quadro Comparativo"
    if "nota fiscal" in nome_lower or re.search(r"\bnf\b", nome_lower):
        return "Nota Fiscal"
    if "comprovante" in nome_lower and "iss" in nome_lower:
        return "Comprovante ISS"
    if "iss" in nome_lower and ("guia" in nome_lower or "empresa" in nome_lower):
        return "Guia ISS"
    if "comprovante" in nome_lower:
        return "Comprovante Fiscal"
    if "declara" in nome_lower and "recebimento" in nome_lower:
        return "Declaração de Recebimento"
    if "declara" in nome_lower and "encerramento" in nome_lower:
        return "Declaração de Encerramento"
    if "optante" in nome_lower or "consulta" in nome_lower:
        return "Consulta Optante"
    if "cnpj" in nome_lower:
        return "CNPJ"
    if "balancete" in nome_lower:
        return "Balancete"
    if "extrato" in nome_lower:
        return "Extrato Bancário"
    if "concilia" in nome_lower:
        return "Conciliação Contábil"
    return "—"


class TabArquivos(QWidget):
    """Preview dos documentos na pasta antes de executar."""

    def __init__(self, parent=None, get_tipo_processo=None):
        super().__init__(parent)
        self._grupos_dispensados = set()  # chaves de grupo com "agora não" nesta sessão
        self._get_tipo_processo = get_tipo_processo or (lambda: "DMPP")
        self._build_ui()
        self.reload()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        header = QHBoxLayout()
        self.lbl_path = QLabel()
        self.lbl_path.setStyleSheet("font-weight: bold;")
        header.addWidget(self.lbl_path, 1)

        self.btn_adicionar = QPushButton("➕ Adicionar arquivos…")
        self.btn_adicionar.clicked.connect(self._adicionar_arquivos)
        header.addWidget(self.btn_adicionar)

        self.btn_remover = QPushButton("🗑️ Remover selecionados")
        self.btn_remover.clicked.connect(self._remover_selecionados)
        header.addWidget(self.btn_remover)

        self.btn_abrir = QPushButton("📁 Abrir pasta")
        self.btn_abrir.clicked.connect(self._open_folder)
        header.addWidget(self.btn_abrir)

        self.btn_reload = QPushButton("🔄 Recarregar")
        self.btn_reload.clicked.connect(self.reload)
        header.addWidget(self.btn_reload)

        layout.addLayout(header)

        self.lbl_count = QLabel()
        self.lbl_count.setStyleSheet("color: #555;")
        layout.addWidget(self.lbl_count)

        # Banner de conflito de numeração (some quando não há conflitos)
        banner_row = QHBoxLayout()
        self.banner_conflito = QLabel()
        self.banner_conflito.setWordWrap(True)
        self.banner_conflito.setStyleSheet(
            "background-color: #fdecea; color: #611a15; padding: 8px; "
            "border: 1px solid #f5c6cb; border-radius: 4px;"
        )
        self.banner_conflito.hide()
        banner_row.addWidget(self.banner_conflito, 1)

        self.btn_resolver = QPushButton("⚠️ Resolver ordem")
        self.btn_resolver.clicked.connect(self._resolver_conflitos)
        self.btn_resolver.hide()
        banner_row.addWidget(self.btn_resolver)
        layout.addLayout(banner_row)

        # Banner de arquivos não classificados (nenhum tipo ativo reconhece)
        self.banner_nao_classificados = QLabel()
        self.banner_nao_classificados.setWordWrap(True)
        self.banner_nao_classificados.setStyleSheet(
            "background-color: #fff3cd; color: #664d03; padding: 8px; "
            "border: 1px solid #ffe69c; border-radius: 4px;"
        )
        self.banner_nao_classificados.hide()
        layout.addWidget(self.banner_nao_classificados)

        self.tbl = QTableWidget()
        self.tbl.setColumnCount(4)
        self.tbl.setHorizontalHeaderLabels(["Nº", "Arquivo", "Tipo detectado", "Tamanho"])
        self.tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tbl.setSelectionBehavior(QTableWidget.SelectRows)
        self.tbl.setSelectionMode(QTableWidget.ExtendedSelection)
        layout.addWidget(self.tbl, 1)

    # =========================================================
    # AÇÕES DE ARQUIVO (adicionar / remover)
    # =========================================================

    def _garantir_pasta(self) -> bool:
        """Cria DOCUMENTOS_DIR se não existir. Retorna True se ok."""
        try:
            os.makedirs(config.DOCUMENTOS_DIR, exist_ok=True)
            return True
        except OSError as e:
            QMessageBox.critical(
                self, "Erro",
                f"Não foi possível criar a pasta de documentos:\n"
                f"{config.DOCUMENTOS_DIR}\n\n{e}"
            )
            return False

    def _adicionar_arquivos(self):
        """Copia PDFs/DOCX escolhidos pelo usuário para a pasta de documentos."""
        if not self._garantir_pasta():
            return

        origens, _ = QFileDialog.getOpenFileNames(
            self,
            "Adicionar arquivos à pasta de documentos",
            "",
            "Documentos (*.pdf *.docx);;Todos os arquivos (*.*)",
        )
        if not origens:
            return

        destino_dir = config.DOCUMENTOS_DIR
        novos = []       # (origem, destino) — sem colisão
        colisoes = []    # (origem, destino) — já existe arquivo com mesmo nome

        for origem in origens:
            nome = os.path.basename(origem)
            destino = os.path.join(destino_dir, nome)
            if os.path.exists(destino):
                # Se o arquivo for literalmente o mesmo (mesmo path físico), ignora
                try:
                    if os.path.samefile(origem, destino):
                        continue
                except OSError:
                    pass
                colisoes.append((origem, destino))
            else:
                novos.append((origem, destino))

        pulados = 0
        if colisoes:
            lista = "\n".join(f"  • {os.path.basename(d)}" for _, d in colisoes)
            resp = QMessageBox.question(
                self, "Nomes duplicados",
                f"{len(colisoes)} arquivo(s) já existem na pasta com o mesmo nome:\n\n"
                f"{lista}\n\nDeseja sobrescrever?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                QMessageBox.No,
            )
            if resp == QMessageBox.Cancel:
                return
            if resp == QMessageBox.Yes:
                novos.extend(colisoes)
            else:
                pulados = len(colisoes)

        copiados = 0
        erros = []
        for origem, destino in novos:
            try:
                shutil.copy2(origem, destino)
                copiados += 1
            except OSError as e:
                erros.append(f"{os.path.basename(origem)}: {e}")

        # Novo estado da pasta pode ter novos conflitos — limpa os "dispensados"
        # para dar ao usuário a chance de resolver.
        self._grupos_dispensados.clear()
        self.reload()

        partes = [f"✅ {copiados} arquivo(s) adicionado(s)."]
        if pulados:
            partes.append(f"{pulados} pulado(s) (já existiam).")
        if erros:
            partes.append("\n❌ Erros:\n" + "\n".join(erros))
        QMessageBox.information(self, "Adicionar arquivos", "\n".join(partes))

    def _remover_selecionados(self):
        """Remove do disco os arquivos selecionados na tabela."""
        linhas = sorted({i.row() for i in self.tbl.selectedIndexes()}, reverse=True)
        if not linhas:
            QMessageBox.information(
                self, "Remover arquivos",
                "Selecione um ou mais arquivos na tabela primeiro."
            )
            return

        nomes = [self.tbl.item(r, 1).text() for r in linhas]
        lista = "\n".join(f"  • {n}" for n in nomes)
        resp = QMessageBox.warning(
            self, "Remover arquivos",
            f"Remover {len(nomes)} arquivo(s) da pasta?\n\n{lista}\n\n"
            "Os arquivos serão apagados do disco. Essa ação não pode ser desfeita.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if resp != QMessageBox.Yes:
            return

        erros = []
        removidos = 0
        for nome in nomes:
            caminho = os.path.join(config.DOCUMENTOS_DIR, nome)
            try:
                os.remove(caminho)
                removidos += 1
            except OSError as e:
                erros.append(f"{nome}: {e}")

        self.reload()

        partes = [f"✅ {removidos} arquivo(s) removido(s)."]
        if erros:
            partes.append("\n❌ Erros:\n" + "\n".join(erros))
        QMessageBox.information(self, "Remover arquivos", "\n".join(partes))

    # =========================================================
    # LISTAGEM / CONFERÊNCIA
    # =========================================================

    def reload(self):
        path = config.DOCUMENTOS_DIR
        self.lbl_path.setText(f"Pasta: {path}")

        # Cria silenciosamente se não existir (rede de segurança; o config.py
        # também deve garantir isso na inicialização).
        try:
            os.makedirs(path, exist_ok=True)
        except OSError:
            pass

        if not os.path.isdir(path):
            self.lbl_count.setText("⚠️ Pasta não encontrada.")
            self.tbl.setRowCount(0)
            self.banner_conflito.hide()
            self.btn_resolver.hide()
            self.banner_nao_classificados.hide()
            return

        def chave(nome):
            m = re.match(r"^(\d+)", nome)
            return int(m.group(1)) if m else 9999

        arquivos = sorted(
            [f for f in os.listdir(path) if f.lower().endswith((".pdf", ".docx"))],
            key=chave,
        )

        pendentes = doc_ordem.conflitos_pendentes(path, config.BASE_DIR)
        nomes_em_conflito = {nome for grupo in pendentes for nome in grupo}

        tipo_processo = self._get_tipo_processo()
        try:
            nao_classificados = set(pipeline.nao_classificados(path, config.BASE_DIR, tipo_processo))
        except Exception:
            nao_classificados = set()

        self.tbl.setRowCount(len(arquivos))
        for row, nome in enumerate(arquivos):
            numero = re.match(r"^(\d+)", nome)
            num_str = numero.group(1) if numero else "?"
            full = os.path.join(path, nome)
            size = _formatar_tamanho(os.path.getsize(full))
            tipo = _identificar_tipo(nome)
            if nome in nao_classificados and tipo == "—":
                tipo = "⚠️ não reconhecido"

            valores = (num_str, nome, tipo, size)
            for col, valor in enumerate(valores):
                item = QTableWidgetItem(valor)
                if nome in nomes_em_conflito:
                    item.setBackground(Qt.yellow)
                    item.setToolTip("Número em conflito com outro arquivo — ordem ambígua")
                elif nome in nao_classificados:
                    item.setBackground(Qt.lightGray)
                    item.setToolTip(
                        f"Nenhum tipo ATIVO do pipeline reconhece este arquivo para o "
                        f"processo {tipo_processo}. Ele será ignorado na execução."
                    )
                self.tbl.setItem(row, col, item)

        self.lbl_count.setText(f"📄 {len(arquivos)} arquivo(s) encontrado(s)")

        if nao_classificados:
            self.banner_nao_classificados.setText(
                f"ℹ️ {len(nao_classificados)} arquivo(s) não correspondem a nenhum tipo "
                f"ativo do pipeline para '{tipo_processo}' (em cinza na tabela) — serão "
                "ignorados na execução. Ajuste em Configurações → Pipeline de Documentos "
                "se algum deles deveria ser processado."
            )
            self.banner_nao_classificados.show()
        else:
            self.banner_nao_classificados.hide()

        if not pendentes:
            self.banner_conflito.hide()
            self.btn_resolver.hide()
            return

        self.banner_conflito.setText(
            f"⚠️ {len(pendentes)} conflito(s) de numeração encontrado(s): dois ou "
            "mais arquivos com o mesmo número (destacados em amarelo). A ordem "
            "entre eles é ambígua — resolva antes de executar."
        )
        self.banner_conflito.show()
        self.btn_resolver.show()

        novos = [g for g in pendentes if doc_ordem.chave_grupo(g) not in self._grupos_dispensados]
        if novos:
            resp = QMessageBox.warning(
                self, "Conflito de numeração",
                f"Encontrei {len(novos)} conflito(s) de numeração na pasta de "
                "documentos: arquivos diferentes com o mesmo número, então a "
                "ordem de processamento fica ambígua.\n\n"
                "Quer decidir a ordem agora?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes,
            )
            if resp == QMessageBox.Yes:
                self._resolver_conflitos()
                return  # _resolver_conflitos() já chama reload() de novo
            for g in novos:
                self._grupos_dispensados.add(doc_ordem.chave_grupo(g))

    def _resolver_conflitos(self):
        """Abre o diálogo 'Qual arquivo é primeiro?' para cada conflito pendente."""
        path = config.DOCUMENTOS_DIR
        pendentes = doc_ordem.conflitos_pendentes(path, config.BASE_DIR)
        for grupo in pendentes:
            dlg = DialogResolverOrdem(grupo, self)
            dlg.exec()
        self.reload()

    def _open_folder(self):
        path = config.DOCUMENTOS_DIR
        if not os.path.isdir(path):
            QMessageBox.warning(self, "Pasta não encontrada", path)
            return
        try:
            if sys.platform.startswith("win"):
                os.startfile(path)  # type: ignore
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as e:
            QMessageBox.warning(self, "Erro", str(e))