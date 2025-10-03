"""
Módulo de escrita de arquivos XMLTV
"""

import xml.etree.ElementTree as ET
from xml.dom import minidom
from pathlib import Path
from datetime import datetime
from typing import List, Dict


class EPGWriter:
    """Escreve dados de EPG em formato XMLTV"""

    def __init__(self, config):
        self.config = config

    def write_xml(self, programs: List[Dict], service_name: str = None, output_path: str = None) -> str:
        """
        Escreve arquivo XML com programas

        Args:
            programs: Lista de programas processados
            output_path: Caminho de saída (opcional)

        Returns:
            Caminho do arquivo gerado
        """
        filename = f"{service_name}_epg.xml" if service_name else "epg.xml"

        output_path = Path(output_path) if output_path else Path(__file__).parent
        output_path = output_path / filename
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Cria elemento raiz
        root = ET.Element("tv")
        root.set(
            "generator-info-name",
            f'@limaalef - Criado em {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
        )
        root.set("generator-info-url", "http://limaalef.com")

        # Adiciona canais únicos
        channels = list(
            dict.fromkeys([p.get("channel") for p in programs if "channel" in p])
        )
        for channel in channels:
            channel_elem = ET.SubElement(root, "channel")
            channel_elem.set("id", channel)

            display_name = ET.SubElement(channel_elem, "display-name")
            display_name.set("lang", "pt")
            display_name.text = channel

        # Adiciona programas
        for prog in programs:
            programme = ET.SubElement(root, "programme")
            programme.set("start", self._format_datetime(prog["start_time"]))
            programme.set("stop", self._format_datetime(prog["end_time"]))
            programme.set("channel", prog["channel"])
            # Título
            if prog.get("title"):
                title = ET.SubElement(programme, "title")
                title.set("lang", "pt")
                title.text = prog["title"]

            # Subtítulo
            if prog.get("subtitle"):
                subtitle = ET.SubElement(programme, "sub-title")
                subtitle.set("lang", "pt")
                subtitle.text = prog["subtitle"]

            # Descrição
            if prog.get("description"):
                desc = ET.SubElement(programme, "desc")
                desc.set("lang", "pt")
                desc.text = prog["description"]

            # Duração
            if prog.get("duration"):
                length = ET.SubElement(programme, "length")
                length.set("units", "minutes")
                length.text = str(prog["duration"])

            # Gênero
            if prog.get("genre"):
                category = ET.SubElement(programme, "category")
                category.set("lang", "en")
                category.text = prog["genre"]

            # Data do evento
            if prog.get("event_date"):
                date = ET.SubElement(programme, "date")
                date.text = datetime.strptime(prog["event_date"], "%d/%m/%Y").strftime(
                    "%Y%m%d"
                )

            # Episódio (formato XMLTV)
            if prog.get("season") is not None or prog.get("episode") is not None:
                episode_num = ET.SubElement(programme, "episode-num")
                episode_num.set("system", "xmltv_ns")

                season = prog.get("season") or ""
                episode = prog.get("episode") or ""

                episode_num.text = f"{season}.{episode}."

            # Classificação indicativa
            if prog.get("rating"):
                rating = ET.SubElement(programme, "rating")
                rating.set("system", "Brazil")

                value = ET.SubElement(rating, "value")
                value.text = f"[{prog['rating']}]"

            # Flags
            if prog.get("rerun"):
                ET.SubElement(programme, "previously-shown")
            elif prog.get("premiere"):
                ET.SubElement(programme, "premiere")
            elif prog.get("live"):
                ET.SubElement(programme, "new")

        # Formata e salva
        xml_str = self._prettify(root)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(xml_str)

        return str(output_path)

    def _format_datetime(self, dt: datetime) -> str:
        """Formata datetime para formato XMLTV"""
        return dt.strftime("%Y%m%d%H%M%S %z").strip()

    def _prettify(self, elem: ET.Element) -> str:
        """Formata XML com indentação"""
        rough_string = ET.tostring(elem, encoding="unicode")
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ", encoding="utf-8").decode("utf-8")


class EPGLogger:
    """Logger simples para EPG"""

    def __init__(self, log_path: Path):
        self.log_path = Path(log_path)
        self.start_time = None

    def start_log(self):
        """Inicia log"""
        self.start_time = datetime.now()
        msg = f"\n{self.start_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        self._write(msg)
        print(msg)

    def log_progress(self, message: str):
        """Log de progresso"""
        print(f"\r{message}", end="", flush=True)

    def log_success(self, message: str):
        """Log de sucesso"""
        msg = f"✓ {message}"
        self._write(msg)
        print(msg)

    def log_error(self, message: str):
        """Log de erro"""
        msg = f"✗ {message}"
        self._write(msg)
        print(msg)

    def end_log(self, program_count: int):
        """Finaliza log"""
        if self.start_time:
            elapsed = datetime.now() - self.start_time
            msg = f"\nProgresso total: {elapsed}\nProgramas salvos: {program_count}\n"
            self._write(msg)
            print(msg)

    def _write(self, message: str):
        """Escreve no arquivo de log"""
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(message + "\n")
