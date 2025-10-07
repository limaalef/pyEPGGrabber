"""
Módulo de logging com barra de progresso e estatísticas
"""

import linecache
import math
import shutil
import sys
import traceback
import os
import platform
from pathlib import Path
from datetime import datetime
from typing import Optional
import time

TERMINAL_SIZE = 0

class Colors:
    SYSTEM = platform.system()

    RESET = "\033[0m"
    
    # Cores primárias
    PRIMARY_TEXT_COLOR = "\033[38;2;205;214;244m"
    SECONDARY_TEXT_COLOR = "\033[38;2;245;237;194m"
    SUCCESS_COLOR = "\033[38;2;141;191;141m"
    ERROR_COLOR = "\033[38;2;212;122;130m"
    WARNING_COLOR = "\033[38;2;238;234;190m"
    INFO_COLOR = "\033[38;2;116;151;228m"
    LINE_COLOR = "\033[38;2;54;54;84m"
    EMPTY_COLOR = "\033[38;2;74;74;104m"

    # Cores de destaque
    HIGHLIGHTED_COLOR = "\033[38;2;148;226;213m"
    UNHIGHLIGHTED_COLOR = "\033[38;2;162;169;193m"
    SELECTED_BG = "\033[45m\033[97m\033[1m"

    # Cores de fundo
    BG_COLOR = "\033[48;2;30;30;46m"
    MAGENTA_BG = "\033[45m"

    # Formatação
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[40m"

    # Atalhos combinados
    TITLE = "\033[1m\033[95m"
    PROMPT = "\033[1m\033[96m"

    # Medidas
    MARGIN_LEFT = 4

    # Bordas
    HORIZONTAL = '─'
    VERTICAL = '│'
    TOP_LEFT = '╭'
    TOP_RIGHT = '╮'
    TOP_MIDDLE = '┬'
    BOTTOM_LEFT = '╰'
    BOTTOM_RIGHT = '╯'
    BOTTOM_MIDDLE = '┴'
    VERTICAL_LEFT = '├'

    def clear_screen():
        """Limpa a tela"""
        print(f"{Colors.BG_COLOR}")
        os.system("cls" if Colors.SYSTEM == "Windows" else "clear")

    def print_banner(title="Titulo", subtitle: Optional[str] = "", version: Optional[str] = ""):
        """Exibe banner do programa"""
        Colors.clear_screen()
        cols = shutil.get_terminal_size().columns

        # Linha 1
        Colors.item()
        Colors.center_text(title, Colors.SECONDARY_TEXT_COLOR)
        if subtitle:
            Colors.center_text(subtitle)

        # Linha 2
        Colors.item()

        # Linha 3
        if version:
            Colors.center_text(f"v{version}     @limaalef", highlight=version)
    
    def error(message, title = "Erro"):
        Colors._box(title, message, Colors.ERROR_COLOR, center=True)

    def warning(message, title = "Atenção"):
        Colors._box(title, message, Colors.WARNING_COLOR, center=True)

    def info(message, title = "Info"):
        Colors._box(title, message, Colors.INFO_COLOR, center=True)

    def ok(message, title = "Ok"):
        Colors._box(title, message, Colors.SUCCESS_COLOR, center=True)

    def item(title: str = "", subtitle: Optional[str] = "", index: Optional[str] = "", color = PRIMARY_TEXT_COLOR, highlight: Optional[str] = ""):
        left_margin = Colors.MARGIN_LEFT
        padding = " " * left_margin

        if highlight and highlight in title:
            split_title = title.split(highlight)
            title = f"{split_title[0]}{Colors.HIGHLIGHTED_COLOR}{highlight}{Colors.PRIMARY_TEXT_COLOR}{split_title[1]}"

        if subtitle:
            line = f"{color}{title}: {Colors.SECONDARY_TEXT_COLOR}{subtitle}{Colors.PRIMARY_TEXT_COLOR}"
        else:
            line = f"{color}{title} {Colors.SECONDARY_TEXT_COLOR}{subtitle}{Colors.PRIMARY_TEXT_COLOR}"

        if index:
            line = f"{Colors.HIGHLIGHTED_COLOR}{index} {line}"
    
        line = f"{padding}{line}"
        print(line)

    def select_item(title: str = "", selected: str = ""):
        indent = " " * Colors.MARGIN_LEFT

        if selected:
            output = f"{Colors.PRIMARY_TEXT_COLOR}{indent}{title} {Colors.UNHIGHLIGHTED_COLOR}[{selected}]{Colors.PRIMARY_TEXT_COLOR}: {Colors.HIGHLIGHTED_COLOR}"
        else:
            output = f"{Colors.PRIMARY_TEXT_COLOR}{indent}{title}: {Colors.HIGHLIGHTED_COLOR}"

        return output

    def center_text(title: str = "", color: str = PRIMARY_TEXT_COLOR, highlight: Optional[str] = ""):
        total_width = shutil.get_terminal_size().columns
        if TERMINAL_SIZE < total_width and TERMINAL_SIZE > 0:
            total_width = TERMINAL_SIZE
            
        size = total_width
        
        if highlight and highlight in title:
            split_title = title.split(highlight)
            title = f"{split_title[0]}{Colors.HIGHLIGHTED_COLOR}{highlight}{color}{split_title[1]}"
            size = size + len(Colors.HIGHLIGHTED_COLOR) + len(color)

        line = title.center(size)
        print(f"{color}{line}{Colors.PRIMARY_TEXT_COLOR}")

    def center_title(title: str = "", color: str = PRIMARY_TEXT_COLOR, highlight: Optional[str] = ""):
        total_width = shutil.get_terminal_size().columns
        if TERMINAL_SIZE < total_width and TERMINAL_SIZE > 0:
            total_width = TERMINAL_SIZE
            
        left_margin = Colors.MARGIN_LEFT
        max_width = total_width - left_margin*2 - 2

        line_width = math.floor((max_width - len(title))/2)
        line_item = f"─" * line_width

        padding = " " * left_margin
        
        if highlight and highlight in title:
            split_title = title.split(highlight)
            title = f"{split_title[0]}{Colors.HIGHLIGHTED_COLOR}{highlight}{Colors.PRIMARY_TEXT_COLOR}{split_title[1]}"

        line = f"{padding}{Colors.LINE_COLOR}{line_item} {Colors.SECONDARY_TEXT_COLOR}{title} {Colors.LINE_COLOR}{line_item}{Colors.PRIMARY_TEXT_COLOR}"
        print(f"\n{color}{line}\n")
        
    def list_item(items: list[str]):
        left_margin = Colors.MARGIN_LEFT
        total_width = shutil.get_terminal_size().columns
        if TERMINAL_SIZE < total_width and TERMINAL_SIZE > 0:
            total_width = TERMINAL_SIZE

        max_width = total_width - left_margin * 2 - 2 - 2
        padding = " " * left_margin
        s_padding = Colors.HORIZONTAL * 2

        for i, item in enumerate(items):
            item_lines = Colors._wrap_text(item, max_width)
            for k, line_text in enumerate(item_lines):
                if len(items) == 1:
                    if k == 0:
                        prefix = f"{padding}{Colors.LINE_COLOR}{Colors.BOTTOM_LEFT}{s_padding} "
                    else:
                        prefix = f"{padding}    "
                else:
                    if i == len(items) - 1:
                        if k == 0:
                            prefix = f"{padding}{Colors.LINE_COLOR}{Colors.BOTTOM_LEFT}{s_padding} "
                        else:
                            prefix = f"{padding}{Colors.LINE_COLOR}    "
                    else:
                        if k == 0:
                            prefix = f"{padding}{Colors.LINE_COLOR}{Colors.VERTICAL_LEFT}{s_padding} "
                        else:
                            prefix = f"{padding}{Colors.LINE_COLOR}{Colors.VERTICAL}   "

                print(f"{prefix}{Colors.UNHIGHLIGHTED_COLOR}{line_text}{Colors.PRIMARY_TEXT_COLOR}")

    def _wrap_text(text, max_width):
        words = text.split()
        lines = []
        current_line = ""
        
        for word in words:
            # Se a palavra sozinha é maior que a largura, quebra ela
            if len(word) > max_width:
                if current_line:
                    lines.append(current_line.strip())
                    current_line = ""
                # Quebra a palavra em pedaços
                for i in range(0, len(word), max_width):
                    lines.append(word[i:i+max_width])
            # Se adicionar a palavra ultrapassar a largura
            elif len(current_line) + len(word) + 1 > max_width:
                lines.append(current_line.strip())
                current_line = word + " "
            else:
                current_line += word + " "
        
        if current_line.strip():
            lines.append(current_line.strip())
        
        return lines if lines else [""]

    def _box(title, message, box_color=PRIMARY_TEXT_COLOR, text_color=PRIMARY_TEXT_COLOR, width: int = None, center: bool = False):
        left_margin = Colors.MARGIN_LEFT
        message = str(message)
        title = str(title)

        total_width = shutil.get_terminal_size().columns
        if TERMINAL_SIZE < total_width and TERMINAL_SIZE > 0:
            total_width = TERMINAL_SIZE
            
        if center and width:
            max_width = width
        elif width:
            max_width = width - 2 - 2 - left_margin
        else:
            max_width = total_width - 2 - 2 - left_margin*2
        
        # Processa o texto: divide por \n e depois quebra cada linha
        all_lines = []
        for line in message.split('\n'):
            all_lines.extend(Colors._wrap_text(line, max_width))
        
        # Margem esquerda
        left_space = ' ' * left_margin
        
        # Linha superior (topo)
        top_table = Colors.HORIZONTAL * (max_width + 2)
        top_table = Colors.HORIZONTAL + f" {title} " + top_table[len(title) + 3:]

        if center:
            top_line = f"{box_color}{Colors.TOP_LEFT}{top_table}{Colors.TOP_RIGHT}".center(total_width + len(box_color))
        else:
            top_line = f"{left_space}{box_color}{Colors.TOP_LEFT}{top_table}{Colors.TOP_RIGHT}"
        print(top_line, end="\n")
        
        # Linhas de conteúdo
        for line in all_lines:
            padding = ' ' * (max_width - len(line))
            if center:
                content_line = f"{box_color}{Colors.VERTICAL} {text_color}{line}{padding} {box_color}{Colors.VERTICAL}".center(total_width + len(box_color)*2 + len(text_color))
            else:
                content_line = f"{left_space}{box_color}{Colors.VERTICAL} {text_color}{line}{padding} {box_color}{Colors.VERTICAL}{text_color}"
            print(content_line, end="\n")
        
        # Linha inferior (base)
        if center:
            bottom_line = f"{box_color}{Colors.BOTTOM_LEFT}{Colors.HORIZONTAL * (max_width + 2)}{Colors.BOTTOM_RIGHT}".center(total_width + len(box_color))
        else:
            bottom_line = f"{left_space}{box_color}{Colors.BOTTOM_LEFT}{Colors.HORIZONTAL * (max_width + 2)}{Colors.BOTTOM_RIGHT}{text_color}"
        print(bottom_line, end=f"{text_color}\n")


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

        if TERMINAL_SIZE < self.bar_length and TERMINAL_SIZE > 0:
            self.bar_length = TERMINAL_SIZE - size - 60
            
        

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
            return f"    {Colors.UNHIGHLIGHTED_COLOR}{self.title}  {Colors.HIGHLIGHTED_COLOR}{bar}{Colors.PRIMARY_TEXT_COLOR} • {percentage:.0f}% • {self.total}/{self.total}{space}{Colors.UNHIGHLIGHTED_COLOR}{rate:.2f} itens/seg"
        else:
            return f"    {Colors.UNHIGHLIGHTED_COLOR}{self.title}  {Colors.SECONDARY_TEXT_COLOR}{bar}{Colors.PRIMARY_TEXT_COLOR} • {percentage:.0f}% •  {Colors.HIGHLIGHTED_COLOR}{self.current}/{Colors.PRIMARY_TEXT_COLOR}{self.total} programas encontrados"

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
        # Adicione isto se quiser manter estatísticas:
        self.stats = {
            'errors': 0,
            'warnings': 0
        }

    def increment_stat(self, stat_name: str, value: int = 1):
        """Incrementa estatística específica"""
        if stat_name in self.stats:
            self.stats[stat_name] += value

    def log_exception(self, exception: Exception, context: str = ""):
        """
        Registra exceção com traceback e trecho de código
        
        Args:
            exception: Exceção capturada
            context: Contexto adicional
        """
        self.increment_stat('errors')
        
        # Extrai informações do traceback
        tb_list = traceback.extract_tb(exception.__traceback__)
        if not tb_list:
            print(f"[ERRO] {context} - {str(exception)}")
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
        
        # Imprime erro (removido progress_bar.write)
        Colors.error(short_msg)
        
        # Extrai código-fonte ao redor do erro
        code_context = self._get_code_context(file_path, line_num, context_lines=3)
        
        # Exibe código no console
        print(code_context)
        sys.exit(1)

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
                        new_line = f"{Colors.UNHIGHLIGHTED_COLOR}{marker}{i:4d} | {line.rstrip()}"
                        spaces = max(
                            cols
                            - len(new_line)
                            + len(Colors.UNHIGHLIGHTED_COLOR)
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