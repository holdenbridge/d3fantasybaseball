# D3 Fantasy Baseball

A live fantasy baseball dashboard built by former D3 baseball players, powered by real MLB data.


[Live App](https://d3fantasybaseball.onrender.com/)

## Preview

![2025 score preview](screenshots/2025%20score.png)

## Overview

D3 Fantasy Baseball tracks a custom 4-player fantasy league and scores each owner using a weighted points system.  
The app combines MLB standings, home run leaders, strikeout leaders, and rookie WAR into a single live leaderboard.

## Scoring System

- Team wins: `1 point` per win
- Batter home runs: `2 points` per HR
- Pitcher strikeouts: `0.5 points` per strikeout
- Rookie WAR: `10 points` per WAR


## Features

- Live leaderboard with total points by owner
- Team standings chart
- Batter home run leaderboard
- Pitcher strikeout leaderboard
- Rookie WAR leaderboard
- Interactive tooltips and responsive layout
- In-memory caching with startup prefetch for faster page loads

## Tech Stack

- Backend: `FastAPI`, `Jinja2`
- Frontend: `HTML`, `D3.js`
- Data: `MLB-StatsAPI`, `pybaseball`
- Hosting: `Render`

## Project Structure

```text
.
├── app/
│   ├── main.py              # FastAPI routes + data fetching/cache logic
│   ├── templates/
│   │   └── index.html       # D3 dashboard UI
│   └── static/
│       └── avatars/         # Player avatar assets
├── requirements.txt
├── pyproject.toml
└── render.yaml
```

## Run Locally

### 1) Clone and enter the repo

```bash
git clone https://github.com/<your-username>/<your-repo>.git
cd <your-repo>
```

### 2) Install dependencies

```bash
pip install -r requirements.txt
```

### 4) Start the app

```bash
uvicorn app.main:app --reload
```

Then open: [http://127.0.0.1:8000](http://127.0.0.1:8000)

## API Endpoints

- `GET /api/standings` - MLB team win/loss standings used in scoring
- `GET /api/hr-leaders` - home run leaderboard (plus drafted-player fallback data)
- `GET /api/k-leaders` - strikeout leaderboard (plus drafted-player fallback data)
- `GET /api/war-rookies` - rookie WAR leaderboard

## Deployment

This project is configured for Render with `render.yaml`.

- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
