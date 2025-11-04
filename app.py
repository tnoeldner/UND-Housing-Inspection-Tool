# --- UND Housing Facilities Inspection App ---
# Renamed from inspection_app_template.py

# Debug: print checklist_prefill and form field values before rendering form
import streamlit as st
import pandas as pd
import psycopg2
from datetime import datetime
import os

# Neon DB connection
def get_neon_connection():
    db = st.secrets["database"]
    conn_str = (
        f"host={db['NEON_DB_HOST']} "
        f"port={db['NEON_DB_PORT']} "
        f"dbname={db['NEON_DB_NAME']} "
        f"user={db['NEON_DB_USER']} "
        f"password={db['NEON_DB_PASSWORD']} "
        f"sslmode=require"
    )
    return psycopg2.connect(conn_str)

def fetch_inspections(building=None, report_type=None, inspector=None, date=None, limit=10):
    conn = get_neon_connection()
    cur = conn.cursor()
    query = "SELECT * FROM inspections WHERE TRUE"
    params = []
    if building:
        query += " AND building = %s"
        params.append(building)
    if report_type:
        query += " AND inspection_type = %s"
        params.append(report_type)
    if inspector:
        query += " AND inspector = %s"
        params.append(inspector)
    if date:
        query += " AND inspection_date = %s"
        params.append(date)
    query += " ORDER BY inspection_date DESC LIMIT %s"
    params.append(limit)
    cur.execute(query, tuple(params))
    rows = cur.fetchall()
    columns = [desc[0] for desc in cur.description]
    cur.close()
    conn.close()
    return pd.DataFrame(rows, columns=columns)

def fetch_inspection_items(inspection_id):
    conn = get_neon_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM inspection_items WHERE inspection_id = %s", (inspection_id,))
    items_rows = cur.fetchall()
    items_columns = [desc[0] for desc in cur.description]
    # Fetch photos for these items
    cur.execute("SELECT * FROM inspection_item_photos WHERE inspection_item_id = ANY (%s)", ([row[0] for row in items_rows],))
    photos_rows = cur.fetchall()
    photos_columns = [desc[0] for desc in cur.description]
    cur.close()
    conn.close()
    items_df = pd.DataFrame(items_rows, columns=items_columns)
    photos_df = pd.DataFrame(photos_rows, columns=photos_columns)
    return items_df, photos_df

# ...existing code for Streamlit UI, Gemini API, and inspection lookup...
import streamlit as st
import requests
import json
from datetime import datetime
import pandas as pd

DATABASE_AVAILABLE = False
try:
    db_secrets = st.secrets.get("database", {})
    required_keys = [
        "NEON_DB_HOST", "NEON_DB_PORT", "NEON_DB_NAME", "NEON_DB_USER", "NEON_DB_PASSWORD"
    ]
    if all(k in db_secrets and db_secrets[k] for k in required_keys):
        DATABASE_AVAILABLE = True
    else:
        DATABASE_AVAILABLE = False
except Exception:
    DATABASE_AVAILABLE = False

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
if "api" in st.secrets and "gemini_api_key" in st.secrets["api"]:
    GEMINI_API_KEY = st.secrets["api"]["gemini_api_key"]
    POWER_AUTOMATE_URL = st.secrets["api"].get("power_automate_url", "")
else:
    raise RuntimeError("Gemini API key not found in Streamlit secrets. Please add it to .streamlit/secrets.toml.")

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
    """Save inspection data to Neon database"""
    try:
        conn = get_neon_connection()
        cur = conn.cursor()
        # Insert into inspections table
        cur.execute(
            """
            INSERT INTO inspections (inspection_type, building, inspection_date, inspector, ai_report, email_report_html)
            VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
            """,
            (
                data['type'],
                data['building'],
                data['date'],
                data['inspector'],
                data.get('aiReport', ''),
                data.get('emailReportHTML', '')
            )
        )
        inspection_id = cur.fetchone()[0]
        # Insert details with granular error reporting
        for detail in data.get('details', []):
            sql = """
                INSERT INTO inspection_items (inspection_id, category, item, rating, notes)
                VALUES (%s, %s, %s, %s, %s)
            """
            params = (
                inspection_id,
                detail.get('category', ''),
                detail['item'],
                detail['rating'],
                detail.get('notes', '')
            )
            try:
                cur.execute(sql, params)
            except Exception as item_error:
                st.error(f"Error inserting item: {detail} -> {item_error}")
        conn.commit()
        cur.close()
        conn.close()
        return True, f"Inspection saved with ID: {inspection_id}"
    except Exception as e:
        return False, f"Database error: {str(e)}"

def main():
    # Prefill form if editing a report
    edit_report_id = st.session_state.get('edit_report_id')
    loaded_report = None
    loaded_items = None
    if edit_report_id and st.session_state.get('force_prefill', True):
        # Fetch only the selected inspection by its ID
        loaded_df = fetch_inspections(limit=50)  # Get enough records to find the ID
        st.write(f"DEBUG: edit_report_id={edit_report_id}, loaded_df ids={loaded_df['id'].tolist() if not loaded_df.empty else 'EMPTY'}")
        loaded_report = loaded_df[loaded_df['id'] == edit_report_id].iloc[0] if not loaded_df.empty and edit_report_id in loaded_df['id'].values else None
    loaded_items_df, loaded_photos_df = fetch_inspection_items(edit_report_id)
    loaded_items = loaded_items_df.to_dict('records') if not loaded_items_df.empty else []
    loaded_photos = loaded_photos_df.to_dict('records') if not loaded_photos_df.empty else []
    st.write(f"DEBUG: loaded_report={loaded_report}")
    st.write(f"DEBUG: loaded_items count={len(loaded_items)} contents={loaded_items}")
    st.write(f"DEBUG: loaded_photos count={len(loaded_photos)} contents={loaded_photos}")
    # Prefill basic info using correct DataFrame column names
    if loaded_report is not None:
        st.write(f"DEBUG: loaded_report columns={loaded_report.index.tolist()}")
        st.session_state.inspection_type = str(loaded_report.get('inspection_type', 'Custodial')).capitalize()
        st.session_state.building = loaded_report.get('building', BUILDINGS[0])
        # Convert date string to datetime.date if needed
        date_val = loaded_report.get('inspection_date', None)
        if isinstance(date_val, str) and date_val not in [None, 'None', '']:
            try:
                st.session_state.inspection_date = datetime.strptime(date_val, "%Y-%m-%d").date()
            except Exception:
                st.session_state.inspection_date = date_val
        elif date_val:
            st.session_state.inspection_date = date_val
        else:
            st.session_state.inspection_date = datetime.today().date()
        st.session_state.inspector = loaded_report.get('inspector', '')
        # Prefill checklist ratings and notes
        if loaded_items:
            checklist_prefill = {}
            inspection_data = get_inspection_data(st.session_state.inspection_type)
            for item in loaded_items:
                # If category is empty, infer it by matching item name
                category_val = item.get('category', '')
                if not category_val:
                    for cat, items in inspection_data.items():
                        if item['item'] in items:
                            category_val = cat
                            break
                    if not category_val:
                        category_val = 'General'
                rating_key = f"{st.session_state.inspection_type}_{category_val}_{item['item']}_rating"
                notes_key = f"{st.session_state.inspection_type}_{category_val}_{item['item']}_notes"
                # Extract numeric rating from 'Level X'
                try:
                    rating_val = int(str(item['rating']).replace('Level ','')) 
                except:
                    rating_val = 0
                # Only set in checklist_prefill, not session_state
                checklist_prefill[rating_key] = rating_val
                checklist_prefill[notes_key] = item.get('notes','')
        # Also update checklist_prefill for form rendering
        checklist_prefill = {}
        inspection_data = get_inspection_data(st.session_state.inspection_type)
        for category, items in inspection_data.items():
            for item in items:
                rating_key = f"{st.session_state.inspection_type}_{category}_{item}_rating"
                notes_key = f"{st.session_state.inspection_type}_{category}_{item}_notes"
                checklist_prefill[rating_key] = st.session_state.get(rating_key, 0)
                checklist_prefill[notes_key] = st.session_state.get(notes_key, "")
        st.session_state.force_prefill = False
    initialize_session_state()

    # Sidebar for workflow selection and database configuration
    with st.sidebar:
        st.title("Inspection Workflow")
        if st.button("New Inspection"):
            st.session_state._new_form_triggered = True
        if st.button("Edit Previous Inspection"):
            st.session_state._edit_form_triggered = True
        st.markdown("---")
        st.title("⚙️ Settings")
        st.subheader("Database Settings")
        if not DATABASE_AVAILABLE:
            st.error("Neon database features are disabled. Please check your secrets configuration.")
            use_database = False
        else:
            use_database = True
        st.markdown("---")
        st.header("Lookup Past Reports")
    # Handle workflow selection only when triggered
    if st.session_state.get('_new_form_triggered', False):
        # Clear session state for new inspection
        st.session_state.edit_report_id = None
        st.session_state.force_prefill = False
        st.session_state.inspection_type = ""
        st.session_state.building = ""
        st.session_state.inspection_date = None
        st.session_state.inspector = ""
        # Clear all rating and notes keys
        for checklist in [CUSTODIAL_DATA, MAINTENANCE_DATA, GROUNDS_DATA]:
            for category, items in checklist.items():
                for item in items:
                    rating_key = f"{st.session_state.inspection_type}_{category}_{item}_rating"
                    notes_key = f"{st.session_state.inspection_type}_{category}_{item}_notes"
                    st.session_state[rating_key] = 0
                    st.session_state[notes_key] = ""
        st.session_state._new_form_triggered = False
        st.rerun()
    if st.session_state.get('_edit_form_triggered', False):
        # Show report lookup UI (existing logic)
        st.session_state.show_data = True
        st.session_state._edit_form_triggered = False
        st.rerun()
    # ...existing code for report lookup UI...
    
    # Main Inspection Form
    # Prefill variables from loaded report/items if available
    inspection_types = ["Custodial", "Maintenance", "Grounds"]
    prefill_type = st.session_state.get("inspection_type")
    prefill_building = st.session_state.get("building")
    prefill_date = st.session_state.get("inspection_date")
    prefill_inspector = st.session_state.get("inspector")
    # Prefill checklist ratings/notes
    checklist_prefill = {}
    inspection_data = get_inspection_data(prefill_type)
    loaded_keys = set()
    if 'loaded_items' in locals() and loaded_items:
        for item in loaded_items:
            category_val = item.get('category', '')
            if not category_val:
                for cat, items_list in inspection_data.items():
                    if item['item'] in items_list:
                        category_val = cat
                        break
            if not category_val:
                category_val = 'General'
            rating_key = f"{prefill_type}_{category_val}_{item['item']}_rating"
            notes_key = f"{prefill_type}_{category_val}_{item['item']}_notes"
            try:
                rating_val = int(str(item['rating']).replace('Level ',''))
            except:
                rating_val = 0
            checklist_prefill[rating_key] = rating_val
            checklist_prefill[notes_key] = item.get('notes','')
            loaded_keys.add(rating_key)
            loaded_keys.add(notes_key)
    # For any items not in loaded_items, use session state defaults
    for category, items in inspection_data.items():
        for item in items:
            rating_key = f"{prefill_type}_{category}_{item}_rating"
            notes_key = f"{prefill_type}_{category}_{item}_notes"
            if rating_key not in checklist_prefill:
                checklist_prefill[rating_key] = st.session_state.get(rating_key, 0)
            if notes_key not in checklist_prefill:
                checklist_prefill[notes_key] = st.session_state.get(notes_key, "")

    # Debug output before form rendering
    st.write(f"DEBUG: checklist_prefill={checklist_prefill}")
    st.write(f"DEBUG: prefill_type={prefill_type} prefill_building={prefill_building} prefill_date={prefill_date} prefill_inspector={prefill_inspector}")

    with st.form("inspection_form"):
        st.markdown('<div class="nav-tabs">', unsafe_allow_html=True)
        col1, col2, col3, col4 = st.columns(4)

        # Always render form, use blank/defaults if None
        with col1:
            inspection_type = st.selectbox(
                "Inspection Type",
                inspection_types,
                index=inspection_types.index(prefill_type) if prefill_type in inspection_types else 0,
                key="inspection_type_select",
            )
        with col2:
            building = st.selectbox(
                "Building",
                BUILDINGS,
                index=BUILDINGS.index(prefill_building) if prefill_building in BUILDINGS else 0,
                key="building_select",
            )
        with col3:
            inspection_date = st.date_input(
                "Inspection Date",
                value=prefill_date if prefill_date else datetime.today().date(),
                key="inspection_date_select",
            )
        with col4:
            inspector = st.text_input(
                "Inspector Name",
                value=prefill_inspector if prefill_inspector else "",
                key="inspector_name_input",
            )

        # Checklist
        st.markdown("### Inspection Checklist")
        inspection_data = get_inspection_data(inspection_type)
        findings = []
        for category, items in inspection_data.items():
            st.markdown(f"#### {category}")
            for item in items:
                with st.container():
                    st.markdown(f"**{item}**")
                    # Debug: show item dict and ID
                    st.caption(f"Item dict: {item if isinstance(item, dict) else {'item': item}}")
                    item_id = item.get('id') if isinstance(item, dict) else None
                    st.caption(f"Item ID: {item_id}")
                    # Debug: show all loaded photo records
                    if loaded_photos:
                        st.caption(f"Loaded photos: {[{'id': p.get('id'), 'item_id': p.get('item_id'), 'size': len(p.get('photo_data', b'')) if p.get('photo_data') else 0} for p in loaded_photos]}")
                    col1, col2 = st.columns([1, 2])
                    rating_key = f"{inspection_type}_{category}_{item}_rating"
                    notes_key = f"{inspection_type}_{category}_{item}_notes"
                    with col1:
                        rating_val = checklist_prefill.get(rating_key, 0)
                        options = [0, 1, 2, 3, 4, 5]
                        try:
                            rating_index = options.index(rating_val)
                        except ValueError:
                            rating_index = 0
                        rating = st.selectbox(
                            "Level",
                            options=options,
                            format_func=lambda x: "Select Level" if x == 0 else f"Level {x}",
                            key=rating_key,
                            index=rating_index
                        )
                        if rating > 0:
                            st.info(APPA_LEVELS[rating])
                    with col2:
                        notes = st.text_area(
                            "Inspector Notes & Action Items",
                            value=checklist_prefill.get(notes_key, ""),
                            key=notes_key,
                            height=80,
                            placeholder="Add any specific observations or action items..."
                        )
                    # Display photos for this item if any (match by item name and inspection_id)
                    if edit_report_id and loaded_photos:
                        import io
                        item_photos = [p for p in loaded_photos if str(p.get('item', '')) == str(item) and int(p.get('inspection_id', 0)) == int(edit_report_id)]
                        # Enhanced debug output
                        st.caption(f"[DEBUG] Loaded photo records: {[{'id': p.get('id'), 'item': p.get('item'), 'inspection_id': p.get('inspection_id'), 'size': len(p.get('photo_data', b'')) if p.get('photo_data') else 0} for p in loaded_photos]}")
                        st.caption(f"[DEBUG] Trying to match photos for item='{item}' and inspection_id={edit_report_id}")
                        st.caption(f"[DEBUG] Matching photos found: {[{'id': p.get('id'), 'item': p.get('item'), 'inspection_id': p.get('inspection_id'), 'size': len(p.get('photo_data', b'')) if p.get('photo_data') else 0} for p in item_photos]}")
                        if item_photos:
                            st.markdown("**Photos for this item:**")
                            for photo in item_photos:
                                img_bytes = photo['photo_data']
                                if isinstance(img_bytes, memoryview):
                                    img_bytes = img_bytes.tobytes()
                                img_file = io.BytesIO(img_bytes)
                                st.image(img_file, caption=f"Photo for {item}", use_column_width=True)
                        else:
                            st.caption(f"[DEBUG] No photos found for item='{item}' and inspection_id={edit_report_id}")
                    if rating > 0 or notes.strip():
                        findings.append((item, rating, notes))
                    st.divider()

        submitted = st.form_submit_button("Save Inspection Report")
        if submitted:
            # Update session state with form values
            st.session_state.inspection_type = inspection_type
            st.session_state.building = building
            st.session_state.inspection_date = inspection_date
            st.session_state.inspector = inspector
            # Save checklist ratings and notes
            for category, items in inspection_data.items():
                for item in items:
                    rating_key = f"{inspection_type}_{category}_{item}_rating"
                    notes_key = f"{inspection_type}_{category}_{item}_notes"
                    st.session_state[rating_key] = st.session_state.get(rating_key, 0)
                    st.session_state[notes_key] = st.session_state.get(notes_key, "")
            st.success("Inspection report saved. You can now submit to Neon or generate an AI report.")
        # Prepare details for database submission (all items)
        details = []
        for category, item, rating, notes in findings:
            details.append({
                "category": category,
                "item": item,
                "rating": f"Level {rating}" if rating > 0 else "Not Rated",
                "notes": notes
            })
        # ...existing code for database submission...
    
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
    
    if st.button("📤 Submit & View Report", type="secondary", use_container_width=True):
        if not building or not inspector:
            st.error("Please fill in building and inspector information.")
        elif not findings:
            st.error("Please complete some checklist items.")
        else:
            # Prepare data for submission
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
                # Generate HTML report for viewing
                report_html = f'<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>'
                report_html += f'<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; background-color: #ffffff; padding: 20px;">'
                report_html += f'<div style="background-color: #009A44; color: white; padding: 20px; text-align: center; margin-bottom: 20px; border-radius: 8px;">'
                report_html += f'<h1 style="margin: 0; font-size: 24px; font-weight: bold; color: white;">{st.session_state.inspection_type} Inspection Report</h1>'
                report_html += f'</div>'
                report_html += f'<div style="background-color: #f8f9fa; padding: 15px; border-radius: 6px; margin-bottom: 20px; border: 1px solid #e9ecef;">'
                report_html += f'<p style="margin: 5px 0; color: #333;"><strong>Building:</strong> {building}</p>'
                report_html += f'<p style="margin: 5px 0; color: #333;"><strong>Inspector:</strong> {inspector}</p>'
                report_html += f'<p style="margin: 5px 0; color: #333;"><strong>Date:</strong> {inspection_date}</p>'
                report_html += f'</div>'
                report_html += f'<h2 style="color: #009A44; border-bottom: 2px solid #009A44; padding-bottom: 8px; margin: 20px 0 15px 0;">Inspection Details</h2>'
                for detail in details:
                    report_html += f'<div style="padding: 10px; margin: 8px 0; background-color: #f9f9f9; border-left: 4px solid #009A44; border-radius: 4px;">'
                    report_html += f'<strong style="color: #333;">{detail["item"]}:</strong> <span style="color: #009A44; font-weight: bold;">{detail["rating"]}</span>'
                    if detail['notes']:
                        report_html += f'<div style="font-style: italic; color: #666; margin-left: 15px; margin-top: 5px;"><strong>Notes:</strong> {detail["notes"]}</div>'
                    report_html += f'</div>'
                if hasattr(st.session_state, 'ai_report'):
                    # Convert markdown formatting to HTML
                    formatted_ai_report = convert_markdown_to_html(st.session_state.ai_report)
                    report_html += f'<h3 style="color: #009A44; border-bottom: 2px solid #009A44; padding-bottom: 8px; margin-top: 30px;">AI Analysis & APPA Assessment</h3>'
                    report_html += f'<div style="background-color: #f8f9fa; padding: 20px; border-left: 6px solid #009A44; line-height: 1.8; border-radius: 6px; margin: 15px 0; font-family: Arial, sans-serif; font-size: 14px; color: #333;">'
                    report_html += formatted_ai_report
                    report_html += f'</div>'
                # Close the HTML properly
                report_html += f'<p style="margin-top: 30px; font-style: italic; color: #666; text-align: center; border-top: 1px solid #eee; padding-top: 20px;">'
                report_html += f'This report was automatically generated by the UND Housing Inspection Tool.'
                report_html += f'</p></body></html>'
                # Show report preview to verify formatting
                st.subheader("\U0001F4DD Report Preview")
                st.components.v1.html(report_html, height=400, scrolling=True)
                submission_data = {
                    "type": st.session_state.inspection_type.lower(),
                    "building": building,
                    "date": str(inspection_date),
                    "inspector": inspector,
                    "aiReport": getattr(st.session_state, 'ai_report', ''),
                    "details": details,
                    "reportHTML": report_html,
                    "htmlVersion": "v2.0-inline-styles-only",  # Force cache refresh
                    "timestamp": datetime.now().isoformat(),
                    "htmlLength": len(report_html),
                    "htmlPreview": report_html[:200] + "..." if len(report_html) > 200 else report_html,
                    "debugInfo": {
                        "hasCSSClasses": "class=" in report_html,
                        "hasInlineStyles": "style=" in report_html,
                        "htmlStartsWith": report_html[:50],
                        "submissionSource": "streamlit-app-local"
                    }
                }
                # Database submission (Neon only)
                db_success = False
                if DATABASE_AVAILABLE and use_database:
                    with st.spinner("Saving to Neon database..."):
                        db_success, db_message = save_to_database(submission_data, None)
                st.subheader("\U0001F4BE Neon Database")
                if db_success:
                    st.success(db_message)
                else:
                    st.error(db_message)
                    if not (DATABASE_AVAILABLE and hasattr(st.session_state, 'db_connection_string') and use_database):
                        st.info("SQL database not configured or disabled")
            
    
    # Show recent inspections if requested
    if hasattr(st.session_state, 'show_data') and st.session_state.show_data:
        st.markdown("---")
        st.subheader("📊 Recent Inspections")
        
        # Show data from available storage
        if DATABASE_AVAILABLE and st.session_state.get('use_database', False):
            # Show Neon database data
            try:
                df = fetch_inspections(limit=10)
                if not df.empty:
                    st.subheader("📊 Neon Database Records")
                    st.dataframe(df, use_container_width=True)
                    # Optionally, add dashboard metrics if needed
            except Exception as e:
                st.error(f"Error loading Neon inspections: {e}")
        
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

# --- End of File ---

# The full code from inspection_app_template.py has been moved here for app.py.