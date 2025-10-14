"""
Módulo de processamento de dados EPG
Processa e normaliza informações de programas
"""

import re
from datetime import datetime
from typing import Dict, Optional

try:
    from sports_api import ScheduleSearcher
    spa = True
except ImportError:
    spa = None


class EPGProcessor:
    """Processa e normaliza dados de EPG"""

    def __init__(self, config):
        self.config = config

    def process_program(
        self, raw_program: Dict, service_config: Dict
    ) -> Optional[Dict]:
        """
        Processa um programa bruto e retorna normalizado

        Args:
            raw_program: Dados brutos do programa
            service_config: Configuração do serviço

        Returns:
            Dicionário com dados processados ou None
        """
        channel = raw_program.get("channel", "")

        # Inicializa dados processados
        processed = {
            "channel": channel,
            "title": raw_program.get("title", ""),
            "subtitle": raw_program.get("subtitle"),
            "description": raw_program.get("description"),
            "start_time": raw_program.get("start_time"),
            "end_time": raw_program.get("end_time"),
            "duration": raw_program.get("duration"),
            "rating": raw_program.get("rating"),
            "rating_criteria": raw_program.get("rating_criteria"),
            "season": raw_program.get("season"),
            "episode": raw_program.get("episode"),
            "genre": raw_program.get("genre"),
            "live": raw_program.get("live"),
            "premiere": False,
            "rerun": False,
            "event_date": None,
            "phase": False,
        }

        # Se não tem título, pula
        if not processed["title"]:
            processed["title"] = f"Programação {channel}"

        # Extrai informações do título/subtítulo
        processed = self._extract_date(processed)
        processed = self._extract_season_episode(processed)
        processed = self._extract_phase(processed)
        processed = self._extract_location(processed)

        # Detecta se é ao vivo, inédito ou reprise
        processed = self._detect_live_status(processed)

        # Processa específico por canal
        processed = self._process_by_channel(processed, channel)

        # Mapeia competições e programas
        processed = self._map_competitions_programs(processed, channel)

        # Mapeia gêneros
        processed = self._map_genre(processed)

        # Normaliza classificação indicativa
        processed = self._normalize_rating(processed)

        # Padroniza a saida
        processed = self.process_output(processed)

        return processed

    def _extract_date(self, prog: Dict) -> Dict:
        """Extrai datas do título/subtítulo"""
        date_pattern = r"\b(\d{1,2}/\d{1,2}/\d{2,4}|\d{6,8})\b"

        for field in ["title", "subtitle"]:
            if not prog.get(field):
                continue

            match = re.search(date_pattern, prog[field])
            if match:
                date_str = match.group(1).replace("/", "")

                # Converte para formato padrão
                if len(date_str) == 6:
                    prog["event_date"] = datetime.strptime(date_str, "%d%m%y").strftime(
                        "%d/%m/%Y"
                    )
                elif len(date_str) == 8:
                    prog["event_date"] = datetime.strptime(date_str, "%d%m%Y").strftime(
                        "%d/%m/%Y"
                    )

                # Remove do texto original
                prog[field] = re.sub(
                    r"\s?-?\s?" + re.escape(match.group(0)), "", prog[field]
                )

        return prog

    def _extract_season_episode(self, prog: Dict) -> Dict:
        """Extrai informações de temporada e episódio"""
        # Padrões para temporada
        season_patterns = [
            r"T(\d+)",
            r"Temporada\s+(\d+)",
            r"Temp\.?\s+(\d+)",
            r"(\d+)ª?\s*Temporada",
        ]

        # Padrões para episódio
        episode_patterns = [r"Episódio\s+(\d+)", r"Ep\.?\s+(\d+)", r"EP\s+(\d+)"]

        for field in ["title", "subtitle"]:
            if not prog.get(field):
                continue

            # Busca temporada
            for pattern in season_patterns:
                match = re.search(pattern, prog[field], re.IGNORECASE)
                if match:
                    prog["season"] = int(match.group(1)) - 1  # XMLTV usa zero-indexed
                    prog[field] = re.sub(
                        r"\s?-?\s?\(?" + pattern + r"\)?",
                        "",
                        prog[field],
                        flags=re.IGNORECASE,
                    )
                    break

            # Busca episódio
            for pattern in episode_patterns:
                match = re.search(pattern, prog[field], re.IGNORECASE)
                if match:
                    prog["episode"] = int(match.group(1)) - 1  # XMLTV usa zero-indexed
                    prog[field] = re.sub(
                        r"\s?-?\s?" + pattern, "", prog[field], flags=re.IGNORECASE
                    )
                    break

        return prog

    def _extract_phase(self, prog: Dict) -> Dict:
        """Extrai fases de competição (oitavas, quartas, final, etc)"""
        
        # Ordem de prioridade: fases mais específicas primeiro
        phase_patterns = [
            (r"Oitavas De Final", "Oitavas de Final", 1),
            (r"Quartas De Final", "Quartas de Final", 2),
            (r"Semifinal(?:is)?", "Semifinal", 3),
            (r"Finais", "Finais", 4),
            (r"Final", "Final", 5),
            (r"Jogo (?:De )?Ida", "Jogo de Ida", 6),
            (r"Jogo (?:De )?Volta", "Jogo de Volta", 7),
            (r"Fase De Grupos", "Fase de Grupos", 8),
            (r"(\d+)ª Rodada", None, 9),  # Tratamento especial
        ]
        
        for field in ["title", "subtitle"]:
            if not prog.get(field):
                continue
            
            found_phases = []
            text = prog[field]
            
            # Encontra todas as fases no texto
            for pattern, replacement, priority in phase_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    if replacement is None:  # Caso especial para rodadas
                        phase_text = f"{match.group(1)}ª Rodada"
                    else:
                        phase_text = replacement
                    
                    found_phases.append({
                        "text": phase_text,
                        "priority": priority,
                        "match": match,
                        "pattern": pattern
                    })
            
            # Se encontrou fases neste campo, processa e para
            if found_phases:
                # Estratégia 1: Se há "Jogo de Ida/Volta" + outra fase, combina
                ida_volta = next((p for p in found_phases if "Jogo de" in p["text"]), None)
                other_phase = next((p for p in found_phases if "Jogo de" not in p["text"]), None)
                
                if ida_volta and other_phase:
                    # Combina as duas fases: "Oitavas de Final - Jogo de Ida"
                    prog["phase"] = f"{other_phase['text']} - {ida_volta['text']}"
                    
                    # Remove ambos os padrões do campo
                    for phase in found_phases:
                        text = re.sub(
                            r"\s?-?\s?" + phase["pattern"], 
                            "", 
                            text, 
                            flags=re.IGNORECASE
                        )
                else:
                    # Estratégia 2: Usa a fase de maior prioridade (menor número)
                    selected_phase = min(found_phases, key=lambda x: x["priority"])
                    prog["phase"] = selected_phase["text"]
                    
                    # Remove apenas o padrão selecionado
                    text = re.sub(
                        r"\s?-?\s?" + selected_phase["pattern"], 
                        "", 
                        text, 
                        flags=re.IGNORECASE
                    )
                
                # Limpa espaços extras e traços soltos
                text = re.sub(r"\s+-\s+", " - ", text.strip())
                text = re.sub(r"^\s*-\s*|\s*-\s*$", "", text).strip()
                prog[field] = text
                
                # Para aqui - não processa o outro campo
                break
        
        return prog

    def _extract_location(self, prog: Dict) -> Dict:
        """
        Extrai localidades do subtitle e as adiciona ao final da phase.
        Localidades seguem o formato: "Cidade, País" ou "- Cidade, País" ou apenas "País"
        """
        if not prog.get("subtitle"):
            return prog
        
        subtitle = prog["subtitle"]
        
        # Padrões para detectar localidades:
        # 1. " - Cidade, País" ou " - País"
        # 2. "Cidade,País" (sem espaço após vírgula)
        location_patterns = [
            r"\s*-\s*([A-ZÀ-Ú][^-]+,\s*[A-ZÀ-Ú][^-]+)$",   # " - Tóquio, Japão"
            r"\s*-\s*([A-ZÀ-Ú][^-]+,[A-ZÀ-Ú][^-]+)$",      # " - Tóquio, Japão" (sem espaço)
            r"^([A-ZÀ-Ú][^-,]+,\s*[A-ZÀ-Ú][^-,]+)$",       # "Szombathely, Hungria"
            r"^([A-ZÀ-Ú][^-,]+,[A-ZÀ-Ú][^-,]+)$",          # "Szombathely,Hungria" (sem espaço)
        ]
        
        location = None
        cleaned_subtitle = subtitle
        
        for pattern in location_patterns:
            match = re.search(pattern, subtitle)
            if match:
                location = match.group(1).strip()
                
                # Formata a localidade: garante espaço após vírgula
                if "," in location:
                    parts = [part.strip() for part in location.split(",")]
                    location = ", ".join(parts)
                
                # Remove a localidade do subtitle
                cleaned_subtitle = re.sub(pattern, "", subtitle).strip()
                break
        
        if location:
            # Se o subtitle ficou vazio, mantém só a localidade formatada
            if not cleaned_subtitle:
                prog["subtitle"] = location
                not_phase = True
            else:
                prog["subtitle"] = cleaned_subtitle
                not_phase = False
            
            # Adiciona localidade ao final da phase
            if not not_phase:
                if prog.get("phase"):
                    prog["phase"] = f"{prog['phase']} - {location}"
                else:
                    prog["phase"] = location
        
        return prog

    def _detect_live_status(self, prog: Dict) -> Dict:
        """Detecta se programa é ao vivo, inédito ou reprise"""
        # Ao vivo
        live_patterns = [r"- Ao Vivo", r"- VIVO", r"AO VIVO$"]
        for pattern in live_patterns:
            if prog.get("title") and re.search(pattern, prog["title"], re.IGNORECASE):
                prog["live"] = True
                prog["title"] = re.sub(
                    r"\s?-?\s?" + pattern, "", prog["title"], flags=re.IGNORECASE
                )
                break

        # Inédito/Estreia
        premiere_patterns = [r"- Inédito", r"- INÉ?DITO", r" INÉDITO", r"- Estreia"]
        for pattern in premiere_patterns:
            if prog.get("title") and re.search(pattern, prog["title"], re.IGNORECASE):
                prog["premiere"] = True
                prog["live"] = pattern.replace(" -", "").replace(" ", "").lower()
                prog["title"] = re.sub(
                    r"\s?-?\s?" + pattern, "", prog["title"], flags=re.IGNORECASE
                )
                break

        # Reprise/VT
        rerun_patterns = [
            r"VT - ",
            r" - VT",
            r"- Reprise",
            r" - Reapresentação",
            r"Retrô",
        ]
        for pattern in rerun_patterns:
            if prog.get("title") and re.search(pattern, prog["title"], re.IGNORECASE):
                prog["rerun"] = True
                if "Premiere Retrô" in prog.get("title"):
                    prog["title"] = re.sub(r'\s*\d{4}', '', prog["subtitle"]).strip()
                    prog["subtitle"] = ""
                    prog["live"] = "Retrô"
                else:
                    prog["title"] = re.sub(pattern, "", prog["title"], flags=re.IGNORECASE)
                    prog["live"] = (
                        "reprise"
                        if pattern in ["- Reprise", " - Reapresentação"]
                        else prog["live"]
                    )
                break

        return prog

    def _process_by_channel(self, prog: Dict, channel: str) -> Dict:
        """Processamento específico por canal"""
        if 'local' in channel.lower():
            if prog.get("description"):
                if re.search(r"\[(\d+\+)\]", prog["description"]):
                    match = re.search(r"\[(\d+\+)\]", prog["description"])
                    prog["rating"] = match.group(1) if match else None
                    prog["description"] = re.sub(r"\s*\[\d+\+\]", "", prog["description"])

        # SporTV, Premiere, Combate
        if any(ch in channel for ch in ["sportv", "premiere", "combate", "ge-tv"]):
            prog["genre"] = "sports (general)"

            # Separa titulo se subtitulo vazio
            if not prog["subtitle"] and " - " in prog["title"]:
                prog["title"], prog["subtitle"] = prog["title"].split(" - ", 1)
            
            # Normaliza confrontos (X minusculo)
            if prog.get("subtitle"):
                prog["subtitle"] = re.sub(r"\s+X\s+", " x ", prog["subtitle"])

            # Remove sufixos desnecessários
            if prog.get("subtitle"):
                prog["subtitle"] = re.sub(r"\s?-?\s?Globoplay", "", prog["subtitle"])
            
            # Trazer mais dados dos jogos
            pattern = r'^[A-Za-zÀ-ÿ0-9\s]+ x [A-Za-zÀ-ÿ0-9\s]+$'
            match_name = prog.get("subtitle")
            if match_name != None:
                if re.match(pattern, match_name):
                    searcher = ScheduleSearcher(prog["start_time"], use_cache=True)
                    teams = prog["subtitle"].split(" x ")

                    r = searcher.get_match_by_teams(
                        date_ref=prog["start_time"],
                        home_team=teams[0],
                        away_team=teams[1]
                    )
                    
                    if len(r) > 0:
                        prog["phase"] = r["phase"]
                        
        elif 'x sports' in channel.lower():
            if prog["subtitle"]:
                prog["description"] = prog["subtitle"]
                prog["subtitle"] = None
            
            if not prog["subtitle"] and " - " in prog["title"]:
                prog["title"], prog["subtitle"] = prog["title"].split(" - ", 1)

        # Record
        elif "record sp" in channel.lower():
            prog["description"] = prog["subtitle"]
            # Captura dados de jogos de futebol
            if ('Campeonato Brasileiro' in prog.get("title") or 'Campeonato Paulista' in prog.get("title")) and spa is True:
                searcher = ScheduleSearcher(prog["start_time"], use_cache=True)

                teams = prog["title"].split(" - ")[1].split(" x ")

                r = searcher.get_match_by_teams(
                    date_ref=prog["start_time"],
                    home_team=teams[0],
                    away_team=teams[1]
                )
                
                if len(r) > 0:
                    prog["title"] = r["title"]

                    temp = self._map_competitions_programs(prog, prog["channel"])
                    prog["description"] = f'{r["description"]}. {prog["description"]}'
                    prog["subtitle"] = None
                    prog["title"] = f'{temp["title"]}: {r["subtitle"]}'
                    prog["phase"] = r["phase"]
                    prog["live"] = True
            elif "Inteligência e Fé" in prog["title"]:
                prog["subtitle"] = "Inteligência e Fé"
                prog["title"] = "Programação IURD"
            elif "Palavra Amiga" in prog["title"]:
                prog["subtitle"] = "Palavra Amiga"
                prog["title"] = "Programação IURD"
            elif "Programa do Templo" in prog["title"]:
                prog["subtitle"] = "Programa do Templo"
                prog["title"] = "Programação IURD"
            elif "Programação Universal - IURD" in prog["title"]:
                prog["subtitle"] = re.sub(r"^\s*Programação Universal\s*-\s*IURD\s?\-?\s?", "", prog["title"])
                prog["title"] = "Programação IURD"
            else:
                prog["subtitle"] = None

        # Band
        elif "band sp" in channel.lower():
            prog["description"] = prog["subtitle"]
            
            match = re.match(r'^(INFOMERCIAL|RELIGIOSO)\s*-\s*(.+)$', prog["title"], re.IGNORECASE)
            if match:
                prog["title"] = match.group(1).upper()
                prog["subtitle"] = match.group(2).strip()
            elif "Igreja Cristo Para As Nações" in prog["title"] or "Igreja Universal do Reino de Deus" in prog["title"] or "Show da Fé" in prog["title"] or "Oração do dia com Profeta Vinícius Iracet" in prog["title"]:
                prog["subtitle"] = prog["title"]
                prog["title"] = "RELIGIOSO"
            else:   
                prog["subtitle"] = None

        # Globo
        elif "globo sp" in channel.lower():
            SESSOES_FILMES = [
                "Corujão I",
                "Corujão II",
                "Corujão III",
                "Corujão VI",
                "Temperatura Máxima",
                "Campeões de Bilheteria",
                "Domingo Maior",
                "Sessão da Tarde",
                "Tela Quente",
                "Cinemaço",
                "Cinema Especial",
                "Festival de Sucessos",
                "Sessão Brasil",
                "Sessão de Natal",
                "Supercine"
            ]

            # Trata "Vale a Pena Ver de Novo"
            if prog.get("title") and "Vale a Pena Ver de Novo" in prog["title"]:
                match = re.search(r"Vale a Pena Ver de Novo\s*-\s*(.*)", prog["title"])
                if match:
                    prog["subtitle"] = match.group(1)
                    prog["title"] = "Vale a Pena Ver de Novo"
            

            # Trata "Sessão Globoplay"
            if prog.get("title") and "Sessão Globoplay" in prog["title"]:
                match = re.search(r"Sessão Globoplay\s*-\s*(.*)", prog["title"])
                if match:
                    prog["subtitle"] = match.group(1)
                    prog["title"] = "Sessão Globoplay"

            if prog["subtitle"]:
                prog["description"] = prog["subtitle"]
                prog["subtitle"] = None
            
            if not prog["subtitle"] and " - " in prog["title"]:
                prog["title"], prog["subtitle"] = prog["title"].split(" - ", 1)

            # Captura dados de jogos de futebol
            if prog.get("title") == "Futebol" and spa is True:
                searcher = ScheduleSearcher(prog["start_time"], ["Brasil", "Corinthians", "Palmeiras", "São Paulo", "Santos"], use_cache=True)

                r = searcher.get_match(prog["start_time"], "Globo")
                
                if len(r) > 0:
                    prog["title"] = r["title"]

                    temp = self._map_competitions_programs(prog, prog["channel"])
                    prog["title"] = f'{temp["title"]}: {r["subtitle"]}'
                    prog["phase"] = r["phase"]
                    prog["description"] = f'{r["description"]}. {prog["description"]}'
                    prog["live"] = True
        
            if prog.get("title").strip().lower() in [s.lower() for s in SESSOES_FILMES]:
                prog["title"] = f'{prog["title"]}: {prog["subtitle"]}'
                prog["subtitle"] = ""

            if "Edição Especial" in prog.get("title"):
                prog["title"] = f'{prog["subtitle"]} - {prog["title"]}'
                prog["subtitle"] = ""

        # GloboNews
        elif "globonews" in channel or "news" in channel:
            prog["genre"] = "news/current affairs (general)"

            # Padroniza "Jornal GloboNews"
            if prog.get("title") and "Edição Das" in prog["title"]:
                match = re.search(r"Edição Das (\d+)h", prog["title"], re.IGNORECASE)
                if match:
                    hour = int(match.group(1))
                    prog["title"] = f"Jornal GloboNews - Edição das {hour:02d}h"
                    prog["subtitle"] = None

        # Viva, Multishow
        elif "viva" in channel or "multishow" in channel:
            # TVZ sempre maiúsculo
            if prog.get("title"):
                prog["title"] = prog["title"].replace("Tvz", "TVZ")

            # Extrai capítulos de novelas
            if prog.get("subtitle") and "Capítulo" in prog["subtitle"]:
                match = re.search(r"Capítulo\s+(\d+)", prog["subtitle"])
                if match:
                    prog["episode"] = int(match.group(1)) - 1
                    prog["subtitle"] = re.sub(r"Capítulo\s+\d+", "", prog["subtitle"])

        # Canais SBT
        elif "sbt" in channel or any(
            s in channel for s in ["silvio", "saudade", "pop"]
        ):
            # Champions League
            if prog.get("title") and "Champions League" in prog["title"]:
                prog["title"] = "UEFA Champions League"
                if prog.get("subtitle"):
                    prog["subtitle"] = re.sub(
                        r"Champions League\s*-?\s*", "", prog["subtitle"]
                    )

            # Copa Sul-Americana
            if prog.get("title") and "Sudamericana" in prog["title"]:
                prog["title"] = "CONMEBOL Sul-Americana"

        return prog

    def _map_competitions_programs(self, prog: Dict, channel: str) -> Dict:
        """Mapeia nomes de competições e programas"""
        title = prog.get("title", "")
        
        # Tenta mapear competição
        mapped, genre = self.config.get_competition_mapping(title)
        if mapped:
            prog["title"] = mapped
            if genre:
                prog["genre"] = genre

        if (
            any(
                ch in channel.lower()
                for ch in ["sportv", "premiere", "combate", "ge-tv", "band sports", "globo sp_local", "x sports_local"]
            )
            and mapped
        ):
            if prog.get("live") != True:
                prog["live"] = "VT"

        # Tenta mapear programa
        mapped_program = self.config.get_program_mapping(title)
        if mapped_program:
            prog["title"] = mapped_program

        return prog

    def _map_genre(self, prog: Dict) -> Dict:
        """Mapeia gêneros para formato XMLTV"""
        if prog.get("genre") and isinstance(prog["genre"], list):
            for g in prog["genre"]:
                mapped = self.config.get_genre_mapping(g)
                if mapped:
                    prog["genre"] = mapped
                    break
        elif prog.get("genre"):
            mapped = self.config.get_genre_mapping(prog["genre"])
            if mapped:
                prog["genre"] = mapped

        # Define gênero padrão baseado em flags
        if prog.get("live") == True:
            prog["genre"] = "live broadcast"

        return prog

    def _normalize_rating(self, prog: Dict) -> Dict:
        """Normaliza classificação indicativa para formato brasileiro"""
        rating = prog.get("rating")

        if not rating:
            return prog

        rating_map = {
            "L": "L",
            "1": "L",
            "AL": "AL",
            "10": "10",
            "12": "12",
            "14": "14",
            "16": "16",
            "18": "18",
            "AGE84": "L",
            "4+": "L",
            "AGE85": "10",
            "5+": "10",
            "AGE105": "12",
            "6+": "12",
            "AGE87": "14",
            "7+": "14",
            "AGE86": "16",
            "8+": "16",
            "AGE89": "18",
            "9+": "18",
        }

        # Remove "anos" e espaços
        rating_clean = str(rating).replace(" anos", "").strip()
        rating_clean = str(rating).replace("[", "").strip().replace("]", "").strip()

        # Mapeia
        prog["rating"] = rating_map.get(rating_clean, rating_clean)

        # Remove se for "SC" ou similar
        if prog["rating"] in [
            "AGE215",
            "S/C",
            "SC",
            "Sem Classificação",
            "no rating",
            "",
        ]:
            prog["rating"] = None

        return prog

    def process_output(self, prog: Dict) -> Dict:
        """
        Processa saída final do programa organizando título, subtítulo e descrição

        Args:
            prog: Dicionário com dados do programa processado

        Returns:
            Dicionário atualizado com formatação final
        """
        # Constantes
        SPORTS_CHANNELS = frozenset(
            [
                "sportv",
                "premiere",
                "combate",
                "espn",
                "sbt",
                "ge-tv",
                "xsports",
                "X Sports",
                "x sports",
                "x-sports",
            ]
        )
        MAX_TITLE_LENGTH = 42

        # 1. Prepara string de data do evento
        event_date_str = self._format_event_date(
            prog.get("event_date"), prog.get("phase")
        )

        # 2. Limpa e normaliza subtítulo
        prog["subtitle"] = self._clean_subtitle(prog["title"], prog.get("subtitle"))

        # 3. Reorganiza título e subtítulo baseado no contexto
        should_merge = self._should_merge_title_subtitle(
            prog["title"],
            prog.get("subtitle"),
            prog.get("episode"),
            prog["channel"],
            SPORTS_CHANNELS,
            MAX_TITLE_LENGTH,
        )

        if should_merge:
            prog["title"] = f"{prog['title']}: {prog['subtitle']}"
            prog["subtitle"] = f"{prog.get('phase') or ''}{event_date_str}".strip()
            prog["phase"] = None

        # 4. Preenche subtítulo vazio com dados contextuais
        if not prog["subtitle"] and (prog.get("event_date") or prog.get("phase")):
            prog["subtitle"] = f"{prog.get('phase') or ''}{event_date_str}".strip()
            prog["phase"] = None

        # 5. Formata descrição
        prog["description"] = self._format_description(
            prog.get("phase"), event_date_str, prog.get("description")
        )

        # 6. Aplica marcadores de transmissão (ao vivo, inédito, etc)
        prog = self._apply_broadcast_markers(prog)

        return prog

    def _format_event_date(self, event_date: str, phase: str) -> str:
        """Formata string de data do evento com ou sem vírgula"""
        if not event_date:
            return ""

        prefix = ", " if phase else ""
        return f"{prefix}realizado em {event_date}"

    def _clean_subtitle(self, title: str, subtitle: str) -> str:
        """Remove redundâncias e limpa o subtítulo"""
        if not subtitle or title == subtitle:
            return None

        # Remove título do início do subtítulo
        cleaned = re.sub(
            rf"^{re.escape(title)}\s*-?\s*", "", subtitle, flags=re.IGNORECASE
        )

        # Remove hífens e espaços das bordas
        cleaned = re.sub(r"^\s*-?\s*", "", cleaned)
        cleaned = re.sub(r"\s*-?\s*$", "", cleaned)

        return cleaned if cleaned else None

    def _should_merge_title_subtitle(
        self,
        title: str,
        subtitle: str,
        episode: int,
        channel: str,
        sports_channels: frozenset,
        max_length: int,
    ) -> bool:
        """Determina se título e subtítulo devem ser mesclados"""
        if not subtitle:
            return False

        if episode is not None:
            return False

        channel_lower = channel.lower()
        is_sports_channel = any(sc in channel_lower for sc in sports_channels)

        return is_sports_channel and len(title) <= max_length

    def _format_description(
        self, phase: str, event_date_str: str, description: str
    ) -> str:
        """Formata a descrição completa do programa"""
        parts = []

        if phase:
            parts.append(phase)

        if event_date_str:
            parts.append(event_date_str.lstrip(", "))

        if description:
            parts.append(description)

        # Une com " - " apenas se houver múltiplas partes
        if len(parts) > 1:
            return " - ".join(parts)
        elif parts:
            return parts[0]

        return ""

    def _apply_broadcast_markers(self, prog: Dict) -> Dict:
        """Aplica marcadores de tipo de transmissão ao título"""
        live_status = prog.get("live")

        # Verifica se já tem marcador no título
        if "- Ao Vivo" in prog["title"]:
            prog["genre"] = "live broadcast"
            return prog

        # Aplica marcador baseado no status
        if live_status is True:
            prog["title"] = f"{prog['title']} - ao vivo"
            prog["genre"] = "live broadcast"

        elif isinstance(live_status, str):
            if "Destaques + Estreia" in live_status:
                prog["title"] = f"{prog['title']} - Estreia"

            elif "Destaque" in live_status:
                prog["live"] = "Destaque"

            elif "inédito" in live_status or "estreia" in live_status:
                prog["title"] = f"{prog['title']} - {live_status}"

            elif "reprise" in live_status:
                prog["title"] = f"{prog['title']} - {live_status}"

            elif "VT" in live_status or "Retrô" in live_status:
                prog["title"] = f"{live_status} - {prog['title']}"

        return prog
