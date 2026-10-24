"""
role_profiles.py
----------------
Stub role profiles for the 9 tech roles supported by WayPointAI.

These are stand-ins until Component 1 (data engineering) delivers real
profiles built from O*NET and Kaggle job postings.  Frequencies are
reasonable approximations based on common job posting patterns — replace
them wholesale once the real data arrives.

Usage
-----
    from role_profiles import ROLE_PROFILES

    profile = ROLE_PROFILES["Software Engineer"]
    # pass to gap_analyzer.analyze_gap(resume, profile)
"""

from __future__ import annotations

ROLE_PROFILES: dict[str, dict] = {
    "Software Engineer": {
        "role": "Software Engineer",
        "required_skills": [
            {"skill": "Python",                     "frequency": 0.85},
            {"skill": "Data Structures & Algorithms","frequency": 0.82},
            {"skill": "Git",                         "frequency": 0.80},
            {"skill": "SQL",                         "frequency": 0.72},
            {"skill": "System Design",               "frequency": 0.68},
            {"skill": "Java",                        "frequency": 0.60},
            {"skill": "REST APIs",                   "frequency": 0.65},
            {"skill": "Linux",                       "frequency": 0.55},
        ],
        "preferred_skills": [
            {"skill": "Docker",                      "frequency": 0.48},
            {"skill": "Kubernetes",                  "frequency": 0.38},
            {"skill": "AWS",                         "frequency": 0.45},
            {"skill": "TypeScript",                  "frequency": 0.40},
            {"skill": "React",                       "frequency": 0.38},
            {"skill": "CI/CD",                       "frequency": 0.42},
        ],
        "avg_years_experience": 2.0,
        "common_education": ["Computer Science", "Software Engineering", "Electrical Engineering"],
    },

    "AI/ML Engineer": {
        "role": "AI/ML Engineer",
        "required_skills": [
            {"skill": "Python",                      "frequency": 0.95},
            {"skill": "Machine Learning",            "frequency": 0.92},
            {"skill": "Deep Learning",               "frequency": 0.80},
            {"skill": "PyTorch",                     "frequency": 0.72},
            {"skill": "TensorFlow",                  "frequency": 0.68},
            {"skill": "SQL",                         "frequency": 0.65},
            {"skill": "Data Structures & Algorithms","frequency": 0.60},
            {"skill": "Git",                         "frequency": 0.75},
        ],
        "preferred_skills": [
            {"skill": "MLflow",                      "frequency": 0.42},
            {"skill": "Hugging Face Transformers",   "frequency": 0.45},
            {"skill": "AWS",                         "frequency": 0.40},
            {"skill": "Docker",                      "frequency": 0.38},
            {"skill": "Scikit-learn",                "frequency": 0.55},
            {"skill": "Natural Language Processing", "frequency": 0.48},
            {"skill": "Computer Vision",             "frequency": 0.40},
        ],
        "avg_years_experience": 2.5,
        "common_education": ["Computer Science", "Mathematics", "Statistics", "Electrical Engineering"],
    },

    "Data Scientist": {
        "role": "Data Scientist",
        "required_skills": [
            {"skill": "Python",                      "frequency": 0.93},
            {"skill": "SQL",                         "frequency": 0.88},
            {"skill": "Machine Learning",            "frequency": 0.82},
            {"skill": "Statistics",                  "frequency": 0.80},
            {"skill": "Data Visualization",          "frequency": 0.72},
            {"skill": "Pandas",                      "frequency": 0.75},
            {"skill": "Scikit-learn",                "frequency": 0.68},
        ],
        "preferred_skills": [
            {"skill": "R",                           "frequency": 0.45},
            {"skill": "Tableau",                     "frequency": 0.42},
            {"skill": "Spark",                       "frequency": 0.38},
            {"skill": "TensorFlow",                  "frequency": 0.35},
            {"skill": "AWS",                         "frequency": 0.38},
            {"skill": "A/B Testing",                 "frequency": 0.40},
            {"skill": "Deep Learning",               "frequency": 0.35},
        ],
        "avg_years_experience": 3.0,
        "common_education": ["Computer Science", "Statistics", "Mathematics", "Economics"],
    },

    "Security Engineer": {
        "role": "Security Engineer",
        "required_skills": [
            {"skill": "Network Security",            "frequency": 0.85},
            {"skill": "Linux",                       "frequency": 0.82},
            {"skill": "Python",                      "frequency": 0.72},
            {"skill": "Penetration Testing",         "frequency": 0.68},
            {"skill": "SIEM",                        "frequency": 0.65},
            {"skill": "Incident Response",           "frequency": 0.70},
            {"skill": "Firewalls",                   "frequency": 0.75},
        ],
        "preferred_skills": [
            {"skill": "Security+",                   "frequency": 0.55},
            {"skill": "CEH",                         "frequency": 0.38},
            {"skill": "CISSP",                       "frequency": 0.32},
            {"skill": "AWS",                         "frequency": 0.40},
            {"skill": "Scripting",                   "frequency": 0.48},
            {"skill": "Wireshark",                   "frequency": 0.45},
            {"skill": "Vulnerability Assessment",    "frequency": 0.52},
        ],
        "avg_years_experience": 3.0,
        "common_education": ["Computer Science", "Cybersecurity", "Information Technology"],
    },

    "Computer Engineer": {
        "role": "Computer Engineer",
        "required_skills": [
            {"skill": "C",                           "frequency": 0.82},
            {"skill": "C++",                         "frequency": 0.80},
            {"skill": "Embedded Systems",            "frequency": 0.78},
            {"skill": "Digital Logic Design",        "frequency": 0.72},
            {"skill": "Microcontrollers",            "frequency": 0.68},
            {"skill": "Python",                      "frequency": 0.60},
            {"skill": "VHDL/Verilog",               "frequency": 0.55},
        ],
        "preferred_skills": [
            {"skill": "FPGA",                        "frequency": 0.42},
            {"skill": "RTOS",                        "frequency": 0.40},
            {"skill": "PCB Design",                  "frequency": 0.38},
            {"skill": "Assembly",                    "frequency": 0.35},
            {"skill": "Linux",                       "frequency": 0.45},
            {"skill": "Git",                         "frequency": 0.50},
        ],
        "avg_years_experience": 2.0,
        "common_education": ["Computer Engineering", "Electrical Engineering", "Computer Science"],
    },

    "IT Support Specialist": {
        "role": "IT Support Specialist",
        "required_skills": [
            {"skill": "Windows Administration",      "frequency": 0.88},
            {"skill": "Active Directory",            "frequency": 0.80},
            {"skill": "Networking",                  "frequency": 0.78},
            {"skill": "Troubleshooting",             "frequency": 0.90},
            {"skill": "Help Desk",                   "frequency": 0.82},
            {"skill": "Microsoft 365",               "frequency": 0.75},
        ],
        "preferred_skills": [
            {"skill": "CompTIA A+",                  "frequency": 0.58},
            {"skill": "Linux",                       "frequency": 0.42},
            {"skill": "Scripting",                   "frequency": 0.38},
            {"skill": "ITIL",                        "frequency": 0.35},
            {"skill": "Azure",                       "frequency": 0.40},
            {"skill": "VPN",                         "frequency": 0.45},
            {"skill": "Ticketing Systems",           "frequency": 0.55},
        ],
        "avg_years_experience": 1.0,
        "common_education": ["Information Technology", "Computer Science", "Computer Engineering"],
    },

    "Hardware Engineer": {
        "role": "Hardware Engineer",
        "required_skills": [
            {"skill": "PCB Design",                  "frequency": 0.85},
            {"skill": "Circuit Analysis",            "frequency": 0.82},
            {"skill": "Altium Designer",             "frequency": 0.72},
            {"skill": "Embedded Systems",            "frequency": 0.70},
            {"skill": "Signal Integrity",            "frequency": 0.65},
            {"skill": "C",                           "frequency": 0.60},
            {"skill": "Oscilloscope",                "frequency": 0.68},
        ],
        "preferred_skills": [
            {"skill": "FPGA",                        "frequency": 0.45},
            {"skill": "VHDL/Verilog",               "frequency": 0.42},
            {"skill": "Python",                      "frequency": 0.38},
            {"skill": "SPICE Simulation",            "frequency": 0.40},
            {"skill": "Thermal Analysis",            "frequency": 0.35},
            {"skill": "DFM",                         "frequency": 0.32},
        ],
        "avg_years_experience": 2.5,
        "common_education": ["Electrical Engineering", "Computer Engineering"],
    },

    "QA Engineer": {
        "role": "QA Engineer",
        "required_skills": [
            {"skill": "Manual Testing",              "frequency": 0.88},
            {"skill": "Test Case Design",            "frequency": 0.85},
            {"skill": "Bug Tracking",                "frequency": 0.82},
            {"skill": "Selenium",                    "frequency": 0.72},
            {"skill": "Python",                      "frequency": 0.65},
            {"skill": "SQL",                         "frequency": 0.62},
            {"skill": "API Testing",                 "frequency": 0.68},
        ],
        "preferred_skills": [
            {"skill": "Cypress",                     "frequency": 0.42},
            {"skill": "JIRA",                        "frequency": 0.55},
            {"skill": "CI/CD",                       "frequency": 0.40},
            {"skill": "Performance Testing",         "frequency": 0.38},
            {"skill": "Java",                        "frequency": 0.40},
            {"skill": "Agile",                       "frequency": 0.50},
        ],
        "avg_years_experience": 1.5,
        "common_education": ["Computer Science", "Software Engineering", "Information Technology"],
    },

    "Product Manager": {
        "role": "Product Manager",
        "required_skills": [
            {"skill": "Product Roadmapping",         "frequency": 0.88},
            {"skill": "User Research",               "frequency": 0.82},
            {"skill": "Agile",                       "frequency": 0.85},
            {"skill": "Stakeholder Management",      "frequency": 0.80},
            {"skill": "Data Analysis",               "frequency": 0.75},
            {"skill": "SQL",                         "frequency": 0.62},
            {"skill": "A/B Testing",                 "frequency": 0.60},
        ],
        "preferred_skills": [
            {"skill": "Figma",                       "frequency": 0.48},
            {"skill": "JIRA",                        "frequency": 0.52},
            {"skill": "Python",                      "frequency": 0.35},
            {"skill": "Google Analytics",            "frequency": 0.42},
            {"skill": "Tableau",                     "frequency": 0.38},
            {"skill": "OKRs",                        "frequency": 0.45},
        ],
        "avg_years_experience": 3.0,
        "common_education": ["Computer Science", "Business", "Engineering", "Economics"],
    },
}
