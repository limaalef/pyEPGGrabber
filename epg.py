"""
Brasil EPG Grabber - Versão Python 2.2.3
Conversor de EPG de múltiplas fontes para formato XMLTV
"""

import argparse
import math
import os
from pathlib import Path
import shutil
import sys

from epg_config import EPGConfig
from epg_fetcher import EPGFetcher
from epg_processor import EPGProcessor
from epg_writer import EPGWriter
from epg_logger import Colors, EPGLogger, ProgressLogger

TITULO = "Brasil EPG Grabber"
SUBTITULO = "Extração e conversão de EPG para formato XMLTV"
VERSION = "2.2.3"

Colors.clear_screen()


class EPGGrabber:
    """Classe principal do EPG Grabber"""

    def __init__(self, config_dir: str = None):
        self.config_dir = Path(config_dir) if config_dir else Path(__file__).parent
        self.config = EPGConfig(self.config_dir)
        self.logger = EPGLogger()
        self.fetcher = EPGFetcher(self.config)
        self.processor = EPGProcessor(self.config)
        self.writer = EPGWriter(self.config)
        self.log_path = "log_epg.log"

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

        # Carrega configurações de serviços
        all_programs = []

        # Para cada serviço configurado
        try:
            logger0 = ProgressLogger(
                log_path=self.log_path,
                title="API requests",
                total=len(services),
                size=len(max(services, key=len)),
            )
            logger0.start()
            for service_name in services:
                service_config = self.config.load_service_config(service_name)

                # Se o serviço não usa loop, captura apenas o dia final
                if service_config.get("no_loop", False):
                    day_range = [days]
                else:
                    day_range = range(days + 1)

                # Cria lista de IDs
                has_placeholder = "LISTACANAIS" in service_config.get("api_url", "")
                get_list_to_url = (
                    service_config.get("list_url", False) and has_placeholder
                )

                if get_list_to_url:
                    channel_list = [{"id": "0"}]
                    channel_list_url = service_config.get("channels")
                else:
                    channel_list_url = None
                    channel_list = (
                        [{"id": channel_id}]
                        if channel_id
                        else service_config.get("channels") or [{"id": "0"}]
                    )

                # Navega pela lista de IDs
                for each_channel in channel_list:
                    all_items = []
                    list_id_channel = (
                        channel_list_url if get_list_to_url else each_channel.get("id")
                    )

                    # Captura dados para cada dia
                    for day in day_range:
                        channel_name = each_channel.get("name")
                        try:
                            # Faz requisição à API
                            data = self.fetcher.fetch(
                                service_config, day, list_id_channel
                            )

                            # Extrai programas dos dados
                            programs = self.fetcher.extract_programs(
                                data, service_config, channel_name
                            )

                            all_items.extend(programs)

                        except Exception as e:
                            context = f"{service_config['name']} - {channel_name} (dia +{day})"
                            self.logger.log_exception(e, context)
                            break

                    logger1 = ProgressLogger(
                        log_path=self.log_path,
                        title=service_name,
                        total=len(all_items),
                        size=len(max(services, key=len)),
                    )
                    logger1.start()

                    # Processa cada programa
                    for program in all_items:
                        processed = self.processor.process_program(
                            program, service_config
                        )
                        if processed:
                            all_programs.append(processed)

                        logger1.update()

                logger0.update()

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

        finally:
            Colors.item()
            Colors.ok(output_path, "XML salvo em")
            Colors.item()

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
            channels = service_config.get("channels", [])

            if channels:
                num_channels = len(channels)
                batch_size = service_config.get("batch_size")

                if "LISTACANAIS" in service_config["api_url"]:
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
                total += days + 1

        return total


def main():
    """Função principal com argumentos de linha de comando"""
    # Exibe banner
    Colors.print_banner(TITULO, SUBTITULO, VERSION)

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
        "-s",
        "--service",
        "--services",
        type=str,
        nargs="+",
        dest="services",
        help="Nome do serviço específico (ex: globoplay)",
    )

    parser.add_argument(
        "-c", "--channel", type=str, help="ID do canal (para Globoplay)"
    )

    parser.add_argument("-o", "--output", type=str, help="Caminho de saída do XML")

    parser.add_argument("--config-dir", type=str, help="Diretório de configurações")

    args = parser.parse_args()

    # Cria instância do grabber
    grabber = EPGGrabber(config_dir=args.config_dir)

    # Determina serviços a usar
    services = args.services

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
        Colors.warning("Operação cancelada pelo usuário")
        sys.exit(1)
    except Exception as e:
        EPGLogger.log_exception(e, "Erro")


def print_execution_summary(
    services: list, days: int, channel_id: int = None, output: str = None
):
    """Exibe resumo da execução solicitada"""
    # Titulo
    Colors.center_title("Resumo da execução")

    # Serviços
    if services and len(services) == 1:
        Colors.item("Serviço", services[0])
    elif services:
        Colors.item("Serviços", ", ".join(services))
    else:
        Colors.item("Serviços", "Todos disponíveis")

    # Dias
    if days == 0:
        days_text = "Hoje"
    elif days == 1:
        days_text = "Hoje + 1 dia"
    else:
        days_text = f"Hoje + {days} dias"

    Colors.item("Período", days_text)

    # Canal específico
    if channel_id:
        Colors.item("Canal específico", f"ID {channel_id}")

    # Saída
    if output:
        Colors.item("Arquivo de saída", output)
    else:
        Colors.item("Arquivo de saída", "(diretório atual)")

    # Base
    Colors.center_title("Execução do programa")


if __name__ == "__main__":
    main()
