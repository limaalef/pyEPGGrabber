"""
Módulo de configuração do EPG Grabber
Carrega configurações de serviços em formato YAML e mapeamentos
"""

import yaml
from pathlib import Path
from typing import Dict, List, Optional


class EPGConfig:
    """Gerencia configurações do EPG Grabber"""

    def __init__(self, config_dir: Path):
        self.config_dir = Path(config_dir)
        self.services_dir = self.config_dir / "services"
        self.mappings_file = self.config_dir / "mappings.yaml"

        # Cache de configurações para evitar leituras repetidas
        self._services_cache = {}
        self._mappings_cache = None

        # Carrega mapeamentos
        self.load_mappings()

    def load_mappings(self):
        """Carrega mapeamentos de programas, competições e gêneros"""
        if self._mappings_cache is not None:
            return

        if not self.mappings_file.exists():
            self._mappings_cache = {}
            self.competitions_map = {}
            self.programs_map = {}
            self.genres_map = {}
            return

        with open(self.mappings_file, "r", encoding="utf-8") as f:
            self._mappings_cache = yaml.safe_load(f) or {}

        self.competitions_map = self._mappings_cache.get("competitions", {})
        self.programs_map = self._mappings_cache.get("programs", {})
        self.genres_map = self._mappings_cache.get("genres", {})

    def get_all_services(self) -> List[str]:
        """Retorna lista de todos os serviços disponíveis"""
        return [f.stem for f in self.services_dir.glob("*.yaml")]

    def load_service_config(self, service_name: str) -> Dict:
        """
        Carrega configuração de um serviço específico

        Args:
            service_name: Nome do arquivo de serviço (sem extensão)

        Returns:
            Dicionário com configurações do serviço
        """
        # Verifica cache
        if service_name in self._services_cache:
            return self._services_cache[service_name]

        service_file = self.services_dir / f"{service_name}.yaml"

        if not service_file.exists():
            raise FileNotFoundError(f"Serviço não encontrado: {service_name}")

        # Carrega YAML
        with open(service_file, "r", encoding="utf-8") as f:
            raw_config = yaml.safe_load(f)

        # Normaliza configuração com valores padrão
        config = {
            "name": raw_config.get("service_name"),
            "api_url": raw_config.get("api_url"),
            "headers": raw_config.get("headers", {}),
            "channels": raw_config.get("channels", []),
            "target_channels": self._normalize_list(raw_config.get("target_channels")),
            "api_level_1": self._normalize_path(raw_config.get("api_level_1")),
            "api_level_2": self._normalize_path(raw_config.get("api_level_2")),
            "channel": self._normalize_path(raw_config.get("channel")),
            "program_title": self._normalize_path(raw_config.get("program_title")),
            "subtitle": self._normalize_path(raw_config.get("subtitle")),
            "description": self._normalize_path(raw_config.get("description")),
            "start_time": self._normalize_path(raw_config.get("start_time")),
            "end_time": self._normalize_path(raw_config.get("end_time")),
            "live": self._normalize_path(raw_config.get("live")),
            "duration": self._normalize_path(raw_config.get("duration")),
            "rating": self._normalize_path(raw_config.get("rating")),
            "rating_criteria": self._normalize_path(raw_config.get("rating_criteria")),
            "rating_auto": self._normalize_path(raw_config.get("rating_auto")),
            "season": self._normalize_path(raw_config.get("season")),
            "episode": self._normalize_path(raw_config.get("episode")),
            "tags": self._normalize_path(raw_config.get("tags")),
            "genre": self._normalize_path(raw_config.get("genre")),
            "timezone": raw_config.get("timezone", "+00:00"),
            "no_loop": raw_config.get("no_loop", False),
            "list_url": raw_config.get("use_list_in_url", False),
        }

        # Adiciona ao cache
        self._services_cache[service_name] = config

        return config

    def _normalize_list(self, value) -> List[str]:
        """Normaliza valor para lista de strings"""
        if value is None:
            return []
        if isinstance(value, str):
            return [v.strip() for v in value.split(",") if v.strip()]
        if isinstance(value, list):
            return [str(v).strip() for v in value if v]
        return []

    def _normalize_path(self, value) -> List[str]:
        """Normaliza caminho de acesso à API (ex: 'data.programs' -> ['data', 'programs'])"""
        if value is None:
            return []
        if isinstance(value, str):
            # Suporta tanto 'data.programs' quanto ['data', 'programs']
            return [v.strip() for v in value.replace("+", ".").split(".") if v.strip()]
        if isinstance(value, list):
            # Se já for lista, achata caso tenha sublistas
            result = []
            for item in value:
                if isinstance(item, str):
                    result.extend(item.replace("+", ".").split("."))
                else:
                    result.append(str(item))
            return [v.strip() for v in result if v.strip()]
        return []

    def get_service_channels(self, service_name: str) -> List[Dict]:
        """Retorna lista de canais configurados para um serviço"""
        config = self.load_service_config(service_name)
        return config.get("channels", [])

    def get_competition_mapping(
        self, competition_name: str, channel: str = None
    ) -> tuple:
        """
        Busca mapeamento de competição

        Returns:
            (nome_formatado, gênero) ou (None, None)
        """
        result = self.competitions_map.get(competition_name)
        if result:
            return tuple(result) if isinstance(result, list) else (result, None)

        return None, None

    def get_program_mapping(self, program_name: str) -> Optional[str]:
        """Busca mapeamento de programa"""
        return self.programs_map.get(program_name)

    def get_genre_mapping(self, genre_name: str) -> Optional[str]:
        """Busca mapeamento de gênero"""
        return self.genres_map.get(genre_name)
