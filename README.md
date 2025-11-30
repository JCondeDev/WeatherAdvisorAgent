# Theophrastus - The Weather & Environmental Advisor Agent

![Architecture](./Theophrastus_thumbnail.png "Theophrastus_thumbnail")

## Overview 

Theophrastus is a multi-agent system that provides comprehensive environmental weather analysis and outdoor activity recommendations. Named after Theophrastus of Eresos-the ancient Greek philosopher known as the "Father of Botany," successor to Aristotle, and pioneer of meteorology. This intelligent agent combines real-time meteorological data with advanced risk assessment to help users make informed decisions about outdoor activities and agricultural planning.

In this system, Theophrastus serves as the central orchestrator, a prophet-philosopher who communes with a divine council of elemental deities to interpret weather patterns and provide sage counsel. Zephyr brings wind and weather data, Atlas maps the terrain, Aether assesses atmospheric dangers, Aurora illuminates the path forward with clear guidance. Through this divine communion, Theophrastus interprets celestial signs and atmospheric omens, transforming raw environmental data into actionable wisdom.

Like the ancient philosopher who studied how plants respond to seasons and weather, this agent bridges the gap between environmental science and practical wisdom, helping farmers and outdoor enthusiasts work in harmony with the natural world. 

## Problem Statement

Planning outdoor activities requires synthesizing complex environmental data from multiple sources - temperature, wind conditions, humidity, precipitation, and location-specific factors. Manual analysis of these variables is:

- Time-Consuming: Gathering data from multiple weather sources and cross-referencing conditions takes significant effort.
Error-Prone: Missing critical risk factors can lead to unsafe decisions.
- Location-Limited: Finding optimal locations for specific activities requires local knowledge that may not be readily available.
- Context-Lacking: Raw weather data doesn't translate directly into actionable advice for specific activities.

Users need a system that not only fetches environmental data but intelligently interprets it, assesses risks, and provides personalized recommendations based on their planned activities and locations.

### Key Features

- Real-Time Weather Data: Fetches current conditions and forecasts from Open-Meteo API.
- Location Discovery: Finds optimal locations based on activity types.
- Risk Assessment: Analyzes environmental hazards.
- Reports: Generates recommendations.
- Quality Assurance: Built-in local evaluation tests.
- Monitoring: Built-in observability with metrics and traces.

## Use Cases

### Outdoor Recreation:
- Hiking and trekking.
- Cycling routes.
- Camping locations.

### Event Planning:
- Festivals.
- Concerts.
- Sport events.

### Professional Applications:
- Construction planning.
- Field activities.

### Travel Planning:
- Destination weather.
- Beach conditions.

## Architecture

Theophrastus employs a **multi-agent orchestration system** where agents and tools collaborate:

![Architecture](./TheophrastusArchitecture_0.png "Theophrastus_Architecture")

---

## Project Structure

```
Enviro_agent/
    - reports/
    - test/
        - test_agent.py                     #Test all agent functionalities in console

    - weather_advisor_agent/
        - config/
            -main_config.py                 # Agent configuration

        - data/

        - sub_agents/
            - zephyr_env_data_agent.py      # Weather data collection
            - atlas_env_location_agent.py   # Location discovery
            - aether_env_risk_agent.py      # Risk assessment
            - aurora_env_advice_writer.py   # Advice generation

        - tools/
            - web_access_tools.py           # API integrations
            - creation_tools.py             # File utilities
            - memory_tools.py               # Memory implementation tools

        - utils/
            - local_observability.py        # Logging & metrics
            - local_evaluator.py            # Verify agent functionality and validation
            - session_cache.py              # Mantain keys permanence
            - validation_checkers.py        # Quality validation

        - agent.py                          # Main orchestrator
    - .env                                  # env config
    - requirements.txt                      # Dependencies
    - README.md                             # This file
```

### The Sub-Agents

#### Zephyr (Data Agent)
- Fetches weather data from Open-Meteo API.
- Processes current conditions and forecasts.
- Validates data completeness.

_Named after Zephyros, Greek god of the west wind—the gentle spring breeze that brings favorable weather and seasonal change._

---

#### Atlas (Location Agent)  
- Discovers locations based on activity.
- Geocodes and validates coordinates.
- Enriches with geographic metadata.

_Named after the Titan Atlas, condemned to hold up the celestial spheres—now known as the bearer of maps and geographic knowledge._

---

#### Aether (Risk Agent)
- Assesses temperature extremes.
- Evaluates wind dangers.
- Analyzes precipitation risks.

_Named after Aether, primordial deity of the upper air—the pure, bright atmosphere the gods breathe, distinct from the mortal air below._

---

#### Aurora (Advice Writer)
- Synthesizes all gathered data.
- Generates professional markdown reports.
- Provides actionable recommendations.

_Named after Aurora (Eos in Greek), goddess of dawn—who brings light and clarity each morning, illuminating the path forward._

---

### The Tools

#### Web Access Tools
**Purpose:** Connect to external APIs for geocoding and weather data.

**API: Open-Meteo Weather** 
- Endpoint: `https://api.open-meteo.com/v1/forecast`.
- Authentication: No requierements (free tier).
- Data: Temperature, wind, humidity, precipitation.
- Coverage: Global.
- Resolution: Hourly forecasts.

---

**`geocode_place_name`**
- Converts location names to coordinates using Open-Meteo Geocoding API.
- Smart suffix removal (National Park, Mountain, Trail, etc.).
- Fuzzy matching with multiple candidate variations.
- Region-aware search with optional hints.

**`fetch_env_snapshot_from_open_meteo`**
- Retrieves comprehensive environmental data from Open-Meteo API.
- Fetches current temperature, humidity, wind speed, air quality.
- Validates coordinate bounds and handles timeouts gracefully.
- Returns structured snapshot with current and hourly data.

---

#### Memory Tools
**Purpose:** Enable cross-session learning and personalization.

**Preference Management:**
- `store_user_preference` - Remember user preferences (activity types, risk tolerance).
- `get_user_preferences` - Retrieve all stored preferences.

**Query History:**
- `add_to_query_history` - Track locations queried (keeps last 20).
- `get_query_history` - Retrieve recent query history.
- `search_query_history` - Search history by keyword.

**Favorite Locations:**
- `store_favorite_location` - Save favorite places with notes.
- `get_favorite_locations` - List all favorites.
- `remove_favorite_location` - Remove from favorites.

---

#### File Management Tools
**Purpose:** Persist reports and recommendations to disk.

**`save_env_report_to_file`**
- Saves generated markdown reports with timestamps.
- Automatic directory creation.
- UTF-8 encoding for international characters.
- Returns confirmation with full file path.

## Features in Detail

### 1. Multi-Location Analysis
Compare weather across multiple locations to find the best option:
```
User: "Compare hiking conditions in these three locations"
- Fetches data for all locations
- Assesses risks individually  
```

### 2. Risk-Based Recommendations
Recommendations based on risks:
- Heat Risk.
- Cold Risk.
- Wind Risk.
- Overall Risk.

### 3. Professional Reports
Structured markdown output with:
- Executive summary
- Current conditions
- Detailed recommendations
- Risk assessment

### 4. Quality Assurance

Local validation:
- Data completeness checks
- Coordinate validation
- Risk report structure
- Advice quality assessment

Local evaluation:
- Quality categories
- Automated scoring
- Performance monitoring
- JSON export for analysis

### 5. Observability

Full instrumentation with:
- Structured logging
- Performance metrics
- Operation tracing
- Error tracking
- JSON exports

## Quick Start

### Installation

```bash
# 1. Clone repository
git clone <repository-url>
cd weather_advisor_agent

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env and add your GOOGLE_API_KEY
# RECOMMENDATION: Disable VertexAI as GOOGLE_GENAI_USE_VERTEXAI=FALSE
```

### Running Theophrastus

- Option 1: ADK Web Interface (Recommended)
```cmd
adk web /agent/path
```
Then navigate to `http://localhost:8000` in your favorite web browser.

- Option 2: Python Script
```powershell
python -m test.test_agent
```

### Usage Example

```python
# Simple weather query
"How is the weather in Sacramento, California?"

# Location discovery
"Find good hiking spots near Mexico City"

# Full analysis
"What's the weather like for hiking in those locations?"

#Report generation
"Based on locations, generate a final recommendations report."
```

## Configuration

### .env Variables

```bash
# Required
GOOGLE_API_KEY=your_api_key_here

# Optional  
LOG_LEVEL=INFO
EVALUATION_ENABLED=true
```

### Model .config

Edit `config.py` to customize models based on your needs!
```python
root_model = "gemini-2.5-flash"
worker_model = "gemini-2.5-flash"
risk_model = "gemini-2.5-pro"
mapper_model = "gemini-2.0-flash-lite"
data_model = "gemini-2.0-flash-lite"
```

## Troubleshooting

### Common Issues

Issue: "No API key found"  
Solution: Ensure `GOOGLE_API_KEY` is set in `.env`.

Issue: "Response time too slow"  
Solution: Check network connectivity and API rate limits.

Issue: "Resource exhausted"  
Solution: Check API quota for RPM(Responses Per Minute) and TPM(Tokens Per Minute).

Issue: "No weather data"  
Solution: Problems within OpenMeteo API, not the agent functionality. Wait a few minutes.

## Future Ideas To Integrate!

### Version 3.0
- [ ] Improvements on local Evaluation, Observability and logging modules.
- [ ] Historical weather analysis.
- [ ] Database persitent memory.
- [ ] Extended forecasts.
- [ ] Aditional options for activity planning.
- [ ] Better reports.

### Version 4.0
- [ ] Multi-provider weather aggregation to avoid no weather data issues.
- [ ] Built-in machine learning models.
- [ ] Satellite imagery analisys.
- [ ] Agriculture and botanic options.

### Version 5.0
- [ ] Integration with hardware devices.

## License

Apache License - see [LICENSE](LICENSE) file for details.

## Contributions & Support!
If you want to contribute for the development, thank you so much!
Follow the next steps please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Ensure all tests pass
5. Submit a pull request

If you find Theophrastus useful, please star the repository!

 _Working with all kinds of engineering is fun!_