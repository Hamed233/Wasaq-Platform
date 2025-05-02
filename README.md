# Wasaq Platform

## GIS-based Endowment Management System

A comprehensive web platform to manage and visualize endowment lands with AI-powered recommendations, analytics, and investor support.

## Features

- Interactive GIS map displaying all endowment properties
- Land status reports and project updates
- Advanced statistics and analytics
- AI-powered recommendations for land development
- Investor support chatbot
- Filtering and search capabilities
- Blockchain integration for data security
- Big data analytics for economic insights

## Technology Stack

- **Backend**: Python, Flask
- **Database**: PostgreSQL with PostGIS extension
- **Frontend**: HTML5, CSS3, JavaScript, Bootstrap
- **GIS**: GeoPandas, Folium
- **AI/ML**: TensorFlow, scikit-learn, Transformers
- **Chatbot**: ChatterBot, NLTK, spaCy
- **Data Visualization**: Plotly, Matplotlib

## Installation

1. Clone the repository
2. Create a virtual environment: `python -m venv venv`
3. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - macOS/Linux: `source venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Set up environment variables in `.env` file
6. Initialize the database: `flask db init`
7. Run migrations: `flask db migrate` and `flask db upgrade`
8. Start the development server: `flask run`

## Project Structure

```
waqaf-platform/
├── app/                    # Application package
│   ├── api/                # API endpoints
│   ├── models/             # Database models
│   ├── static/             # Static files (CSS, JS, images)
│   ├── templates/          # HTML templates
│   └── utils/              # Utility functions
├── instance/               # Instance-specific configuration
├── migrations/             # Database migrations
├── .env                    # Environment variables
├── config.py               # Configuration settings
├── requirements.txt        # Project dependencies
└── run.py                  # Application entry point
```

