# Pocket Option Market Intelligence API

API FastAPI profissional para transformar dados brutos da Pocket Option em inteligência de mercado com indicadores, estrutura de mercado, volume sintético, price action, sinais e estatísticas.

## O que esta API faz

Esta API funciona como um servidor de inteligência de mercado. Ela recebe ou processa dados de mercado e devolve respostas estruturadas para dashboards, bots, aplicativos mobile, IA e outros clientes REST.

Os módulos atuais incluem:
- coleta e preparação de candles
- cálculo de indicadores técnicos
- volume sintético
- estrutura de mercado
- sinais operacionais
- cache de mercado
- endpoints de monitoramento e dashboard

## Requisitos

- Python 3.13+
- pip atualizado
- rede com acesso à API de origem configurada no projeto

## Instalação

1. Clone o repositório:
```bash
git clone https://github.com/denis8658/API_indicadores.git
cd API_indicadores
```

2. Crie um ambiente virtual (opcional, mas recomendado):
```bash
python -m venv .venv
.venv\Scripts\activate
```

3. Instale as dependências:
```bash
pip install -r requirements.txt
```

## Variáveis de ambiente

Copie o arquivo de exemplo e ajuste conforme necessário:
```bash
copy .env.example .env
```

Exemplo de conteúdo:
```env
DEBUG=False
DATABASE_URL=postgresql://user:pass@host:port/db
API_PORT=8000
API_HOST=0.0.0.0
SECRET_KEY=seu-secret-aleatorio
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

## Executar localmente

### Modo simples
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Modo com reload para desenvolvimento
```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

A API ficará disponível em:
- http://127.0.0.1:8000
- http://localhost:8000

## Documentação automática

O FastAPI gera automaticamente:
- Swagger: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

## Endpoints principais

### Saúde
- GET /health
- GET /

### Mercado
- GET /market/assets
- GET /market/candles
- GET /market/ticks
- GET /market/indicators
- GET /market/features
- GET /market/market-structure
- GET /market/price-action
- GET /market/signals
- GET /market/statistics
- GET /market/activity
- GET /market/dashboard
- GET /market/cache
- GET /market/history
- GET /market/trend
- GET /market/volatility
- GET /market/momentum
- GET /market/confluence
- GET /market/order-blocks
- GET /market/liquidity
- GET /market/support-resistance
- GET /market/health

## Exemplos de uso

### Verificar se a API está online
```bash
curl http://127.0.0.1:8000/health
```

Resposta esperada:
```json
{"status":"ok","service":"pocket-option-market-intelligence"}
```

### Buscar o dashboard
```bash
curl http://127.0.0.1:8000/market/dashboard
```

### Buscar candles
```bash
curl "http://127.0.0.1:8000/market/candles?symbol=EURUSD"
```

### Buscar sinais
```bash
curl "http://127.0.0.1:8000/market/signals?symbol=EURUSD"
```

## Exemplo com Python

```python
import requests

base_url = "http://127.0.0.1:8000"

health = requests.get(f"{base_url}/health", timeout=10)
print(health.json())

dashboard = requests.get(f"{base_url}/market/dashboard", timeout=10)
print(dashboard.json())
```

## Testes

Para validar a API localmente:
```bash
pytest -q
```

## Estrutura do projeto

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
.tests/
```

## Observações importantes

- A API é projetada para funcionar como camada de inteligência de mercado.
- A coleta de dados da Pocket Option deve respeitar o fluxo de sessão e o uso do SSID quando necessário.
- Em ambientes de produção, defina corretamente as origens permitidas no CORS.
- O projeto pode ser expandido com integração real aos dados da fonte, cache mais avançado, persistência e autenticação.

## Deploy

Para subir em ambientes como Railway, Render, Fly.io ou VPS, use a porta fornecida pela plataforma e configure o host para 0.0.0.0.

Exemplo de comando de startup:
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

## Suporte

Para dúvidas ou melhorias, abra uma issue no repositório GitHub ou entre em contato com o mantenedor.
