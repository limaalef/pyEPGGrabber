"""
Módulo de requisições às APIs de EPG
"""

import requests
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pytz


class EPGFetcher:
    """Faz requisições às APIs de EPG"""

    def __init__(self, config):
        self.config = config
        self.session = requests.Session()

    def fetch(
        self, service_config: Dict, days: int = 0, channel_id: Optional[int] = None
    ) -> Dict:
        """
        Faz requisição à API

        Args:
            service_config: Configuração do serviço
            days: Número de dias a adicionar à data atual
            channel_id: ID do canal (para APIs específicas)

        Returns:
            Dados JSON da resposta
        """
        url = self._build_url(service_config["api_url"], days, channel_id)
        headers = service_config.get("headers", {})

        try:
            response = self.session.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            return response.json()

        except requests.exceptions.RequestException as e:
            raise Exception(f"Erro ao acessar API: {str(e)}")

    def _build_url(
        self, url_template: str, days: int, channel_id: Optional[int]
    ) -> str:
        """Constrói URL com variáveis substituídas"""
        date = datetime.now() + timedelta(days=days)

        # Substitui variáveis
        url = url_template
        url = url.replace("ANO-MES-DIA", date.strftime("%Y-%m-%d"))
        url = url.replace("DIA/MES/ANO", date.strftime("%d/%m/%Y"))
        url = url.replace("QTDHORAS", str((days + 1) * 24))
        url = url.replace("QTDDIAS", str((days if days > 0 else 1)))

        # Unix timestamps
        date_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        date_end = date_start + timedelta(days=1)
        url = url.replace("UNIXTIMESTART", str(int(date_start.timestamp())))
        url = url.replace("UNIXTIMEEND", str(int(date_end.timestamp())))

        # ID do canal
        if channel_id:
            url = url.replace("IDCANAL", str(channel_id))

        return url

    def extract_programs(self, data: Dict, service_config: Dict) -> List[Dict]:
        """
        Extrai lista de programas dos dados da API

        Args:
            data: Dados JSON da API
            service_config: Configuração do serviço

        Returns:
            Lista de programas
        """
        programs = []

        # Navega pelos níveis da API
        current_data = data
        for level in service_config["api_level_1"]:
            if level in current_data:
                current_data = current_data[level]
            else:
                return programs

        # Garante que seja lista
        if not isinstance(current_data, list):
            current_data = [current_data]

        # Para cada item no nível 1
        for item in current_data:
            # Extrai canal
            channel = self._extract_field(item, service_config["channel"])
            if not channel:
                channel = service_config.get("name")

            # Verifica se canal deve ser incluído
            target_channels = service_config.get("target_channels", [])
            if target_channels and not any(
                ch in str(channel).lower() for ch in target_channels
            ):
                continue

            # Navega ao nível 2 (programas)
            program_data = item
            for level in service_config["api_level_2"]:
                if level in program_data:
                    program_data = program_data[level]

            if not isinstance(program_data, list):
                program_data = [program_data]

            # Extrai cada programa
            for prog in program_data:
                program = self._extract_program(prog, service_config, channel)
                if program:
                    programs.append(program)
        return programs

    def _extract_field(self, data: Dict, path: List[str]) -> Optional[str]:
        """Extrai campo navegando pelo caminho"""
        current = data
        if path:
            for key in path:
                if isinstance(current, dict) and key in current:
                    current = current[key]
                else:
                    return None
            return current
        else:
            return None

    def _extract_program(
        self, prog_data: Dict, config: Dict, channel: str
    ) -> Optional[Dict]:
        """Extrai dados de um programa"""
        start_time = self._extract_field(prog_data, config["start_time"])
        self._parse_datetime(start_time, config["timezone"])
        end_time = self._extract_field(prog_data, config["end_time"])
        program = {
            "channel": channel,
            "title": self._extract_field(prog_data, config["program_title"]),
            "subtitle": self._extract_field(prog_data, config["subtitle"]),
            "description": self._extract_field(prog_data, config["description"]),
            "start_time": self._parse_datetime(start_time, config["timezone"]),
            "end_time": self._parse_datetime(end_time, config["timezone"]),
            "duration": self._extract_field(prog_data, config["duration"]),
            "live": self._extract_field(prog_data, config["live"]),
            "rating": self._extract_field(prog_data, config["rating"]),
            "season": self._extract_field(prog_data, config["season"]),
            "episode": self._extract_field(prog_data, config["episode"]),
            "genre": self._extract_field(prog_data, config["genre"]),
        }

        return program if program["title"] else None

    def _parse_datetime(self, dt_str: str, timezone: str) -> Optional[datetime]:
        """Parse datetime de vários formatos"""
        tz = pytz.timezone(timezone)

        try:
            timestamp = int(dt_str)
            if timestamp > 10000000000:
                timestamp = timestamp / 1000

            return datetime.fromtimestamp(timestamp, tz)
        except ValueError:
            try:
                dt = datetime.fromisoformat(dt_str)
                dt = tz.localize(dt)
                return dt
            except ValueError:
                formats = [
                    "%Y-%m-%dT%H:%M:%SZ",
                    "%Y-%m-%dT%H:%MZ",
                    "%Y%m%d%H%M%S %z",
                    "%Y%m%d%H%M%S",
                ]

                for fmt in formats:
                    try:
                        return datetime.strptime(dt_str, fmt)
                    except ValueError:
                        continue

        return dt_str
