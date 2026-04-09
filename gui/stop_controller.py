"""
Controlador de parada da automação.

- Mantém uma flag global `should_stop` lida pelo AutomationWorker entre ações.
- Registra hotkey global F12 (funciona mesmo sem a GUI em foco) usando
  a biblioteca `keyboard`.
- Usado tanto pela mini-janela flutuante (botão STOP) quanto pelo F12.
"""

import threading
from PySide6.QtCore import QObject, Signal

_lock = threading.Lock()


class _StopController(QObject):
    """Singleton Qt-aware com signal para notificar a GUI."""

    stop_requested = Signal()

    def __init__(self):
        super().__init__()
        self._should_stop = False
        self._hotkey_registered = False

    @property
    def should_stop(self) -> bool:
        with _lock:
            return self._should_stop

    def request_stop(self):
        """Sinaliza que a automação deve parar no próximo checkpoint."""
        with _lock:
            if self._should_stop:
                return
            self._should_stop = True
        self.stop_requested.emit()

    def reset(self):
        """Volta a flag para False (antes de iniciar nova execução)."""
        with _lock:
            self._should_stop = False

    def register_hotkey(self, key: str = "f12"):
        """Registra hotkey global (F12 por padrão) que chama request_stop().

        Usa a biblioteca `keyboard`. Se não estiver disponível, falha
        silenciosamente — o botão da mini-janela continua funcionando.
        """
        if self._hotkey_registered:
            return
        try:
            import keyboard  # type: ignore
            keyboard.add_hotkey(key, self.request_stop)
            self._hotkey_registered = True
        except Exception as e:
            print(f"[stop_controller] Não foi possível registrar hotkey {key}: {e}")

    def unregister_hotkey(self):
        if not self._hotkey_registered:
            return
        try:
            import keyboard  # type: ignore
            keyboard.unhook_all_hotkeys()
            self._hotkey_registered = False
        except Exception:
            pass


# Singleton global
stop_controller = _StopController()
