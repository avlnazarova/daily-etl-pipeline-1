# Daily ETL Pipeline

## 📖 Project Description

This Python project automates daily data processing and enrichment. It takes CSV files with lead data, enriches them with CRM information via API, detects the CMS used by lead websites, and produces a dashboard-ready CSV.

It is designed to be modular, easy to maintain, and suitable for automation workflows.

## 🗂 Project Structure

```
daily-etl-pipeline-1/
│
├── data/
│   ├── input/            # Daily CSV files
│   ├── output/           # Processed dashboard files
│
├── src/
│   ├── script.py         # Main processing script
│   └── detect_cms.py     # CMS detection functions
│
├── .gitignore
├── requirements.txt
├── README.md
├── config.example.env
```

## 🔧 Setup

### 1. Clone the repository

```
git clone https://github.com/yourusername/daily-etl-pipeline-1.git
cd daily-etl-pipeline-1
```

### 2. Create and activate a virtual environment

macOS / Linux

```
python3 -m venv .venv
source .venv/bin/activate
```

Windows

```
python -m venv .venv
.venv\Scripts\activate
```

Make sure you are using Python 3.9+:

```
python --version
```

### 3. Install dependencies

```
pip install -r requirements.txt
```

### 4. Configure environment variables

This project uses environment variables for sensitive configuration (CRM API credentials).

Copy the example config:

```
cp config.example.env .env
```


Edit .env with your credentials:

```
HSAutomationToken=your_hubspot_access_token
```


⚠️ Do not commit .env to version control.
It is included in .gitignore.

### 7. Running the script

Run the main script with a specified date:

```
python src/script.py --date 2025-09-02
```

