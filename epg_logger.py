"""
Módulo de logging com barra de progresso e estatísticas
"""

import linecache
import math
import shutil
import sys
import traceback
from pathlib import Path
from datetime import datetime
from typing import Optional
import time

class Colors:
    RESET = "\033[0m"

    BG_COLOR = "\033[48;2;30;30;46m"

    LINE_COLOR = "\033[38;2;54;54;84m"
    EMPTY_COLOR = "\033[38;2;74;74;104m"

    PRIMARY_TEXT_COLOR = "\033[38;2;205;214;244m"
    SECONDARY_TEXT_COLOR = "\033[38;2;245;237;194m"
    HIGHLIGHT_TEXT_COLOR = "\033[38;2;148;226;213m"
    UNHIGHLIGHT_TEXT_COLOR = "\033[38;2;162;169;193m"


class ProgressLogger:
    """
    Logger com barra de progresso customizável para acompanhamento de processos iterativos.
    Suporta múltiplas barras simultâneas.
    """

    # Gerenciador de múltiplas barras
    _active_loggers = []
    _terminal_lines = 0

    def __init__(
        self,
        title="Processo",
        total=100,
        bar_char="─",
        empty_char="—",
        size=0,
        log_path: Path = "log_epg.log",
    ):
        """
        Inicializa o logger de progresso.

        Args:
            title (str): Título da barra de progresso
            total (int): Quantidade total de itens a processar
            bar_length (int): Comprimento da barra em caracteres
            bar_char (str): Caractere para parte preenchida da barra
            empty_char (str): Caractere para parte vazia da barra
            color (str): Cor da barra ('red', 'green', 'yellow', 'blue', 'magenta', 'cyan')
        """
        self.title = title
        self.total = total
        self.current = 0
        self.bar_length = shutil.get_terminal_size().columns - size - 60
        self.bar_char = bar_char
        self.empty_char = empty_char
        self.start_time = None
        self.end_time = None
        self.is_complete = False
        self.position = -1
        self.size = size
        self.log_path = Path(log_path)

    def start(self):
        """Inicia o contador de tempo e registra a barra."""
        self.start_time = time.time()
        self.current = 0
        self.is_complete = False
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Adiciona à lista de loggers ativos
        if self not in ProgressLogger._active_loggers:
            ProgressLogger._active_loggers.append(self)
            self.position = len(ProgressLogger._active_loggers) - 1

        self._display_all()

        # Log em arquivo
        msg = f"\n{'='*80}\nInício: {timestamp}\n{'='*80}\n"
        #self._write(msg + "\n")

        return self

    def update(self, step=1):
        """
        Atualiza o progresso e exibe a barra.

        Args:
            step (int): Quantidade de itens a incrementar
        """
        if not self.start_time:
            self.start()

        self.current += step

        # Garante que não ultrapasse o total
        if self.current > self.total:
            self.current = self.total

        self._display_all()

        # Verifica se completou
        if self.current >= self.total and not self.is_complete:
            self.complete()

    def _get_progress_line(self):
        """Retorna a linha de progresso formatada."""
        percentage = (self.current / self.total) * 100 if self.total > 0 else 0
        filled_length = (
            int(self.bar_length * self.current / self.total) if self.total > 0 else 0
        )

        bar = (
            self.bar_char * filled_length
            + Colors.EMPTY_COLOR
            + self.empty_char * (self.bar_length - filled_length)
        )

        self.title = self._adjust_text_size(self.title, self.size)
        space = " " * max((13 - len(str(self.total)) * 2), 0)

        if self.is_complete:
            elapsed_time = self.end_time - self.start_time
            rate = self.total / elapsed_time if elapsed_time > 0 else 0
            return f"    {Colors.UNHIGHLIGHT_TEXT_COLOR}{self.title}  {Colors.HIGHLIGHT_TEXT_COLOR}{bar}{Colors.PRIMARY_TEXT_COLOR} • {percentage:.0f}% • {self.total}/{self.total}{space}{Colors.UNHIGHLIGHT_TEXT_COLOR}{rate:.2f} itens/seg"
        else:
            return f"    {Colors.UNHIGHLIGHT_TEXT_COLOR}{self.title}  {Colors.SECONDARY_TEXT_COLOR}{bar}{Colors.PRIMARY_TEXT_COLOR} • {percentage:.0f}% •  {Colors.HIGHLIGHT_TEXT_COLOR}{self.current}/{Colors.PRIMARY_TEXT_COLOR}{self.total} programas encontrados"

    #def _write(self, message: str):
        #"""Escreve no arquivo de log"""
        #try:
        #    with open(self.log_path, "a", encoding="utf-8") as f:
        #        f.write(message)
        #except Exception as e:
        #    print(f"Erro ao escrever log: {e}")

    @classmethod
    def _display_all(cls):
        """Exibe todas as barras ativas."""
        if not cls._active_loggers:
            return

        # Move cursor para o início das barras
        if cls._terminal_lines > 0:
            sys.stdout.write(f"\033[{cls._terminal_lines}A")

        # Limpa e reescreve todas as linhas
        for logger in cls._active_loggers:
            line = logger._get_progress_line()
            # Limpa a linha e escreve
            sys.stdout.write("\033[K" + line + "\n")

        cls._terminal_lines = len(cls._active_loggers)
        sys.stdout.flush()

    def complete(self):
        """Finaliza a barra de progresso e exibe a taxa de processamento."""
        if self.is_complete:
            return

        self.end_time = time.time()
        self.is_complete = True

        self._display_all()

    def remove(self):
        """Remove a barra da exibição."""
        if self in ProgressLogger._active_loggers:
            ProgressLogger._active_loggers.remove(self)
            self._display_all()

    def set_title(self, title):
        """
        Altera o título da barra de progresso.

        Args:
            title (str): Novo título
        """
        self.title = title

    def _adjust_text_size(self, text, size):
        if text == None:
            return " " * size

        text = text[:size]
        return text.ljust(size)

    @classmethod
    def clear_all(cls):
        """Limpa todas as barras ativas."""
        cls._active_loggers.clear()
        cls._terminal_lines = 0

    def __enter__(self):
        """Suporte para context manager."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Finaliza automaticamente ao sair do context manager."""
        if not self.is_complete:
            self.complete()


class EPGLogger:
    """Logger com barra de progresso e estatísticas detalhadas"""

    def __init__(self):
        self.start_time = None

    #def _write(self, message: str):
    #    """Escreve no arquivo de log"""
        #try:
        #    with open(self.log_path, "a", encoding="utf-8") as f:
        #        f.write(message)
        #except Exception as e:
        #    print(f"Erro ao escrever log: {e}")

    def log_exception(self, exception: Exception, context: str = ""):
        """
        Registra exceção com traceback e trecho de código

        Args:
            exception: Exceção capturada
            context: Contexto adicional
        """
        self.increment_stat("errors")

        # Extrai informações do traceback
        tb_list = traceback.extract_tb(exception.__traceback__)
        if not tb_list:
            #self._write(f"[ERRO] {context} - {str(exception)}\n")
            return

        last_frame = tb_list[-1]
        file_path = last_frame.filename
        file_name = Path(file_path).name
        line_num = last_frame.lineno
        func_name = last_frame.name

        # Mensagem resumida para console
        short_msg = f"{file_name}:{line_num} em {func_name}() - {type(exception).__name__}: {str(exception)}"
        if context:
            short_msg = f"{context} - {short_msg}"

        print(f"❌ {short_msg}")

        # Extrai código-fonte ao redor do erro
        code_context = self._get_code_context(file_path, line_num, context_lines=3)

        # Log completo para arquivo
        full_msg = f"""

{code_context}
"""
        print(full_msg)

    def _get_code_context(
        self, file_path: str, line_num: int, context_lines: int = 3
    ) -> str:
        """
        Extrai trecho de código ao redor da linha do erro

        Args:
            file_path: Caminho do arquivo
            line_num: Número da linha com erro
            context_lines: Quantas linhas antes/depois mostrar

        Returns:
            String formatada com código
        """
        # Obtém a largura atual do terminal
        cols = shutil.get_terminal_size().columns

        try:
            lines = []
            lines.append(
                f"{Colors.BG_COLOR}{Colors.PRIMARY_TEXT_COLOR}┌"
                + "── Code "
                + ("─" * (cols - 2 - 8))
                + "┐"
            )
            start = max(1, line_num - context_lines)
            end = line_num + context_lines + 1

            for i in range(start, end):
                line = linecache.getline(file_path, i)
                if line:
                    # Marca a linha do erro com indicador
                    if i == line_num:
                        marker = f"│{Colors.SECONDARY_TEXT_COLOR} >>> "
                        new_line = (
                            f"{marker}{i:4d} | {line.rstrip()}"
                            + Colors.PRIMARY_TEXT_COLOR
                            + Colors.BG_COLOR
                        )
                        spaces = max(
                            cols
                            + len(Colors.SECONDARY_TEXT_COLOR)
                            + len(Colors.PRIMARY_TEXT_COLOR)
                            + len(Colors.BG_COLOR)
                            - len(new_line)
                            - 1,
                            0,
                        )
                    else:
                        marker = "│     "
                        new_line = f"{Colors.UNHIGHLIGHT_TEXT_COLOR}{marker}{i:4d} | {line.rstrip()}"
                        spaces = max(
                            cols
                            - len(new_line)
                            + len(Colors.UNHIGHLIGHT_TEXT_COLOR)
                            - 1,
                            0,
                        )

                    lines.append(new_line + (" " * spaces + "│"))

            # Limpa cache do linecache
            linecache.checkcache(file_path)

            lines.append("└" + ("─" * (cols - 2)) + "┘")

            return "\n".join(lines) if lines else "Código fonte não disponível"

        except Exception:
            return "Erro ao ler código fonte"

    def interface_subtitle(self, subtitle: Optional[str]):
        cols = shutil.get_terminal_size().columns

        text_space = 4 if not subtitle else 6
        the_space = "" if not subtitle else " "

        print(f"{Colors.BG_COLOR} " * cols)

        spaces = f"{Colors.BG_COLOR}{Colors.LINE_COLOR}─" * math.floor(
            max(cols - len(subtitle) - text_space, 0) / 2
        )
        adjust = " " * (cols - len(subtitle) - len(spaces) * 2)
        print(
            f"{Colors.BG_COLOR}  {spaces}{the_space}{Colors.BG_COLOR}{Colors.SECONDARY_TEXT_COLOR}{subtitle}{the_space}{spaces}{adjust}  "
        )

        print(f"{Colors.BG_COLOR}{Colors.PRIMARY_TEXT_COLOR} " * cols)

    def interface_item(self, title: str = "", subtitle: str = ""):
        cols = shutil.get_terminal_size().columns

        indent = "    "

        if subtitle:
            output = f"{Colors.BG_COLOR}{Colors.PRIMARY_TEXT_COLOR}{indent}{title}: {Colors.HIGHLIGHT_TEXT_COLOR}{subtitle}"
        else:
            output = f"{Colors.BG_COLOR}{Colors.PRIMARY_TEXT_COLOR}{indent}{title} {Colors.HIGHLIGHT_TEXT_COLOR}{subtitle}"

        space = f"{Colors.BG_COLOR} " * max(
            cols
            + len(Colors.BG_COLOR)
            + len(Colors.PRIMARY_TEXT_COLOR)
            + len(Colors.HIGHLIGHT_TEXT_COLOR)
            - len(output),
            0,
        )
        print(f"{output}{space}")

    def interface_centered_text(
        self, title: str = "", color: str = Colors.PRIMARY_TEXT_COLOR
    ):
        cols = shutil.get_terminal_size().columns

        space = f" " * math.floor(max(cols - len(title), 0) / 2)
        adjust = " " * (cols - len(title) - len(space) * 2)
        line = f"{Colors.BG_COLOR}{color}{space}{title}{space}{adjust}"
        print(line)
