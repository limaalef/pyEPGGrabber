"""
Módulo de logging com barra de progresso e estatísticas
"""

from pathlib import Path
from datetime import datetime
from typing import Optional
from tqdm import tqdm
import time

class EPGLogger:
    """Logger com barra de progresso e estatísticas detalhadas"""
    
    def __init__(self, log_path: Path):
        self.log_path = Path(log_path)
        self.start_time = None
        self.stats = {
            'channels_processed': 0,
            'programs_collected': 0,
            'programs_processed': 0,
            'errors': 0,
            'api_calls': 0
        }
        self.progress_bar = None
    
    def start_log(self, total_tasks: int = 100):
        """
        Inicia log e barra de progresso
        
        Args:
            total_tasks: Número total de tarefas (requisições esperadas)
        """
        self.start_time = datetime.now()
        timestamp = self.start_time.strftime('%Y-%m-%d %H:%M:%S')
        
        # Cria barra de progresso
        self.progress_bar = tqdm(
            total=total_tasks,
            desc="Capturando EPG",
            unit="req",
            bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}, {rate_fmt}] [ETA {remaining}]',
            ncols=100
        )
        
        # Log em arquivo
        msg = f"\n{'='*80}\nInício: {timestamp}\n{'='*80}\n"
        self._write(msg)
    
    def update_progress(self, description: str = None, increment: int = 1):
        """
        Atualiza barra de progresso
        
        Args:
            description: Descrição atual (opcional)
            increment: Quantidade a incrementar
        """
        if self.progress_bar:
            if description:
                self.progress_bar.set_description(description)
            self.progress_bar.update(increment)
    
    def increment_stat(self, stat_name: str, value: int = 1):
        """Incrementa estatística específica"""
        if stat_name in self.stats:
            self.stats[stat_name] += value
    
    def log_channel_start(self, channel_name: str, day: int, total_days: int):
        """Log de início de processamento de canal"""
        desc = f"{channel_name} (Dia {day+1}/{total_days})"
        self.update_progress(desc)
        self.increment_stat('api_calls')
    
    def log_programs_collected(self, count: int):
        """Registra programas coletados da API"""
        self.increment_stat('programs_collected', count)
    
    def log_program_processed(self):
        """Registra programa processado com sucesso"""
        self.increment_stat('programs_processed')
    
    def log_channel_completed(self, channel_name: str):
        """Log de conclusão de canal"""
        self.increment_stat('channels_processed')
    
    def log_error(self, message: str):
        """Registra erro"""
        self.increment_stat('errors')
        error_msg = f"[ERRO] {message}"
        
        # Imprime abaixo da barra de progresso
        if self.progress_bar:
            self.progress_bar.write(f"❌ {message}")
        
        self._write(error_msg + '\n')
    
    def log_warning(self, message: str):
        """Registra aviso"""
        if self.progress_bar:
            self.progress_bar.write(f"⚠️  {message}")
        self._write(f"[AVISO] {message}\n")
    
    def log_success(self, message: str):
        """Registra sucesso"""
        if self.progress_bar:
            self.progress_bar.write(f"✓ {message}")
        self._write(f"[OK] {message}\n")
    
    def get_elapsed_time(self) -> str:
        """Retorna tempo decorrido formatado"""
        if not self.start_time:
            return "00:00:00"
        
        elapsed = datetime.now() - self.start_time
        hours, remainder = divmod(int(elapsed.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    def get_stats_summary(self) -> str:
        """Retorna resumo das estatísticas"""
        return (
            f"Requisições: {self.stats['api_calls']} | "
            f"Canais: {self.stats['channels_processed']} | "
            f"Coletados: {self.stats['programs_collected']} | "
            f"Processados: {self.stats['programs_processed']} | "
            f"Erros: {self.stats['errors']}"
        )
    
    def end_log(self):
        """Finaliza log com estatísticas completas"""
        if self.progress_bar:
            self.progress_bar.close()
        
        elapsed_time = self.get_elapsed_time()
        end_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Calcula taxa de processamento com proteção contra divisão por zero
        total_seconds = 0
        rate_per_second = 0
        avg_time_per_program = 0
        
        if self.start_time:
            total_seconds = (datetime.now() - self.start_time).total_seconds()
            
            if total_seconds > 0 and self.stats['programs_processed'] > 0:
                rate_per_second = self.stats['programs_processed'] / total_seconds
                avg_time_per_program = (total_seconds / self.stats['programs_processed']) * 1000
        
        # Monta relatório final
        report = f"""
{'='*80}
RELATÓRIO FINAL
{'='*80}
Término: {end_time}
Tempo total: {elapsed_time}

ESTATÍSTICAS:
  Requisições à API:     {self.stats['api_calls']:>6}
  Canais processados:    {self.stats['channels_processed']:>6}
  Programas coletados:   {self.stats['programs_collected']:>6}
  Programas processados: {self.stats['programs_processed']:>6}
  Erros encontrados:     {self.stats['errors']:>6}
  
DESEMPENHO:
  Taxa média: {rate_per_second:.2f} programas/segundo
  Tempo médio por programa: {(total_seconds / self.stats['programs_processed'] * 1000):.2f}ms
{'='*80}
"""
        
        print(report)
        self._write(report)
    
    def _write(self, message: str):
        """Escreve no arquivo de log"""
        try:
            with open(self.log_path, 'a', encoding='utf-8') as f:
                f.write(message)
        except Exception as e:
            print(f"Erro ao escrever log: {e}")