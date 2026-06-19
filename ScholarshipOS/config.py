import os

# Load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)
except ImportError:
    pass

PROFILE = {
    "name": "Sium Ahameed Bhuyan",
    "email": "",
    "phone": "",
    "current_education": "BSc in Statistics (Graduated), Dhaka College",
    "university": "Dhaka College",
    "department": "Statistics",
    "gpa": "3.20",
    "cgpa_scale": "4.00",
    "current_year": 0,
    "graduated": True,
    "country": "Bangladesh",
    "target_countries": ["Germany", "USA", "UK", "Canada", "Switzerland", "Singapore", "Australia"],
    "target_degrees": ["MSc", "Masters"],
    "target_fields": [
        "Machine Learning",
        "Data Science",
        "Artificial Intelligence",
        "Deep Learning",
        "Statistics",
        "Data Analytics"
    ],
    "top_scholarships": ["DAAD", "Erasmus Mundus", "Fulbright", "Knight-Hennessy"],
    "target_universities": [
        "Carnegie Mellon University",
        "ETH Zurich",
        "National University of Singapore",
        "EPFL",
        "Technical University of Munich",
        "University of Montreal",
        "RWTH Aachen University",
        "University of Melbourne",
        "University of Waterloo"
    ],
    "preferred_language": "English",
    "scholarship_type_preference": "full_ride",
    "fallback_type": "full_tuition_waiver",
    "graduation_year": 2025,
    "available_test_scores": {
        "ielts": None,
        "toefl": None,
        "gre": None
    }
}

SHEETS_CONFIG = {
    "spreadsheet_id": os.environ.get("GOOGLE_SPREADSHEET_ID", "1gZXzyaEWC015x7BN-Ja9rWCY81BN-5g0-2n2a41K_qk"),
    "credentials_path": os.environ.get("GOOGLE_CREDENTIALS_PATH", "credentials.json"),
}

APP_CONFIG = {
    "app_name": "ScholarAI Agent",
    "version": "1.2.0",
    "data_dir": "data",
    "log_level": os.environ.get("LOG_LEVEL", "INFO"),
}
