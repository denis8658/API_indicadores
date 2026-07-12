# Pocket Option Market Intelligence API

API FastAPI profissional para transformar dados brutos da Pocket Option em inteligência de mercado com indicadores, estrutura de mercado, volume sintético, price action, sinais e estatísticas.

## Executar

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Endpoints principais

- GET /health
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
