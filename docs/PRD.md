# Climbers Journal — Product Requirements

## Problem

Athletes who climb use generic training platforms (Strava, Garmin, intervals.icu) that don't understand climbing-specific training. Logging climbing sessions, tracking projects, and understanding how climbing fits into overall training load requires manual effort across multiple tools.

## Solution

A local-first training journal with an LLM assistant that connects to your existing training data (starting with intervals.icu) and lets you query it conversationally. Ask about your latest activity, training trends, or weekly load — the LLM fetches the data and responds.

## MVP Scope

- Chat UI (Next.js) connected to a FastAPI backend
- LLM (Kimi K2.5) with tool use to query intervals.icu
- Tools: get latest activity, get recent activities, get wellness/load data
- Runs locally, no auth, no database

## Future Direction

- Climbing-specific activity logging (grades, ascents, projects)
- Training load analytics (CTL/ATL/TSB) with climbing-aware metrics
- Database persistence, user auth, deployment
- Garmin/GPX import, interactive crag maps
