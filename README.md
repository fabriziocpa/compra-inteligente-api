# Compra Inteligente API

Backend en FastAPI para simular planes de pago de crédito vehicular bajo la
modalidad «Compra Inteligente» (método francés vencido ordinario, con cuota
inicial, cuota balón, gracia total/parcial, tasas TEA/TNA e indicadores
VAN/TIR/TCEA).

## Estructura

- `src/main.py`: punto de entrada (app FastAPI).
- `src/contexts/*`: bounded contexts (auth, clients, vehicles, loans, audit).
  - `loans/domain/services/`: motor financiero (francés, compra inteligente,
    conversión de tasas, indicadores) — documentado con las fórmulas de la
    metodología del curso.
  - `audit/`: bitácora de operaciones (toda mutación queda registrada en BD).
- `migrations/`: migraciones Alembic.
- `tests/`: pruebas unitarias (verifican los ejemplos de la separata).

## Requisitos

- Python 3.12 con [uv](https://docs.astral.sh/uv/)
- PostgreSQL 14+ corriendo en local

## Puesta en marcha (primera vez)

1. **Dependencias**

   ```bash
   uv sync
   ```

2. **Variables de entorno** — copia `.env.example` a `.env` y ajusta:

   - `DATABASE_URL`: usa un rol que exista en tu Postgres. En macOS con
     Homebrew el rol por defecto es tu usuario del sistema, sin contraseña:

     ```
     DATABASE_URL=postgresql+asyncpg://TU_USUARIO@localhost:5432/compra_inteligente
     ```

   - `JWT_SECRET_KEY`: genera uno con
     `python -c "import secrets; print(secrets.token_hex(32))"`.

3. **Base de datos** — basta con crear la BD vacía:

   ```bash
   createdb compra_inteligente
   ```

   > El API aplica las migraciones de Alembic automáticamente al arrancar
   > (`alembic upgrade head` en el lifespan), así que no hace falta correrlas
   > a mano. Si prefieres hacerlo manualmente: `uv run alembic upgrade head`.

4. **Servidor**

   ```bash
   uv run uvicorn src.main:app --reload --port 8000
   ```

   Documentación interactiva en `http://localhost:8000/docs`.

## Pruebas

```bash
uv run pytest
```

Las pruebas unitarias reproducen los 5 ejemplos del método francés de la
separata *Planes de pago (Unidad 3)* fila por fila, además de las conversiones
de tasas y los indicadores.

## Convenciones del dominio

- Año bancario de 360 días, meses de 30 (`frequency_days` por defecto 30).
- Signos: interés, cuota y amortización NEGATIVOS (egresos del deudor).
- Códigos de gracia: `S` = sin gracia, `P` = parcial (solo interés),
  `T` = total (interés capitaliza).
- Fracciones en 0..1: `"0.20"` = 20 % (cuota inicial, balón, tasas, cargos %).
