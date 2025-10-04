![GitHub last commit](https://img.shields.io/github/last-commit/limaalef/pyEPGGrabber?logo=github)

# pyEPGGrabber

Conversor de EPG (Electronic Program Guide) de múltiplas fontes para formato XMLTV.

Criado a partir de um script feito por mim originalmente em Powershell e convertido para Python utilizando o Claude AI.
Todo o código foi ajustado e melhorado por mim, garantindo um bom funcionamento com diversos serviços.

## Estrutura de Arquivos

```
pyEPGGrabber/
├── epg.py                 # Script principal
├── epg_config.py          # Gerenciador de configurações
├── epg_fetcher.py         # Requisições às APIs
├── epg_processor.py       # Processamento de dados
├── epg_writer.py          # Geração XML e logs
├── services/              # Configurações de APIs
│   ├── maissbt.yaml
│   ├── uolplay.yaml
└── mappings.yaml         # Dicionários de mapeamento
```

## Instalação

```bash
# Instalar dependências
pip install -r requirements.txt

# Clonar ou copiar os arquivos para um diretório
```

## Configuração

### 1. Arquivo de Serviço (services/*.yaml)

Exemplo de configuração:

```
api_url: https://api.exemplo.com/epg?date=ANO-MES-DIA&id=IDCANAL

service_name: MeuServico

headers:
  Accept: "*/*"
  User-Agent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"

channels:                    # Opcional: Utilize esta opção se API retornar um canal por requisição ou para listar os IDs na URL (setar true em 'use_list_in_url')
  - id: 123                  # ID que será inserido na URL no local da variável 'IDCANAL' ou como lista na variável 'LISTACANAIS'
    name: Canal 1            # Opcional: Se a API não retornar o nome do canal
  - id: 456
    name: Canal 2

target_channels:             # Opcional: Se a API retornar todos os canais disponíveis, opção para filtrar os canais desejados
  - canal1
  - canal2
  - canal3

api_level_1: data.programs   # Caminho do JSON até o nome do canal, caso esteja nível acima
api_level_2: schedule.items  # Caminho do JSON até a lista de programas

channel: channel.slug
program_title: title
subtitle: metadata
description: synopsis
start_time: start_time
end_time: end_time
live: liveBroadcast
duration: durationInMinutes
rating: contentRating
rating_criteria: contentRatingCriteria
rating_auto: selfRatedContent
season: seasonNumber
episode: episodeNumber
tags: tags
genre: macros.genre

timezone: "America/Sao_Paulo"
no_loop: false              # Ativar esta opção caso a API não permita definir uma quantidade de dias ou data
use_list_in_url: true       # Ao ativar esta opção a lista de canais será integrada a URL no local da variável "LISTACANAIS": canal1,canal2...
```

**Variáveis disponíveis na URL:**
- `ANO-MES-DIA` → substituído por data no formato YYYY-MM-DD
- `DIA-MES-ANO` → substituído por data no formato DD-MM-YYYY
- `LISTACANAIS` → substituído por lista de canais definida em channels
- `QTDHORAS` → total de horas (dias × 24)
- `QTDDIAS` → total de dias
- `UNIXTIMESTART` → timestamp Unix do início do dia
- `UNIXTIMEEND` → timestamp Unix do fim do dia
- `IDCANAL` → ID do canal (quando fornecido)

### 2. Mapeamentos (mappings.yaml)

Já fornecido com dicionários de:
- Competições esportivas
- Programas de TV
- Gêneros XMLTV

## Uso

### Linha de Comando

```bash
# Capturar EPG de hoje
python epg.py

# Capturar 7 dias de EPG
python epg.py -d 7

# Usar serviço específico
python epg.py -s maissbt -d 3

# Especificar arquivo de saída
python epg.py -o "/caminho/para/epg.xml"
```

### Parâmetros

- `-d, --days`: Número de dias para capturar (padrão: 1 = hoje)
- `-s, --service`: Nome do serviço específico
- `-c, --channel`: ID do canal (para APIs específicas)
- `-o, --output`: Caminho do arquivo de saída
- `--config-dir`: Diretório de configurações

### Como Módulo Python

```python
from epg_grabber import EPGGrabber

# Criar instância
grabber = EPGGrabber()

# Capturar 3 dias de EPG
xml_path = grabber.grab_epg(days=3, output_mode='xml')
print(f"XML gerado: {xml_path}")

# Usar serviço específico
programs = grabber.grab_epg(
    days=1,
    services=['globoplay']
)
```

## Formato XMLTV Gerado

O XML segue o padrão XMLTV com:

```xml
<?xml version="1.0" encoding="utf-8"?>
<tv generator-info-name="@limaalef" generator-info-url="http://limaalef.com">
  <channel id="globo">
    <display-name lang="pt">globo</display-name>
  </channel>
  
  <programme start="20250112183000 -0300" stop="20250112193000 -0300" channel="globo">
    <title lang="pt">Jornal Nacional</title>
    <sub-title lang="pt">Edição de hoje</sub-title>
    <desc lang="pt">Principais notícias do dia</desc>
    <category lang="en">news/current affairs (general)</category>
    <rating system="Brazil">
      <value>[L]</value>
    </rating>
    <new/>
  </programme>
</tv>
```

## Processamento Automático

### Normalização de Títulos
- Adiciona sufixos "- ao vivo", "- inédito", "VT -"
- Extrai temporadas e episódios
- Identifica fases de competições esportivas

### Mapeamento Inteligente
- Converte nomes de competições para formato descrito no mapeamento
- Normaliza classificações indicativas
- Mapeia gêneros para padrão XMLTV

## Automação

### Agendar Execução Diária (Linux/macOS)

```bash
# Editar crontab
crontab -e

# Adicionar linha (executa todo dia às 3h)
0 3 * * * /usr/bin/python3 /caminho/para/epg.py -d 7
```

### Agendar Execução (Windows)

```powershell
# Criar tarefa agendada
schtasks /create /tn "EPG Grabber" /tr "python C:\caminho\para\epg.py -d 7" /sc daily /st 03:00
```

## Solução de Problemas

### Erro: "Serviço não encontrado"
- Verifique se o arquivo `.yaml` existe em `services/`
- Nome do serviço = nome do arquivo sem extensão

### Erro: "Encoding inválido"
- Verifique se o arquivo de serviço está em UTF-8
- Use editor que suporte UTF-8 (VS Code, Notepad++)

### XML vazio ou incompleto
- Verifique se a API está respondendo (teste URL no navegador)
- Confira se os caminhos em `api_level_1` e `api_level_2` estão corretos

### Datas/horários incorretos
- Confirme timezone no arquivo de configuração
- Verifique formato de data retornado pela API
- Ajuste parsing em `_parse_datetime()` se necessário

## Contribuindo

Para adicionar novos serviços:

1. Crie arquivo em `services/nome_servico.yaml`
2. Configure campos conforme documentação da API
3. Adicione headers se necessário
4. Teste: `python epg.py -s nome_servico`

Para adicionar mapeamentos:

1. Edite `mappings.yaml`
2. Adicione entradas em `competitions`, `programs` ou `genres`
3. Formato: `"Nome Original": ["Nome Formatado", "gênero"]`

## Licença

Código livre para uso pessoal e modificação.

## Créditos

- **Autor Original**: @limaalef 
- **Conversão Python**: Baseado no código PowerShell original e convertido para Python utilizando Claude AI
- **Formato**: XMLTV (http://xmltv.org)

## Suporte

Para dúvidas ou problemas, abra uma issue com:
- Comando executado
- Conteúdo do yaml do serviço utilizado
