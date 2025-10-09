import streamlit as st
import requests
import json
from datetime import datetime
import pandas as pd

# Optional database import
try:
    from database import InspectionDatabase
    DATABASE_AVAILABLE = True
except ImportError as e:
    DATABASE_AVAILABLE = False
    InspectionDatabase = None

# File storage fallback
from file_storage import FileStorage

# Page configuration
st.set_page_config(
    page_title="University Housing Inspection Tool",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for UND branding and mobile optimization
st.markdown("""
<style>
    .main-header {
        text-align: center;
        color: #374151;
        margin-bottom: 2rem;
    }
    
    .inspection-card {
        background: white;
        padding: 1.5rem;
        border-radius: 0.5rem;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        margin-bottom: 1rem;
    }
    
    .appa-info {
        background: #e6f5ec;
        border-left: 4px solid #009A44;
        padding: 1rem;
        border-radius: 0.25rem;
        margin-bottom: 1rem;
    }
    
    .nav-tabs {
        display: flex;
        justify-content: center;
        margin-bottom: 2rem;
        gap: 0.5rem;
    }
    
    .stSelectbox > div > div {
        font-size: 16px;
    }
    
    .stTextInput > div > div > input {
        font-size: 16px;
    }
    
    .stTextArea > div > div > textarea {
        font-size: 16px;
    }
    
    .ai-report-area {
        background: #f8f9fa;
        padding: 1rem;
        border-left: 4px solid #009A44;
        border-radius: 0.25rem;
        white-space: pre-line;
        font-family: 'Arial', sans-serif;
    }
    
    /* Mobile optimizations */
    @media (max-width: 768px) {
        .main .block-container {
            padding: 1rem;
        }
        
        .stButton > button {
            width: 100%;
            min-height: 48px;
            font-size: 1rem;
        }
    }
</style>
""", unsafe_allow_html=True)

# Configuration - Use Streamlit secrets for deployment
try:
    GEMINI_API_KEY = st.secrets["api"]["gemini_api_key"]
    POWER_AUTOMATE_URL = st.secrets["api"]["power_automate_url"]
except:
    # Fallback for local development
    GEMINI_API_KEY = "AIzaSyCxo29Q6HRHRzxTuTU_IanG9yvJmctdzb0"
    POWER_AUTOMATE_URL = "https://defaultec37a091b9a647e598d0903d4a4192.03.environment.api.powerplatform.com:443/powerautomate/automations/direct/workflows/da9ca2f832b44a5fb19f50d0462068b3/triggers/manual/paths/invoke?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=-sb1eRCUppSwjFPD_zX02_25KpU78k4QIbZwjDffrQU"

# Building options
BUILDINGS = [
    "Noren Hall", "Selke Hall", "Brannon Hall", "McVey Hall", "West Hall",
    "Landing Zone", "Wilkerson Commons", "Swanson Hall", "Smith Hall", "Johnstone Hall",
    "University Place", "3600 Campus Rd", "3605 Manitoba", "110 State St", "Williamsburg",
    "Mt. Vernon", "Virginia Rose", "Townhouses", "72 Plex", "Berkely Drive",
    "540 CC", "550 CC", "580 CC", "560 CC", "570 CC"
]

# APPA Level definitions
APPA_LEVELS = {
    1: "Level 1: Orderly Spotlessness / Like-New Condition",
    2: "Level 2: Ordinary Tidiness / Good Condition", 
    3: "Level 3: Casual Inattention / Fair Condition",
    4: "Level 4: Moderate Dinginess / Poor Condition",
    5: "Level 5: Unkempt Neglect / Critical/Failed Condition"
}

# Inspection data
CUSTODIAL_DATA = {
    "Common Areas (Lobbies, Hallways, Lounges)": [
        "Flooring (Hard Surface)", "Flooring (Carpet/Rugs)", "Walls & Baseboards",
        "Entrances & Glass", "Furniture & Upholstery", "Lighting Fixtures",
        "Trash & Recycling Bins", "Drinking Fountains", "Odor Control"
    ],
    "Restrooms (Common/Public)": [
        "Floors & Drains", "Toilets & Urinals", "Sinks & Countertops",
        "Mirrors & Dispensers", "Stall Partitions", "Trash Receptacles", "Ventilation & Odor"
    ],
    "Ancillary Spaces (Kitchens, Laundry, Study Rooms)": [
        "Flooring", "Countertops & Sinks", "Appliances (Exterior)",
        "Laundry Machines (Exterior)", "Furniture (Tables/Chairs)", "Trash & Recycling Bins"
    ]
}

MAINTENANCE_DATA = {
    "Building Exterior & Envelope": [
        "Foundation & Walls", "Windows & Seals", "Doors & Hardware",
        "Roof & Gutters", "Walkways & Stairs", "Exterior Lighting"
    ],
    "Interior Common Areas (Lobbies, Hallways, Stairs)": [
        "Flooring Condition", "Wall & Ceiling Condition", "Paint Condition",
        "Doors & Hardware", "Handrails & Guardrails", "Lighting (Functionality)",
        "HVAC Vents & Grilles", "Fire & Life Safety"
    ],
    "Building Systems (General Observations)": [
        "HVAC Operation", "Plumbing (Public Areas)", "Electrical (Outlets/Switches)", "Elevator Operation"
    ],
    "Apartments/Dorms (Sample Inspection)": [
        "Door & Lockset", "Paint & Wall Condition", "Flooring Condition",
        "Windows & Blinds", "Plumbing Fixtures", "Appliances (If applicable)", "Lighting & Electrical"
    ]
}

GROUNDS_DATA = {
    "Landscaping (Seasonal)": [
        "Turf & Lawn Health", "Edging (Walks, Curbs)", "Plant Beds & Mulch",
        "Trees & Shrubs Pruning", "Weed Control", "Litter & Debris Removal"
    ],
    "Hardscapes & Site Amenities": [
        "Walkways & Patios Condition", "Benches & Site Furniture", "Trash & Ash Receptacles",
        "Bike Racks", "Signage"
    ],
    "Snow & Ice Removal (Seasonal)": [
        "Walkway & Sidewalk Clarity", "Entrances & ADA Ramps", "Stairs & Landings",
        "De-Icing Application", "Snow Pile Placement"
    ]
}

def initialize_session_state():
    """Initialize session state variables"""
    if 'inspection_type' not in st.session_state:
        st.session_state.inspection_type = 'Custodial'
    
    if 'ratings' not in st.session_state:
        st.session_state.ratings = {}
    
    if 'notes' not in st.session_state:
        st.session_state.notes = {}

def get_inspection_data(inspection_type):
    """Get inspection data based on type"""
    if inspection_type == 'Custodial':
        return CUSTODIAL_DATA
    elif inspection_type == 'Maintenance':
        return MAINTENANCE_DATA
    elif inspection_type == 'Grounds':
        return GROUNDS_DATA

def discover_gemini_models():
    """Discover available Gemini models"""
    try:
        response = requests.get(
            f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_API_KEY}"
        )
        if response.ok:
            models = response.json()
            gemini_models = [
                model for model in models.get('models', [])
                if 'gemini' in model['name'].lower() 
                and 'embedding' not in model['name'].lower()
                and 'generateContent' in model.get('supportedGenerationMethods', [])
            ]
            if gemini_models:
                # Sort by preference: newer models first
                gemini_models.sort(key=lambda x: x['name'], reverse=True)
                return gemini_models[0]['name']
    except Exception as e:
        st.error(f"Error discovering models: {e}")
    
    return "models/gemini-2.5-flash"  # Fallback

def call_gemini_api(prompt, model_name=None):
    """Call Gemini API for AI analysis"""
    if not model_name:
        model_name = discover_gemini_models()
    
    url = f"https://generativelanguage.googleapis.com/v1beta/{model_name}:generateContent?key={GEMINI_API_KEY}"
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 4000,
            "topP": 0.9
        }
    }
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        
        if response.ok:
            result = response.json()
            candidate = result.get('candidates', [{}])[0]
            
            if candidate.get('finishReason') == 'SAFETY':
                return "Response was blocked for safety reasons. Please try rephrasing your request."
            
            content = candidate.get('content', {}).get('parts', [{}])[0].get('text', '')
            
            if candidate.get('finishReason') == 'MAX_TOKENS' and content:
                content += "\n\n[Note: Response was truncated. Consider running analysis again.]"
            
            return content or "Could not generate response."
        else:
            return f"API Error: {response.status_code} - {response.text}"
            
    except requests.exceptions.Timeout:
        return "Request timed out. Please try again."
    except Exception as e:
        return f"Error calling AI service: {str(e)}"

def generate_comprehensive_report(inspection_type, building, findings):
    """Generate comprehensive APPA report"""
    if not findings:
        return "Please complete some checklist items before generating a report."
    
    # Organize findings by level
    level_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    all_findings_text = []
    
    for item, rating, notes in findings:
        if rating > 0:
            level_counts[rating] += 1
            finding_text = f"- {item}: Level {rating}"
            if notes.strip():
                finding_text += f" (Inspector Notes: {notes})"
            all_findings_text.append(finding_text)
    
    findings_text = "\n".join(all_findings_text)
    
    prompt = f"""You are a facilities management expert analyzing {inspection_type.lower()} inspection data for {building} using APPA standards.

**INSPECTION SUMMARY:**
• Level 1: {level_counts[1]} items
• Level 2: {level_counts[2]} items  
• Level 3: {level_counts[3]} items
• Level 4: {level_counts[4]} items
• Level 5: {level_counts[5]} items

**DETAILED FINDINGS:**
{findings_text}

**PROVIDE CONCISE ANALYSIS:**

**OVERALL APPA LEVEL:** [Assign 1-5 with 2-sentence justification]

**STRENGTHS:** [List 2-3 key Level 1-2 achievements]

**URGENT ISSUES:** [List Level 4-5 items requiring immediate action]

**ACTION PLAN:** [3-4 specific, prioritized recommendations]

**MANAGEMENT ASSESSMENT:** [Brief comment on facility management effectiveness]

Keep response under 400 words. Focus on actionable insights and APPA compliance."""
    
    return prompt

def convert_markdown_to_html(text):
    """Convert basic markdown formatting to HTML for emails"""
    if not text:
        return text
    
    import re
    
    # First, escape any existing HTML to prevent conflicts
    text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    
    # Convert **SECTION:** headers to styled headers
    text = re.sub(r'\*\*([A-Z\s]+:)\*\*', r'<h4 style="color: #009A44; margin: 15px 0 5px 0; font-size: 16px;">\1</h4>', text)
    
    # Convert **bold text** to <strong>
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    
    # Convert line breaks to HTML
    text = text.replace('\n', '<br>')
    
    # Handle bullet points (lines starting with • or *)
    text = re.sub(r'<br>[•*] (.*?)(?=<br>|$)', r'<br>• \1', text)
    
    # Handle numbered lists (lines starting with numbers)
    text = re.sub(r'<br>(\d+)\. (.*?)(?=<br>|$)', r'<br><strong>\1.</strong> \2', text)
    
    # Clean up multiple consecutive <br> tags
    text = re.sub(r'(<br>){3,}', '<br><br>', text)
    
    # Remove leading <br> if it exists
    text = text.lstrip('<br>')
    
    return text

def submit_to_sharepoint(data):
    """Submit data to SharePoint via Power Automate"""
    try:
        response = requests.post(POWER_AUTOMATE_URL, json=data, timeout=30)
        if response.ok:
            return True, "Successfully submitted to SharePoint and email sent!"
        else:
            return False, f"Submission failed: {response.status_code} - {response.text}"
    except Exception as e:
        return False, f"Error submitting data: {str(e)}"

def save_to_database(data, db):
    """Save inspection data to local database"""
    try:
        success, message = db.save_inspection(data)
        return success, message
    except Exception as e:
        return False, f"Database error: {str(e)}"

def main():
    initialize_session_state()
    
    # Sidebar for database configuration
    with st.sidebar:
        st.title("⚙️ Settings")
        
        # Database configuration
        st.subheader("Database Settings")
        
        if not DATABASE_AVAILABLE:
            st.warning("SQL Database not available. Using file-based storage instead.")
            st.info("File-based storage saves inspections as JSON files locally.")
            use_database = False
            use_file_storage = st.checkbox("Enable File Storage", value=True, help="Save inspections to local JSON files")
        else:
            use_database = st.checkbox("Enable SQL Database Storage", value=False, help="Save inspections to SQL Server database")
            use_file_storage = st.checkbox("Enable File Storage Backup", value=True, help="Also save to local JSON files")
        
        if use_database:
            st.info("Configure your database connection in Streamlit secrets or enter below:")
            
            # Database type selection
            db_type = st.selectbox("Database Type", [
                "SQL Server (Campus Network)",
                "Azure SQL Database", 
                "Custom Connection String"
            ])
            
            if db_type == "SQL Server (Campus Network)":
                server_name = st.text_input("Server Name", placeholder="your-sql-server")
                database_name = st.text_input("Database Name", value="Inspections")
                
                if server_name:
                    conn_string = f"Driver={{ODBC Driver 17 for SQL Server}};Server={server_name};Database={database_name};Trusted_Connection=yes;"
                    st.session_state.db_connection_string = conn_string
            
            elif db_type == "Azure SQL Database":
                server_name = st.text_input("Azure Server", placeholder="yourserver.database.windows.net")
                database_name = st.text_input("Database Name", value="Inspections")
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                
                if all([server_name, username, password]):
                    conn_string = f"Driver={{ODBC Driver 17 for SQL Server}};Server=tcp:{server_name},1433;Database={database_name};Uid={username};Pwd={password};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
                    st.session_state.db_connection_string = conn_string
            
            else:  # Custom
                conn_string = st.text_area("Connection String", placeholder="Enter your custom ODBC connection string")
                if conn_string:
                    st.session_state.db_connection_string = conn_string
            
            # Test connection button
            if st.button("Test Database Connection"):
                if hasattr(st.session_state, 'db_connection_string'):
                    db = InspectionDatabase(st.session_state.db_connection_string)
                    if db.connect():
                        st.success("✅ Database connection successful!")
                        db.disconnect()
                        
                        # Offer to create tables
                        if st.button("Create Database Tables"):
                            db.create_tables()
                    else:
                        st.error("❌ Database connection failed!")
                else:
                    st.warning("Please configure database connection first")
        
        # View stored data
        st.subheader("📊 View Data")
        if st.button("Show Recent Inspections"):
            st.session_state.show_data = True
        
        # File storage export
        if use_file_storage or (not DATABASE_AVAILABLE):
            if st.button("📁 Export to CSV"):
                file_storage = FileStorage()
                success, message = file_storage.export_to_csv()
                if success:
                    st.success(message)
                else:
                    st.error(message)
    
    # Header
    st.markdown('<div class="main-header">', unsafe_allow_html=True)
    st.title("🏠 University Housing Inspection Tool")
    st.markdown("Use the checklists below to evaluate building conditions based on APPA standards and best practices.")
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Navigation tabs
    st.markdown('<div class="nav-tabs">', unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🧹 Custodial", use_container_width=True):
            st.session_state.inspection_type = 'Custodial'
    
    with col2:
        if st.button("🔧 Maintenance", use_container_width=True):
            st.session_state.inspection_type = 'Maintenance'
    
    with col3:
        if st.button("🌿 Grounds", use_container_width=True):
            st.session_state.inspection_type = 'Grounds'
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Current inspection type indicator
    st.markdown(f"## {st.session_state.inspection_type} Building Evaluation")
    
    # APPA Info box
    st.markdown("""
    <div class="appa-info">
        <strong>APPA Service Levels</strong><br>
        Select a level for each item. The definition will appear below it.
    </div>
    """, unsafe_allow_html=True)
    
    # Basic information form
    st.markdown("### Basic Information")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        building = st.selectbox("Select Building", [""] + BUILDINGS)
    
    with col2:
        inspection_date = st.date_input("Inspection Date", datetime.now())
    
    with col3:
        inspector = st.text_input("Inspector Name")
    
    # Checklist
    st.markdown("### Inspection Checklist")
    
    inspection_data = get_inspection_data(st.session_state.inspection_type)
    findings = []
    
    for category, items in inspection_data.items():
        st.markdown(f"#### {category}")
        
        for item in items:
            with st.container():
                st.markdown(f"**{item}**")
                
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    # Make keys unique by including category to avoid duplicates
                    rating_key = f"{st.session_state.inspection_type}_{category}_{item}_rating"
                    rating = st.selectbox(
                        "Level",
                        options=[0, 1, 2, 3, 4, 5],
                        format_func=lambda x: "Select Level" if x == 0 else f"Level {x}",
                        key=rating_key
                    )
                    
                    if rating > 0:
                        st.info(APPA_LEVELS[rating])
                
                with col2:
                    notes_key = f"{st.session_state.inspection_type}_{category}_{item}_notes"
                    notes = st.text_area(
                        "Inspector Notes & Action Items",
                        key=notes_key,
                        height=80,
                        placeholder="Add any specific observations or action items..."
                    )
                
                if rating > 0 or notes.strip():
                    findings.append((item, rating, notes))
                
                st.divider()
    
    # AI Analysis Section
    st.markdown("### 🤖 AI Analysis & APPA Assessment")
    
    ai_report_placeholder = st.empty()
    
    if st.button("Generate AI Report & APPA Score", type="primary", use_container_width=True):
        if not findings:
            st.error("Please complete some checklist items before generating a report.")
        else:
            with st.spinner("Generating comprehensive APPA analysis..."):
                prompt = generate_comprehensive_report(st.session_state.inspection_type, building, findings)
                ai_report = call_gemini_api(prompt)
                st.session_state.ai_report = ai_report
    
    # Display AI report if available
    if hasattr(st.session_state, 'ai_report'):
        with ai_report_placeholder.container():
            st.markdown('<div class="ai-report-area">', unsafe_allow_html=True)
            st.markdown(st.session_state.ai_report)
            st.markdown('</div>', unsafe_allow_html=True)
    
    # Submit section
    st.markdown("---")
    
    if st.button("📤 Submit & Email Report", type="secondary", use_container_width=True):
        if not building or not inspector:
            st.error("Please fill in building and inspector information.")
        elif not findings:
            st.error("Please complete some checklist items.")
        else:
            # Prepare data for submission
            details = []
            for item, rating, notes in findings:
                if rating > 0 or notes.strip():
                    details.append({
                        "item": item,
                        "rating": f"Level {rating}" if rating > 0 else "Not Rated",
                        "notes": notes
                    })
            
            # Generate email HTML with ONLY inline styles - NO CSS classes
            email_html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; background-color: #ffffff; padding: 20px;">

<div style="background-color: #009A44; color: white; padding: 20px; text-align: center; margin-bottom: 20px; border-radius: 8px;">
<h1 style="margin: 0; font-size: 24px; font-weight: bold; color: white;">{st.session_state.inspection_type} Inspection Report</h1>
</div>

<div style="background-color: #f8f9fa; padding: 15px; border-radius: 6px; margin-bottom: 20px; border: 1px solid #e9ecef;">
<p style="margin: 5px 0; color: #333;"><strong>Building:</strong> {building}</p>
<p style="margin: 5px 0; color: #333;"><strong>Inspector:</strong> {inspector}</p>
<p style="margin: 5px 0; color: #333;"><strong>Date:</strong> {inspection_date}</p>
</div>

<h2 style="color: #009A44; border-bottom: 2px solid #009A44; padding-bottom: 8px; margin: 20px 0 15px 0;">Inspection Details</h2>
"""
            
            for detail in details:
                email_html += f"""
                <div style="padding: 10px; margin: 8px 0; background-color: #f9f9f9; border-left: 4px solid #009A44; border-radius: 4px;">
                    <strong style="color: #333;">{detail['item']}:</strong> <span style="color: #009A44; font-weight: bold;">{detail['rating']}</span>
                    {f'<div style="font-style: italic; color: #666; margin-left: 15px; margin-top: 5px;"><strong>Notes:</strong> {detail["notes"]}</div>' if detail['notes'] else ''}
                </div>
                """
            
            if hasattr(st.session_state, 'ai_report'):
                # Convert markdown formatting to HTML
                formatted_ai_report = convert_markdown_to_html(st.session_state.ai_report)
                
                email_html += f"""
<h3 style="color: #009A44; border-bottom: 2px solid #009A44; padding-bottom: 8px; margin-top: 30px;">AI Analysis & APPA Assessment</h3>
<div style="background-color: #f8f9fa; padding: 20px; border-left: 6px solid #009A44; line-height: 1.8; border-radius: 6px; margin: 15px 0; font-family: Arial, sans-serif; font-size: 14px; color: #333;">
{formatted_ai_report}
</div>
"""
            
            # Close the HTML properly
            email_html += """
<p style="margin-top: 30px; font-style: italic; color: #666; text-align: center; border-top: 1px solid #eee; padding-top: 20px;">
This report was automatically generated by the UND Housing Inspection Tool.
</p>

</body>
</html>"""
            
            submission_data = {
                "type": st.session_state.inspection_type.lower(),
                "building": building,
                "date": str(inspection_date),
                "inspector": inspector,
                "aiReport": getattr(st.session_state, 'ai_report', ''),
                "details": details,
                "emailReportHTML": email_html
            }
            
            # Submit to multiple destinations
            sharepoint_success = False
            db_success = False
            file_success = False
            
            # SharePoint submission
            with st.spinner("Submitting to SharePoint and sending email..."):
                sharepoint_success, sharepoint_message = submit_to_sharepoint(submission_data)
            
            # Database submission (if enabled and available)
            if DATABASE_AVAILABLE and hasattr(st.session_state, 'db_connection_string'):
                with st.spinner("Saving to SQL database..."):
                    db = InspectionDatabase(st.session_state.db_connection_string)
                    db_success, db_message = save_to_database(submission_data, db)
            
            # File storage (if enabled or as fallback)
            use_file_storage = st.session_state.get('use_file_storage', not DATABASE_AVAILABLE)
            if use_file_storage:
                with st.spinner("Saving to local files..."):
                    file_storage = FileStorage()
                    file_success, file_message = file_storage.save_inspection(submission_data)
            
            # Show results
            cols = st.columns(3)
            
            with cols[0]:
                st.subheader("📧 SharePoint & Email")
                if sharepoint_success:
                    st.success(sharepoint_message)
                else:
                    st.error(sharepoint_message)
            
            with cols[1]:
                st.subheader("💾 SQL Database")
                if DATABASE_AVAILABLE and hasattr(st.session_state, 'db_connection_string'):
                    if db_success:
                        st.success(db_message)
                    else:
                        st.error(db_message)
                else:
                    st.info("SQL database not configured")
            
            with cols[2]:
                st.subheader("📁 File Storage")
                if use_file_storage:
                    if file_success:
                        st.success(file_message)
                    else:
                        st.error(file_message)
                else:
                    st.info("File storage not enabled")
    
    # Show recent inspections if requested
    if hasattr(st.session_state, 'show_data') and st.session_state.show_data:
        st.markdown("---")
        st.subheader("📊 Recent Inspections")
        
        # Show data from available storage
        if DATABASE_AVAILABLE and hasattr(st.session_state, 'db_connection_string'):
            # Show SQL database data
            db = InspectionDatabase(st.session_state.db_connection_string)
            inspections = db.get_inspections(limit=10)
            
            if inspections:
                st.subheader("📊 SQL Database Records")
                df = pd.DataFrame(inspections)
                st.dataframe(df, use_container_width=True)
                
                # Dashboard data
                dashboard_data = db.get_dashboard_data()
                if dashboard_data:
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("Total Inspections", dashboard_data.get('total_inspections', 0))
                    
                    with col2:
                        st.metric("Last 30 Days", dashboard_data.get('recent_activity', 0))
                    
                    with col3:
                        custodial_count = dashboard_data.get('by_type', {}).get('custodial', 0)
                        st.metric("Custodial", custodial_count)
                    
                    with col4:
                        maintenance_count = dashboard_data.get('by_type', {}).get('maintenance', 0)
                        st.metric("Maintenance", maintenance_count)
        
        # Always show file storage data (fallback or backup)
        file_storage = FileStorage()
        file_inspections = file_storage.get_inspections(limit=10)
        
        if file_inspections:
            st.subheader("📁 File Storage Records")
            file_df = pd.DataFrame(file_inspections)
            st.dataframe(file_df, use_container_width=True)
            
            # File storage stats
            stats = file_storage.get_summary_stats()
            if stats:
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Total Files", stats.get('total_inspections', 0))
                
                with col2:
                    st.metric("Recent Files", stats.get('recent_activity', 0))
                
                with col3:
                    custodial_count = stats.get('by_type', {}).get('custodial', 0)
                    st.metric("Custodial", custodial_count)
                
                with col4:
                    maintenance_count = stats.get('by_type', {}).get('maintenance', 0)
                    st.metric("Maintenance", maintenance_count)
        
        if not file_inspections and (not DATABASE_AVAILABLE or not hasattr(st.session_state, 'db_connection_string')):
            st.info("No inspections found in any storage location")
        
        # Clear the show data flag
        if st.button("Hide Data"):
            st.session_state.show_data = False
            st.rerun()

if __name__ == "__main__":
    main()