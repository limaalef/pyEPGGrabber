"""
Brasil EPG Grabber - Versão Python 1.2.0
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

VERSION = "2.0.0"

os.system("cls" if os.name == "nt" else "clear")


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
            self.logger.interface_subtitle("")
            self.logger.interface_item("XML salvo em", output_path)
            self.logger.interface_subtitle("")

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
        print("\n\n✗ Operação cancelada pelo usuário")
        sys.exit(1)
    except Exception as e:
        EPGLogger.log_exception(e, "Erro")


def print_banner():
    """Exibe banner do programa"""
    temp_logger = EPGLogger()
    cols = shutil.get_terminal_size().columns

    # Linha 1
    temp_logger.interface_item("")
    temp_logger.interface_centered_text(
        "Brasil EPG Grabber", Colors.SECONDARY_TEXT_COLOR
    )

    # Linha 2
    temp_logger.interface_centered_text(
        "Extração e conversão de EPG para formato XMLTV"
    )
    temp_logger.interface_item("")

    # Linha 3
    linha3_1 = "v"
    linha3_2 = VERSION
    linha3_3 = "    @limaalef"
    spaces_linha3 = f" " * math.floor(
        max(cols - len(linha3_1) - len(linha3_2) - len(linha3_3), 0) / 2
    )
    adjust_linha3 = " " * (
        cols - len(linha3_1) - len(linha3_2) - len(linha3_3) - len(spaces_linha3) * 2
    )
    linha3 = f"{Colors.BG_COLOR}{Colors.PRIMARY_TEXT_COLOR}{spaces_linha3}{linha3_1}{Colors.HIGHLIGHT_TEXT_COLOR}{linha3_2}{Colors.PRIMARY_TEXT_COLOR}{linha3_3}{spaces_linha3}{adjust_linha3}"
    print(linha3)


def print_execution_summary(
    services: list, days: int, channel_id: int = None, output: str = None
):
    """Exibe resumo da execução solicitada"""
    temp_logger = EPGLogger()

    # Titulo
    temp_logger.interface_subtitle("Resumo da execução")

    # Serviços
    if services and len(services) == 1:
        temp_logger.interface_item("Serviço", services[0])
    elif services:
        temp_logger.interface_item("Serviços", ", ".join(services))
    else:
        temp_logger.interface_item("Serviços", "Todos disponíveis")

    # Dias
    if days == 0:
        days_text = "Hoje"
    elif days == 1:
        days_text = "Hoje + 1 dia"
    else:
        days_text = f"Hoje + {days} dias"

    temp_logger.interface_item("Período", days_text)

    # Canal específico
    if channel_id:
        temp_logger.interface_item("Canal específico", f"ID {channel_id}")

    # Saída
    if output:
        temp_logger.interface_item("Arquivo de saída", output)
    else:
        temp_logger.interface_item("Arquivo de saída", "(diretório atual)")

    # Base
    temp_logger.interface_subtitle("Execução do programa")


if __name__ == "__main__":
    main()
