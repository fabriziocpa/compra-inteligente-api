# Compra Inteligente API

Backend en FastAPI para simular planes de pago de crédito vehicular.

## Estructura básica
- `src/main.py`: punto de entrada de la API (FastAPI app)
- `src/contexts/*`: módulos de dominio (auth, clients, vehicles, loans)
- `migrations/`: migraciones Alembic

## Requisitos
- Python 3.12
- PostgreSQL

## Migraciones
Usa Alembic para crear las tablas.

```alembic upgrade head```

### Pruebas

```pytest```