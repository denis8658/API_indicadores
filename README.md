# Pocket Option Market Intelligence API

API FastAPI para transformar dados brutos da PocketOption em inteligencia de mercado com candles, ticks, indicadores, estrutura de mercado, volume sintetico, price action, sinais e estatisticas.

## O Que Esta API Faz

Esta API funciona como uma camada REST entre clientes externos e a PocketOption API.

Ela busca dados na API de origem:

```text
https://pocketoptionapi-mainscalp-production-0434.up.railway.app
```

E entrega respostas prontas para dashboards, bots, aplicativos, IAs e outros clientes REST.

Modulos atuais:

- coleta de assets, candles e ticks
- calculo de indicadores tecnicos
- volume sintetico
- estrutura de mercado
- price action
- sinais operacionais
- cache de mercado
- endpoints de monitoramento e dashboard

## URLs

API de indicadores em producao:

```text
https://apiindicadores-production.up.railway.app
```

PocketOption API usada como origem:

```text
https://pocketoptionapi-mainscalp-production-0434.up.railway.app
```

API local:

```text
http://127.0.0.1:8000
```

## Requisitos

- Python 3.13+
- pip atualizado
- acesso de rede para a PocketOption API
- SSID da PocketOption quando a API de origem ainda nao estiver inicializada

## Instalacao

1. Clone o repositorio:

```bash
git clone https://github.com/denis8658/API_indicadores.git
cd API_indicadores
```

2. Crie e ative o ambiente virtual:

```bash
python -m venv .venv
.venv\Scripts\activate
```

3. Instale as dependencias:

```bash
pip install -r requirements.txt
```

## Variaveis De Ambiente

Copie o arquivo de exemplo:

```bash
copy .env.example .env
```

Exemplo recomendado:

```env
DEBUG=False
API_BASE_URL=https://pocketoptionapi-mainscalp-production-0434.up.railway.app
POCKET_OPTION_SSID=42["auth",{"session":"sua_sessao","isDemo":1,"uid":123456,"platform":9}]
ALLOWED_ORIGINS=*
```

Tambem e aceito:

```env
POCKET_SSID=42["auth",{"session":"sua_sessao","isDemo":1,"uid":123456,"platform":9}]
```

Observacoes:

- O SSID deve ser o texto completo iniciado por `42["auth",...]`.
- Nao use apenas o valor de `session`, porque a PocketOption API espera o payload completo.
- Se a PocketOption API de origem ja estiver inicializada e conectada, esta API consegue reutilizar essa conexao mesmo sem SSID local.

## Como Obter O SSID

1. Acesse a PocketOption pelo navegador.
2. Abra o DevTools com `F12`.
3. Va em `Network`.
4. Filtre por `WS`.
5. Abra a conexao WebSocket da PocketOption.
6. Procure uma mensagem iniciada por:

```text
42["auth"
```

7. Copie a mensagem completa, por exemplo:

```text
42["auth",{"session":"abc123","isDemo":1,"uid":123456,"platform":9}]
```

8. Configure esse valor em `POCKET_OPTION_SSID` ou `POCKET_SSID`.

## Executar Localmente

Modo simples:

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Modo desenvolvimento:

```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Documentacao automatica:

```text
http://127.0.0.1:8000/docs
http://127.0.0.1:8000/redoc
```

## Passo A Passo Para Conectar E Buscar Dados

### 1. Verificar se a nossa API esta online

Local:

```bash
curl http://127.0.0.1:8000/health
```

Producao:

```bash
curl https://apiindicadores-production.up.railway.app/health
```

Resposta esperada:

```json
{"status":"ok","service":"pocket-option-market-intelligence"}
```

### 2. Verificar se a camada de mercado esta pronta

```bash
curl http://127.0.0.1:8000/market/health
```

Resposta esperada:

```json
{"status":"ok","market":"ready"}
```

### 3. Verificar se a PocketOption API de origem esta conectada

```bash
curl https://pocketoptionapi-mainscalp-production-0434.up.railway.app/health
```

Resposta esperada quando a origem esta pronta:

```json
{
  "status": "healthy",
  "connected": true,
  "client_initialized": true,
  "authenticated": true,
  "websocket_connected": true
}
```

Se `connected` ou `client_initialized` estiver `false`, configure `POCKET_OPTION_SSID` nesta API ou inicialize a PocketOption API de origem com o SSID completo.

### 4. Buscar lista de ativos

Local:

```bash
curl http://127.0.0.1:8000/market/assets
```

Producao:

```bash
curl https://apiindicadores-production.up.railway.app/market/assets
```

Resposta resumida:

```json
{
  "assets": [
    {"symbol": "EURUSD", "name": 1},
    {"symbol": "EURUSD_otc", "name": 66}
  ]
}
```

### 5. Buscar candles e alimentar o cache

```bash
curl "http://127.0.0.1:8000/market/candles?symbol=EURUSD"
```

Em producao:

```bash
curl "https://apiindicadores-production.up.railway.app/market/candles?symbol=EURUSD"
```

O endpoint:

- chama a PocketOption API em `POST /api/candles`
- usa `asset`, `timeframe=60` e `count=500`
- calcula indicadores
- atualiza o cache local
- retorna os ultimos 20 candles processados

Resposta resumida:

```json
{
  "candles": [
    {
      "asset": "EURUSD",
      "timeframe": 60,
      "open": 1.14147,
      "high": 1.14147,
      "low": 1.14147,
      "close": 1.14147,
      "timestamp": 1783832220,
      "ema_9": 1.14147,
      "rsi_14": null,
      "sar": 1.14147,
      "synthetic_volume": 1.0
    }
  ]
}
```

### 6. Buscar tick atual de um ativo

Depois de buscar candles, a PocketOption API ativa o stream do ativo. Entao chame:

```bash
curl "http://127.0.0.1:8000/market/ticks?symbol=EURUSD"
```

Em producao:

```bash
curl "https://apiindicadores-production.up.railway.app/market/ticks?symbol=EURUSD"
```

Resposta resumida:

```json
{
  "ticks": [
    {
      "asset": "EURUSD",
      "price": 1.14147,
      "timestamp": 1783832220,
      "source": "stream"
    }
  ]
}
```

### 7. Buscar dashboard

O dashboard usa os dados que ja foram carregados no cache.

```bash
curl "http://127.0.0.1:8000/market/dashboard?symbol=EURUSD"
```

Em producao:

```bash
curl "https://apiindicadores-production.up.railway.app/market/dashboard?symbol=EURUSD"
```

Se ainda nao chamou `/market/candles`, o dashboard pode retornar:

```json
{"dashboard":{"symbol":"EURUSD","status":"empty"}}
```

Depois de buscar candles, a resposta esperada e:

```json
{
  "dashboard": {
    "symbol": "EURUSD",
    "status": "ok",
    "indicator_count": 38,
    "cache": {
      "candles": {"EURUSD": 97},
      "ticks": {},
      "indicators": {"EURUSD": 97}
    }
  }
}
```

### 8. Buscar sinais

Primeiro carregue candles:

```bash
curl "http://127.0.0.1:8000/market/candles?symbol=EURUSD"
```

Depois busque sinais:

```bash
curl "http://127.0.0.1:8000/market/signals?symbol=EURUSD"
```

Em producao:

```bash
curl "https://apiindicadores-production.up.railway.app/market/signals?symbol=EURUSD"
```

Resposta resumida:

```json
{
  "signals": [
    {
      "symbol": "EURUSD",
      "action": "NONE",
      "score": 0.0,
      "confidence": 0.0,
      "expiration": 30
    }
  ]
}
```

## Fluxo Recomendado

Use esta ordem:

```text
1. GET /health
2. GET /market/health
3. GET /market/assets
4. GET /market/candles?symbol=EURUSD
5. GET /market/ticks?symbol=EURUSD
6. GET /market/dashboard?symbol=EURUSD
7. GET /market/signals?symbol=EURUSD
```

## Endpoints Principais

Saude:

- `GET /`
- `GET /health`
- `GET /market/health`

Mercado:

- `GET /market/assets`
- `GET /market/candles?symbol=EURUSD`
- `GET /market/ticks?symbol=EURUSD`
- `GET /market/indicators?symbol=EURUSD`
- `GET /market/features?symbol=EURUSD`
- `GET /market/market-structure?symbol=EURUSD`
- `GET /market/price-action`
- `GET /market/signals?symbol=EURUSD`
- `GET /market/statistics`
- `GET /market/activity?symbol=EURUSD`
- `GET /market/dashboard?symbol=EURUSD`
- `GET /market/cache`
- `GET /market/history?symbol=EURUSD`
- `GET /market/trend?symbol=EURUSD`
- `GET /market/volatility?symbol=EURUSD`
- `GET /market/momentum?symbol=EURUSD`
- `GET /market/confluence?symbol=EURUSD`
- `GET /market/order-blocks`
- `GET /market/liquidity`
- `GET /market/support-resistance`
- `GET /market/signal-history?symbol=EURUSD&timeframe=60`
- `GET /market/backtest?symbol=EURUSD&timeframe=60`

Todos os endpoints analiticos por ativo aceitam `timeframe` em segundos. O valor padrao continua sendo `60`; por exemplo:

```bash
curl "http://127.0.0.1:8000/market/trend?symbol=EURUSD&timeframe=300"
```

## Analises E Persistencia

O pipeline calcula tendencia, momentum, volatilidade, price action, BOS, CHoCH, pivots, suporte, resistencia, liquidez, order blocks e confluencia. Endpoints, sinais e backtest usam os mesmos calculos.

Candles e sinais sao persistidos em SQLite no caminho definido por `DATABASE_PATH`. Quando novos candles chegam, sinais vencidos sao avaliados automaticamente como `WIN`, `LOSS` ou `DRAW`; `/market/statistics` usa esses resultados reais. `/market/backtest` executa uma simulacao historica sem gravar operacoes artificiais no historico real.

## Exemplo Com Python

```python
import requests

base_url = "https://apiindicadores-production.up.railway.app"
symbol = "EURUSD"

health = requests.get(f"{base_url}/health", timeout=10)
print(health.json())

assets = requests.get(f"{base_url}/market/assets", timeout=30)
print(assets.json())

candles = requests.get(f"{base_url}/market/candles", params={"symbol": symbol}, timeout=60)
print(candles.json())

dashboard = requests.get(f"{base_url}/market/dashboard", params={"symbol": symbol}, timeout=30)
print(dashboard.json())

signals = requests.get(f"{base_url}/market/signals", params={"symbol": symbol}, timeout=30)
print(signals.json())
```

## Troubleshooting

### `/market/candles` retorna 500

Verifique:

1. Se a PocketOption API esta online:

```bash
curl https://pocketoptionapi-mainscalp-production-0434.up.railway.app/health
```

2. Se a PocketOption API esta conectada:

```json
{
  "connected": true,
  "client_initialized": true,
  "authenticated": true,
  "websocket_connected": true
}
```

3. Se o SSID esta configurado corretamente:

```env
POCKET_OPTION_SSID=42["auth",{"session":"...","isDemo":1,"uid":...,"platform":9}]
```

4. Se o deploy no Railway esta usando a ultima versao do GitHub.

### Dashboard retorna `empty`

Chame primeiro:

```bash
curl "https://apiindicadores-production.up.railway.app/market/candles?symbol=EURUSD"
```

Depois:

```bash
curl "https://apiindicadores-production.up.railway.app/market/dashboard?symbol=EURUSD"
```

### Ticks retornam vazio

Chame primeiro candles para ativar o stream do ativo na PocketOption API:

```bash
curl "https://apiindicadores-production.up.railway.app/market/candles?symbol=EURUSD"
```

Depois:

```bash
curl "https://apiindicadores-production.up.railway.app/market/ticks?symbol=EURUSD"
```

## Testes

Para validar a API localmente:

```bash
pytest -q
```

## Deploy

Para subir em Railway, Render, Fly.io ou VPS, use a porta fornecida pela plataforma e configure host `0.0.0.0`.

Comando de startup:

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Variaveis importantes no Railway:

```env
API_BASE_URL=https://pocketoptionapi-mainscalp-production-0434.up.railway.app
POCKET_OPTION_SSID=42["auth",{"session":"...","isDemo":1,"uid":...,"platform":9}]
ALLOWED_ORIGINS=*
```

## Estrutura Do Projeto

```text
app/
  cache/
  collectors/
  config/
  indicators/
  market_structure/
  price_action/
  routers/
  schemas/
  services/
  synthetic_volume/
  main.py
requirements.txt
README.md
tests/
```
