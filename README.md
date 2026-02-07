# EdgeFinder

EdgeFinder fournit un tableau de bord pour analyser les probabilités de matchs et repérer des value bets.

## Prérequis

- Docker + Docker Compose (recommandé).
- Optionnel : Python 3.11+ et Node.js 20+ pour un lancement sans Docker.

## Installation (avec Docker)

1. Copiez le fichier d'exemple pour vos variables d'environnement :

   ```bash
   cp .env.example .env
   ```

2. Renseignez vos clés API dans `.env` :

   - `FOOTBALL_API_KEY` : clé pour l'API football.
   - `ODDS_API_KEY` : clé pour l'API de cotes.
   - `DATABASE_URL` : URL SQLAlchemy (par défaut en SQLite dans un volume Docker).

3. Lancez l'application :

   ```bash
   docker compose up --build
   ```

4. Accédez aux services :

   - Frontend : http://localhost:5173
   - API backend : http://localhost:8000

## Installation locale (sans Docker)

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example ../.env
# Éditez ../.env avec vos clés API
uvicorn main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

## Configuration des clés API

Les clés sont chargées via `FOOTBALL_API_KEY` et `ODDS_API_KEY`. Sans ces variables, l'API renverra une erreur au démarrage. Renseignez-les dans votre fichier `.env` (ou via les variables d'environnement de votre système) avant de démarrer l'application.
