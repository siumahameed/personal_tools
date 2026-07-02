# ScholarAI Agent — Setup Guide

## Prerequisites
- Python 3.11+
- pip (Python package installer)
- A Google account (for Google Sheets)

## Step 1: Install Dependencies

```bash
cd scholarship-agent
pip install -r requirements.txt
```

## Step 2: Google Sheets API Setup (Optional but Recommended)

### If you WANT Google Sheets sync:
1. Go to https://console.cloud.google.com/
2. Create a New Project → name it "scholarai"
3. Enable **Google Sheets API** and **Google Drive API**
4. Go to **Credentials** → Create Credentials → **Service Account**
5. Name it "scholarai-agent" → click Create
6. Under "Grant this service account access to project":
   - Role: **Editor**
   - Click Continue → Done
7. In the Credentials list, click the service account email
8. Go to **Keys** → **Add Key** → **JSON**
9. A JSON file will download — this is your `credentials.json`
10. Place it in the `scholarship-agent/` folder

### If you DON'T want Google Sheets:
The system saves all data to local JSON files in `data/` folder automatically.
No setup needed.

## Step 3: Configure Your Profile

Edit `config.py` to personalize:
```python
PROFILE = {
    "name": "Sium Ahameed Bhuyan",
    "email": "your.email@example.com",     # Add your email
    "current_education": "BSc in Statistics, Dhaka College",
    "gpa": "3.20",
    ...
}
```

## Step 4: Run the System

### Option A: Web Dashboard (Recommended)
```bash
python main.py --web
```
Then open http://localhost:5000 in your browser.

### Option B: CLI Mode
```bash
python main.py
```
Follow the interactive menu.

### Option C: Full Scan
```bash
python main.py --scan
```
Runs all agents automatically and saves all results.

## How It Works

### Agents
| Agent | What it does |
|-------|-------------|
| **Scholarship Agent** | Finds scholarships (DAAD, Erasmus Mundus, etc.), their requirements, deadlines, and match scores |
| **University Agent** | Lists German universities with English MSc programs in ML/AI/Data Science/Statistics |
| **Professor Agent** | Finds professors at target universities, their emails, research interests, and recent papers |

### Features
| Feature | What it does |
|---------|-------------|
| **Timeline** | Personalized application roadmap with deadlines |
| **Tracker** | Track your application status (Not Started → Applied → Accepted/Rejected) |
| **Checklist** | Document checklist with progress tracking |
| **Match Scores** | Auto-calculates scholarship fit based on your profile |
| **Cost Comparison** | Compare living costs across German cities |

### Google Sheets Integration
If connected, all data auto-syncs to Google Sheets:
- `ScholarAI_Scholarships`
- `ScholarAI_Universities`
- `ScholarAI_Professors`
- `ScholarAI_Tracker`
- `ScholarAI_Checklist`

### Interactive Agents
Every agent asks for confirmation before running:
- "Start scholarship research?"
- "Save results to storage?"
This ensures you control what data is collected and stored.

## Troubleshooting

**"Module not found"**: Run `pip install -r requirements.txt`

**Google Sheets errors**: The system runs without Google Sheets. Data saves locally.

**Web dashboard not loading**: Ensure FastAPI and Uvicorn are installed:
```bash
pip install fastapi uvicorn
```

Good luck with your applications! 🇩🇪
