"""
QThread que roda SEIAutomation.executar() fora da thread da GUI.

- Redireciona stdout/stderr para um LogStream (signal line(str)).
- Faz monkey-patch em aguardar() da instância: antes de cada sleep
  checa stop_controller.should_stop e levanta KeyboardInterrupt.
- Emite signals para a GUI reagir (log, status, término).
"""

import time
import traceback
from PySide6.QtCore import QThread, Signal

from gui.log_stream import LogStream, StdoutRedirector
from gui.stop_controller import stop_controller


class AutomationWorker(QThread):
    log_line = Signal(str)
    finished_ok = Signal()
    finished_error = Signal(str)
    stopped_by_user = Signal()

    def __init__(self, opcoes: dict, parent=None):
        """
        Args:
            opcoes: dict com chaves:
                - tipo_processo ('DMPP' ou 'UFIEC')
                - pular_docs_fixos (bool)
                - ciclo_inicial (int)
                - arquivo_inicial (int ou None)
        """
        super().__init__(parent)
        self.opcoes = opcoes
        self.log_stream = LogStream()
        self.log_stream.line.connect(self.log_line)

    def run(self):
        stop_controller.reset()

        # Import tardio: garante que os overrides do user_config.json
        # já foram aplicados antes de a automação ler as coordenadas.
        try:
            import sei_automation
        except Exception as e:
            self.finished_error.emit(f"Falha ao importar sei_automation: {e}")
            return

        with StdoutRedirector(self.log_stream):
            try:
                automacao = sei_automation.SEIAutomation(
                    pular_docs_fixos=self.opcoes.get("pular_docs_fixos", False),
                    ciclo_inicial=self.opcoes.get("ciclo_inicial", 1),
                    arquivo_inicial=self.opcoes.get("arquivo_inicial"),
                    tipo_processo=self.opcoes.get("tipo_processo", "DMPP"),
                )

                # Monkey-patch: checa flag de parada antes de cada sleep
                self._inject_stop_check(automacao)

                sucesso = automacao.executar()

                if stop_controller.should_stop:
                    self.stopped_by_user.emit()
                elif sucesso:
                    self.finished_ok.emit()
                else:
                    self.finished_error.emit("A automação terminou com erros (ver log).")

            except KeyboardInterrupt:
                self.stopped_by_user.emit()
            except Exception as e:
                tb = traceback.format_exc()
                print(tb)
                self.finished_error.emit(str(e))

    def _inject_stop_check(self, automacao):
        """Substitui o método aguardar() da instância por uma versão
        que verifica stop_controller.should_stop antes do sleep."""
        import config

        def aguardar_com_checkpoint(segundos=None):
            if stop_controller.should_stop:
                raise KeyboardInterrupt()
            if segundos is None:
                segundos = config.WAIT_FOR_ELEMENT
            # Divide o sleep em pedaços pequenos para reagir rapidamente
            step = 0.1
            remaining = float(segundos)
            while remaining > 0:
                if stop_controller.should_stop:
                    raise KeyboardInterrupt()
                time.sleep(min(step, remaining))
                remaining -= step

        # Bind ao instance
        import types
        automacao.aguardar = types.MethodType(
            lambda self, segundos=None: aguardar_com_checkpoint(segundos),
            automacao,
        )
