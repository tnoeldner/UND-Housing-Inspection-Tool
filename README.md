# 🏠 University Housing Inspection Tool

A comprehensive facilities inspection tool for higher education housing, featuring AI-powered APPA assessment and mobile-responsive design.

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://your-app-url-here.streamlit.app)

## ✨ Features

- 📱 **Mobile-Optimized**: Fully responsive design for phones and tablets
- 🤖 **AI Analysis**: Comprehensive APPA assessment using Google Gemini AI
- 🏠 **Multi-Type Inspections**: Custodial, Maintenance, and Grounds evaluations
- 📊 **SharePoint Integration**: Automatic data submission and email reporting
- 📋 **Standardized Checklists**: Based on APPA standards for higher education
- 💾 **Multiple Storage Options**: SharePoint, local files, and optional SQL database

## 🚀 Quick Start

### For Inspectors (Using the App)

1. **Open the app**: [Your Deployment URL]
2. **Select inspection type**: Custodial, Maintenance, or Grounds
3. **Fill in basic info**: Building, date, inspector name
4. **Complete checklist**: Rate items using APPA levels 1-5
5. **Generate AI report**: Click "Generate AI Report & APPA Score"
6. **Submit**: Click "Submit & Email Report"

### For Developers (Local Setup)

1. **Clone the repository**:
```bash
git clone [your-repo-url]
cd UND-Housing-Inspection-Tool
```

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Configure secrets** (create `.streamlit/secrets.toml`):
```toml
[api]
gemini_api_key = "your-gemini-api-key"
power_automate_url = "your-power-automate-webhook-url"
```

4. **Run the app**:
```bash
streamlit run app.py
```

## 🌐 Deployment

### Streamlit Community Cloud (Recommended)

1. **Push to GitHub**: Upload your code to a GitHub repository
2. **Go to [share.streamlit.io](https://share.streamlit.io)**
3. **Connect GitHub**: Authorize Streamlit to access your repo
4. **Deploy**: Select your repository and branch
5. **Add secrets**: In the Streamlit dashboard, add your API keys to secrets

### Deploy to Other Platforms

#### Heroku
```bash
# Add Procfile
echo "web: streamlit run app.py --server.port=$PORT --server.address=0.0.0.0" > Procfile

# Deploy
git add .
git commit -m "Streamlit app"
git push heroku main
```

#### Railway
1. Connect GitHub repository to Railway
2. Set build command: `pip install -r requirements.txt`
3. Set start command: `streamlit run app.py --server.port=$PORT --server.address=0.0.0.0`

## Configuration

### API Keys
Update these variables in `app.py`:

```python
GEMINI_API_KEY = "your-gemini-api-key"
POWER_AUTOMATE_URL = "your-power-automate-webhook-url"
```

### Building List
Modify the `BUILDINGS` list in `app.py` to match your facilities.

## Mobile Usage

- **Touch-Optimized**: All buttons and form elements are sized for mobile use
- **Responsive Layout**: Automatically adapts to screen size
- **Offline Capable**: Can be installed as a Progressive Web App

## Data Structure

The app submits this JSON structure to SharePoint:

```json
{
  "type": "custodial|maintenance|grounds",
  "building": "Building Name",
  "date": "2025-10-09",
  "inspector": "Inspector Name", 
  "aiReport": "Comprehensive AI analysis...",
  "details": [
    {
      "item": "Item Name",
      "rating": "Level 3",
      "notes": "Inspector notes"
    }
  ],
  "emailReportHTML": "Full HTML email content"
}
```

## SharePoint Setup

1. Create new columns in your SharePoint list:
   - `aiReport` (Multiple lines of text, Enhanced rich text)

2. Update your Power Automate flow to map:
   - `aiReport: triggerBody()['aiReport']`

3. Update email templates to use the new comprehensive report format

## Migration from HTML Version

The Streamlit version maintains the same data structure and API integration, so no backend changes are required beyond adding the new `aiReport` column.

## Support

For issues or questions about the inspection tool, please contact the facilities management team.