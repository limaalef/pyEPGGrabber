#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Brasil EPG Grabber - Versão Python 1.2.0
Conversor de EPG de múltiplas fontes para formato XMLTV
"""

import argparse
import json
from pathlib import Path
from datetime import datetime, timedelta
import sys
from colorama import Fore, Back, Style, init

from epg_config import EPGConfig
from epg_fetcher import EPGFetcher
from epg_processor import EPGProcessor
from epg_writer import EPGWriter
from epg_logger import EPGLogger

init(autoreset=True)


class EPGGrabber:
    """Classe principal do EPG Grabber"""

    def __init__(self, config_dir: str = None):
        self.config_dir = Path(config_dir) if config_dir else Path(__file__).parent
        self.config = EPGConfig(self.config_dir)
        self.logger = EPGLogger(self.config_dir / "log_epg.log")
        self.fetcher = EPGFetcher(self.config)
        self.processor = EPGProcessor(self.config)
        self.writer = EPGWriter(self.config)

    def grab_epg(
        self,
        days: int = 0,
        services: list = None,
        channel_id: int = None,
        output: str = None,
    ):
        """
        Captura dados de EPG

        Args:
            days: Número de dias para capturar (0 = hoje)
            services: Lista de serviços a usar (None = todos)
            channel_id: ID específico de canal (para Globoplay)
        """
        if services is None:
            services = self.config.get_all_services()

        # Calcula total de tarefas para barra de progresso
        total_tasks = self._calculate_total_tasks(services, days)

        # Inicia log com total
        self.logger.start_log(total_tasks)

        # Carrega configurações de serviços
        all_programs = []

        # Para cada serviço configurado
        try:
            for service_name in services:
                service_config = self.config.load_service_config(service_name)

                # Se o serviço não usa loop, captura apenas o dia final
                if service_config.get("no_loop", False):
                    day_range = [days]
                else:
                    day_range = range(days + 1)

                # Cria lista de IDs
                has_placeholder = "LISTACANAIS" in service_config.get("api_url", "")
                get_list_to_url = service_config.get("list_url", False) and has_placeholder

                if get_list_to_url:
                    channel_list = [{"id": "0"}]
                    channel_list_url = service_config.get("channels")
                else:
                    channel_list_url = None
                    channel_list = (
                    [{"id": channel_id}] if channel_id else
                    service_config.get("channels") or [{"id": "0"}]
                )
            
                # Navega pela lista de IDs
                for each_channel in channel_list:
                    list_id_channel = channel_list_url if get_list_to_url else each_channel.get("id")
                    
                    # Captura dados para cada dia
                    for day in day_range:
                        channel_name = each_channel.get("name")
                        self.logger.log_channel_start(channel_name, day, len(day_range))
                        try:
                            # Faz requisição à API
                            data = self.fetcher.fetch(
                                service_config, day, list_id_channel
                            )

                            # Extrai programas dos dados
                            programs = self.fetcher.extract_programs(
                                data, service_config, channel_name
                            )

                            self.logger.log_programs_collected(len(programs))

                            # Processa cada programa
                            for program in programs:
                                processed = self.processor.process_program(
                                    program, service_config
                                )
                                if processed:
                                    all_programs.append(processed)
                                    self.logger.log_program_processed()

                            self.logger.update_progress()

                        except Exception as e:
                            self.logger.log_error(f"{service_config['name']} - {channel_name} (dia +{day}): {str(e)}")
                            self.logger.update_progress()
                            continue
                    
                    self.logger.log_channel_completed(channel_name)

            # Ordena programas por canal e horário
            all_programs.sort(key=lambda x: (x["channel"], x["start_time"]))

            # Gera saída conforme modo escolhido
            name = (
                service_config.get("name").replace(" ", "_").lower()
                if len(services) <= 1
                else None
            )
            output_path = self.writer.write_xml(
                all_programs, service_name=name, output_path=output
            )

            self.logger.log_success(f"XML gerado: {output_path}")
            
        finally:
            # Garante que log seja finalizado mesmo com erro
            self.logger.end_log()
        
        return output_path

    def _format_text(self, programs):
        """Formata programas como texto para Telegram"""
        output = []
        current_date = None

        for prog in programs:
            if prog["date"] != current_date:
                output.append(f"\n<i>{prog['date']}</i>")
                current_date = prog["date"]

            output.append(f"<b>{prog['start_time']}</b> {prog['title']}")

        return "\n".join(output)

    def _calculate_total_tasks(self, services: list, days: int) -> int:
        """Calcula número total de requisições que serão feitas"""
        total = 0
        
        for service_name in services:
            service_config = self.config.load_service_config(service_name)
            channels = service_config.get('channels', [])
            
            if channels:
                num_channels = len(channels)
                batch_size = service_config.get('batch_size')
                
                if 'LISTACANAIS' in service_config['api_url']:
                    # Requisições em lote
                    if batch_size:
                        batches = (num_channels + batch_size - 1) // batch_size
                    else:
                        batches = 1
                    total += batches * (days + 1)
                else:
                    # Requisição individual por canal
                    total += num_channels * (days + 1)
            else:
                # API que retorna todos os canais
                total += (days + 1)
        
        return total

def main():
    """Função principal com argumentos de linha de comando"""
    # Exibe banner
    print_banner()
    
    parser = argparse.ArgumentParser(
        description="Brasil EPG Grabber - Captura dados de programação de TV"
    )

    parser.add_argument(
        "-d",
        "--days",
        type=int,
        default=0,
        help="Número de dias para capturar (padrão: 0 = hoje)",
    )

    parser.add_argument(
        "-s", "--service", type=str, help="Nome do serviço específico (ex: globoplay)"
    )

    parser.add_argument(
        "-c", "--channel", type=int, help="ID do canal (para Globoplay)"
    )

    parser.add_argument("-o", "--output", type=str, help="Caminho de saída do XML")

    parser.add_argument("--config-dir", type=str, help="Diretório de configurações")

    args = parser.parse_args()

    # Cria instância do grabber
    grabber = EPGGrabber(config_dir=args.config_dir)

    # Determina serviços a usar
    services = [args.service] if args.service else None
    
    # Exibe resumo antes de iniciar
    print_execution_summary(services, args.days, args.channel, args.output)

    # Executa captura
    try:
        grabber.grab_epg(
            days=args.days,
            services=services,
            channel_id=args.channel,
            output=args.output,
        )

    except KeyboardInterrupt:
        print("\n\n✗ Operação cancelada pelo usuário")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Erro: {str(e)}")
        sys.exit(1)

def print_banner():
    """Exibe banner do programa"""
    banner = f"""
{Back.MAGENTA}{Fore.LIGHTWHITE_EX}{'='*80}{Style.RESET_ALL}
{Back.MAGENTA}{Fore.LIGHTWHITE_EX}{'  Brasil EPG Grabber - Versão Python 1.2.0':^80}{Style.RESET_ALL}
{Back.MAGENTA}{Fore.LIGHTWHITE_EX}{'  Conversor de EPG para formato XMLTV':^80}{Style.RESET_ALL}
{Back.MAGENTA}{Fore.LIGHTWHITE_EX}{'='*80}{Style.RESET_ALL}
"""
    print(banner)

def print_execution_summary(services: list, days: int, channel_id: int = None, output: str = None):
    """Exibe resumo da execução solicitada"""
    print(f"{Fore.LIGHTMAGENTA_EX}{'RESUMO DA EXECUÇÃO':^80}{Style.RESET_ALL}")
    print(f"{Fore.LIGHTMAGENTA_EX}{'-'*80}{Style.RESET_ALL}")
    
    # Serviços
    if services and len(services) == 1:
        print(f"{Fore.WHITE}  Serviço:          {Fore.LIGHTCYAN_EX}{services[0]}{Style.RESET_ALL}")
    elif services:
        print(f"{Fore.WHITE}  Serviços:         {Fore.LIGHTCYAN_EX}{', '.join(services)}{Style.RESET_ALL}")
    else:
        print(f"{Fore.WHITE}  Serviços:         {Fore.LIGHTCYAN_EX}Todos disponíveis{Style.RESET_ALL}")
    
    # Dias
    if days == 0:
        days_text = "Hoje"
    elif days == 1:
        days_text = "Hoje + 1 dia"
    else:
        days_text = f"Hoje + {days} dias"
    print(f"{Fore.WHITE}  Período:          {Fore.LIGHTCYAN_EX}{days_text}{Style.RESET_ALL}")
    
    # Canal específico
    if channel_id:
        print(f"{Fore.WHITE}  Canal específico: {Fore.LIGHTCYAN_EX}ID {channel_id}{Style.RESET_ALL}")
    
    # Saída
    if output:
        print(f"{Fore.WHITE}  Arquivo de saída: {Fore.LIGHTCYAN_EX}{output}{Style.RESET_ALL}")
    else:
        print(f"{Fore.WHITE}  Arquivo de saída: {Fore.LIGHTCYAN_EX}(diretório atual){Style.RESET_ALL}")
    
    print(f"{Fore.LIGHTMAGENTA_EX}{'-'*80}{Style.RESET_ALL}\n")

if __name__ == "__main__":
    main()
