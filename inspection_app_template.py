def get_all_inspection_ids():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id FROM inspections ORDER BY inspection_date DESC LIMIT 50")
    ids = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()
    return ids


# Gemini Pro Vision image analysis
import base64
import streamlit as st
import base64
def inject_custom_css():
    st.markdown(
        '''<style>
        body, .main, .block-container { font-family: "Segoe UI", "Roboto", "Arial", sans-serif; background: #f6f8fa; }
        .app-header { background: #009A44; color: #fff; padding: 24px 0 12px 0; text-align: center; border-radius: 0 0 16px 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.04); }
        .app-header h1 { font-size: 2.6rem; margin-bottom: 0.2em; letter-spacing: 1px; }
        .app-header img { margin-bottom: 0.5em; }
        .app-card { background: #fff; border-radius: 12px; box-shadow: 0 2px 12px rgba(0,0,0,0.07); padding: 32px 24px; margin-bottom: 32px; }
        .app-footer { text-align: center; color: #374151; font-size: 1.1rem; margin-top: 48px; padding-bottom: 16px; }
        .stButton>button, .stForm>button { background: #009A44; color: #fff; border-radius: 6px; font-size: 1.1rem; padding: 0.5em 1.5em; border: none; box-shadow: 0 1px 4px rgba(0,0,0,0.07); transition: background 0.2s; }
        .stButton>button:hover, .stForm>button:hover { background: #007a36; }
        .stTextInput>div>input, .stTextArea>div>textarea, .stSelectbox>div>div>select { border-radius: 6px; border: 1px solid #cfd8dc; font-size: 1.05rem; }
        .stCheckbox>div { font-size: 1.05rem; }
        .stForm { margin-bottom: 0; }
        .stMarkdown { font-size: 1.08rem; }
        </style>''', unsafe_allow_html=True)

def app_header():
    st.markdown(
        '''<div class="app-header">
            <h1>UND Housing Inspection Tool</h1>
            <div style="font-size:1.2rem; font-weight:400; margin-bottom:0.5em;">Facilities Management &amp; Inspections</div>
        </div>''', unsafe_allow_html=True)

def app_footer():
    st.markdown(
        '''<div class="app-footer">
            &copy; 2025 University of North Dakota &mdash; Housing Facilities<br>
            <span style="font-size:0.95rem;">For support, contact <a href="mailto:facilities@und.edu">facilities@und.edu</a></span>
        </div>''', unsafe_allow_html=True)
import bcrypt
def authenticate_user():
        st.markdown("# Login Required")
        with st.form("login_form"):
            email = st.text_input("Email", value="")
            password = st.text_input("Password", value="", type="password")
            submitted = st.form_submit_button("Login")
            if submitted:
                if email and password:
                    conn = get_conn()
                    cur = conn.cursor()
                    cur.execute("SELECT email, password_hash, first_name, last_name, position, is_admin FROM users WHERE email = %s", (email,))
                    user = cur.fetchone()
                    cur.close()
                    conn.close()
                    if user and bcrypt.checkpw(password.encode(), user[1].encode()):
                        st.session_state["user_email"] = user[0]
                        st.session_state["user_name"] = f"{user[2]} {user[3]}"
                        st.session_state["user_position"] = user[4]
                        st.session_state["is_admin"] = user[5]
                        st.session_state["app_state"] = "home"
                        st.success(f"Login successful! Email: {user[0]} | Name: {user[2]} {user[3]}")
                        st.rerun()
                    else:
                        st.error("Invalid email or password.")
                else:
                    st.error("Please enter both email and password.")
        st.stop()
st.set_page_config(
    page_title="UND Housing Inspection Tool",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="collapsed"
)
inject_custom_css()
if st.session_state.get("app_state") == "home":
    app_header()
import requests

# Gemini Pro Vision image analysis
import base64
import streamlit as st
import requests
import io

# Load Gemini API key from Streamlit secrets
GEMINI_API_KEY = st.secrets["api"]["gemini_api_key"] if "api" in st.secrets and "gemini_api_key" in st.secrets["api"] else None

def call_gemini_vision_api(image_bytes, model_name="models/gemini-1.5-pro-vision-latest"):
    if not GEMINI_API_KEY:
        return "Gemini Vision API key not configured."
    url = f"https://generativelanguage.googleapis.com/v1beta/{model_name}:generateContent?key={GEMINI_API_KEY}"
    # Encode image as base64
    b64_image = base64.b64encode(image_bytes).decode("utf-8")
    payload = {
        "contents": [
            {
                "parts": [
                    {"inline_data": {"mime_type": "image/png", "data": b64_image}}
                ]
            }
        ]
    }
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT building FROM inspections ORDER BY building")
    buildings = [row[0] for row in cur.fetchall() if row[0]]
    cur.close()
    conn.close()
    return buildings

def get_inspectors():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT inspector FROM inspections WHERE inspector IS NOT NULL AND inspector <> '' ORDER BY inspector")
    inspectors = [row[0] for row in cur.fetchall() if row[0]]
    cur.close()
    conn.close()
    return inspectors

def call_gemini_api(prompt, model_name=None):
    """Call Gemini API for AI analysis"""
    if not GEMINI_API_KEY:
        return "Gemini API key not configured."
    if not model_name:
        model_name = "models/gemini-2.5-flash"
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
    """Generate comprehensive APPA report prompt"""
    if not findings:
        return "Please complete some checklist items before generating a report."
    level_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    all_findings_text = []
    for category, item, rating, notes, photo in findings:
        if rating and rating != "Select":
            try:
                rating_num = int(str(rating).replace("Level ", ""))
            except:
                rating_num = 0
            if rating_num > 0:
                level_counts[rating_num] += 1
                finding_text = f"- {item}: Level {rating_num}"
                if notes.strip():
                    finding_text += f" (Inspector Notes: {notes})"
                if photo:
                    # Get image caption from Gemini Vision
                    try:
                        photo_bytes = photo.getvalue()
                        caption = call_gemini_vision_api(photo_bytes)
                        finding_text += f" (Photo: {caption})"
                    except Exception as e:
                        finding_text += " (Photo attached, caption error)"
                all_findings_text.append(finding_text)
    findings_text = "\n".join(all_findings_text)
    prompt = f"""You are a facilities management expert analyzing {inspection_type.lower()} inspection data for {building} using APPA standards.\n\n**INSPECTION SUMMARY:**\n• Level 1: {level_counts[1]} items\n• Level 2: {level_counts[2]} items\n• Level 3: {level_counts[3]} items\n• Level 4: {level_counts[4]} items\n• Level 5: {level_counts[5]} items\n\n**DETAILED FINDINGS:**\n{findings_text}\n\n**PROVIDE CONCISE ANALYSIS:**\n\n**OVERALL APPA LEVEL:** [Assign 1-5 with 2-sentence justification]\n\n**STRENGTHS:** [List 2-3 key Level 1-2 achievements]\n\n**URGENT ISSUES:** [List Level 4-5 items requiring immediate action]\n\n**ACTION PLAN:** [3-4 specific, prioritized recommendations]\n\n**MANAGEMENT ASSESSMENT:** [Brief comment on facility management effectiveness]\n\nKeep response under 400 words. Focus on actionable insights and APPA compliance."""
    return prompt

def convert_markdown_to_html(text):
    """Convert basic markdown formatting to HTML for emails"""
    if not text:
        return text
    import re
    text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    text = re.sub(r'\*\*([A-Z\s]+:)\*\*', r'<h4 style="color: #009A44; margin: 15px 0 5px 0; font-size: 16px;">\1</h4>', text)
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    text = text.replace('\n', '<br>')
    text = re.sub(r'<br>[•*] (.*?)(?=<br>|$)', r'<br>• \1', text)
    text = re.sub(r'<br>(\d+)\. (.*?)(?=<br>|$)', r'<br><strong>\1.</strong> \2', text)
    text = re.sub(r'(<br>){3,}', '<br><br>', text)
    text = text.lstrip('<br>')
    return text
import streamlit as st
edit_id = st.session_state.get("edit_id")
def clear_checklist_widget_state(checklist_data):
    # Debug: show raw loaded inspection data and items before checklist loop
    st.caption(f"[DEBUG] Raw loaded inspection data: {locals().get('inspection_data', 'N/A')}")
    st.caption(f"[DEBUG] Raw loaded items: {locals().get('items', 'N/A')}")
    for category, items in checklist_data.items():
        for item in items:
            rating_key = f"{category}_{item}_rating"
            notes_key = f"{category}_{item}_notes"
            if rating_key in st.session_state:
                del st.session_state[rating_key]
            if notes_key in st.session_state:
                del st.session_state[notes_key]

import psycopg2
from datetime import date

# --- Database connection ---
def get_conn():
    db = st.secrets["database"]
    return psycopg2.connect(
        dbname=db["NEON_DB_NAME"],
        user=db["NEON_DB_USER"],
        password=db["NEON_DB_PASSWORD"],
        host=db["NEON_DB_HOST"],
        port=db["NEON_DB_PORT"]
    )

# --- Data Model ---
def get_buildings():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT building FROM inspections ORDER BY building")
    buildings = [row[0] for row in cur.fetchall() if row[0]]
    cur.close()
    conn.close()
    return buildings

def get_inspectors():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT inspector FROM inspections WHERE inspector IS NOT NULL AND inspector <> '' ORDER BY inspector")
    inspectors = [row[0] for row in cur.fetchall() if row[0]]
    cur.close()
    conn.close()
    return inspectors
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT inspector FROM inspections WHERE inspector IS NOT NULL AND inspector <> '' ORDER BY inspector")
    inspectors = [row[0] for row in cur.fetchall() if row[0]]
    cur.close()
    conn.close()
    return inspectors
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT building FROM inspections ORDER BY building")
    buildings = [row[0] for row in cur.fetchall() if row[0]]
    cur.close()
    conn.close()
    return buildings

BUILDINGS = get_buildings()
INSPECTION_TYPES = ["Custodial", "Maintenance", "Grounds"]
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
        "Foundation & Walls", "Windows & Seals", "Doors & Hardware", "Roof & Gutters", "Walkways & Stairs", "Exterior Lighting"
    ],
    "Interior Common Areas (Lobbies, Hallways, Stairs)": [
        "Flooring Condition", "Wall & Ceiling Condition", "Paint Condition", "Doors & Hardware", "Handrails & Guardrails", "Lighting (Functionality)", "HVAC Vents & Grilles", "Fire & Life Safety"
    ],
    "Building Systems (General Observations)": [
        "HVAC Operation", "Plumbing (Public Areas)", "Electrical (Outlets/Switches)", "Elevator Operation"
    ],
    "Apartments/Dorms (Sample Inspection)": [
        "Door & Lockset", "Paint & Wall Condition", "Flooring Condition", "Windows & Blinds", "Plumbing Fixtures", "Appliances (If applicable)", "Lighting & Electrical"
    ]
}
GROUNDS_DATA = {
    "Landscaping (Seasonal)": [
        "Turf & Lawn Health", "Edging (Walks, Curbs)", "Plant Beds & Mulch", "Trees & Shrubs Pruning", "Weed Control", "Litter & Debris Removal"
    ],
    "Hardscapes & Site Amenities": [
        "Walkways & Patios Condition", "Benches & Site Furniture", "Trash & Ash Receptacles", "Bike Racks", "Signage"
    ],
    "Snow & Ice Removal (Seasonal)": [
        "Walkway & Sidewalk Clarity", "Entrances & ADA Ramps", "Stairs & Landings", "De-Icing Application", "Snow Pile Placement"
    ]
}

# --- Load Inspections ---
def fetch_inspections(building=None, inspector=None, date_filter=None):
    conn = get_conn()
    cur = conn.cursor()
    query = "SELECT id, building, inspection_date, inspector FROM inspections WHERE 1=1"
    params = []
    if building:
        query += " AND building = %s"
        params.append(building)
    if inspector:
        query += " AND inspector = %s"
        params.append(inspector)
    if date_filter:
        query += " AND inspection_date = %s"
        params.append(date_filter)
    query += " ORDER BY inspection_date DESC LIMIT 20"
    cur.execute(query, params)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

# --- Load Inspection Details ---
def load_inspection(inspection_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, building, inspector, inspection_type, inspection_date FROM inspections WHERE id = %s", (inspection_id,))
    row = cur.fetchone()
    inspection = {
        "id": row[0],
        "building": row[1],
        "inspector": row[2],
        "inspection_type": row[3],
        "inspection_date": row[4]
    } if row else {}
    cur.execute("SELECT id, category, item, rating, notes FROM inspection_items WHERE inspection_id = %s", (inspection_id,))
    items = []
    for r in cur.fetchall():
        item_id, category, item, rating, notes = r
        # Fetch all photos for this item
        cur.execute("SELECT photo FROM inspection_item_photos WHERE inspection_item_id = %s", (item_id,))
        photos = [p[0] for p in cur.fetchall() if p[0]]
        items.append({
            "category": category,
            "item": item,
            "rating": rating,
            "notes": notes,
            "photos": photos
        })
    cur.close()
    conn.close()
    return inspection, items

# --- Save/Update Inspection ---
def save_inspection(data, items, edit_id=None):
    conn = get_conn()
    cur = conn.cursor()
    if edit_id:
        cur.execute("UPDATE inspections SET building=%s, inspection_date=%s, inspector=%s, inspection_type=%s WHERE id=%s",
            (data["building"], data["inspection_date"], data["inspector"], data["inspection_type"], edit_id))
        cur.execute("DELETE FROM inspection_items WHERE inspection_id=%s", (edit_id,))
        inspection_id = edit_id
    else:
        cur.execute("INSERT INTO inspections (building, inspection_date, inspector, inspection_type) VALUES (%s, %s, %s, %s) RETURNING id",
            (data["building"], data["inspection_date"], data["inspector"], data["inspection_type"]))
        inspection_id = cur.fetchone()[0]
    for item_tuple in items:
        # Support multiple photos (last element is a list)
        if len(item_tuple) == 5:
            category, item, rating, notes, photo_list = item_tuple
        else:
            category, item, rating, notes = item_tuple
            photo_list = []
        # Always save category, even if blank
        cur.execute("INSERT INTO inspection_items (inspection_id, category, item, rating, notes) VALUES (%s, %s, %s, %s, %s) RETURNING id",
            (inspection_id, category if category else "", item, rating, notes))
        item_id = cur.fetchone()[0]
        # Save each photo in inspection_item_photos
        for photo in photo_list:
            if photo:
                cur.execute("INSERT INTO inspection_item_photos (inspection_item_id, photo) VALUES (%s, %s)", (item_id, photo.getvalue()))
    conn.commit()
    cur.close()
    conn.close()
    return inspection_id

# --- Sidebar: Lookup ---
st.sidebar.header("Inspection Workflow")
try:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM inspection_item_photos")
    photo_count = cur.fetchone()[0]
    cur.close()
    conn.close()
    st.sidebar.write(f"[DEBUG] Total photos in DB: {photo_count}")
except Exception as e:
    st.sidebar.write(f"[DEBUG] Photo count error: {e}")
if st.sidebar.button("New Inspection"):
    st.session_state._new_form_triggered = True
    st.session_state._edit_form_triggered = False
    st.session_state["edit_id"] = None
    st.session_state["new_inspection_type"] = None
    st.rerun()

if st.session_state.get('_new_form_triggered', False) and st.session_state.get("edit_id") is None:
    st.sidebar.markdown("---")
    st.sidebar.subheader("Select Inspection Type")
    # Always initialize selectbox from session state
    valid_types = ["Custodial", "Maintenance", "Grounds"]
    current_type = st.session_state.get("new_inspection_type")
    if current_type not in valid_types:
        st.session_state["new_inspection_type"] = "Custodial"
        current_type = "Custodial"
    selected_type = st.sidebar.selectbox(
        "Inspection Type",
        valid_types,
        index=valid_types.index(current_type)
    )
    # Update type in session state and rerun only if changed
    if st.session_state["new_inspection_type"] != selected_type:
        st.session_state["new_inspection_type"] = selected_type
        for checklist_data in [CUSTODIAL_DATA, MAINTENANCE_DATA, GROUNDS_DATA]:
            for category, items in checklist_data.items():
                for item in items:
                    rating_key = f"{category}_{item}_rating"
                    notes_key = f"{category}_{item}_notes"
                    if rating_key in st.session_state:
                        del st.session_state[rating_key]
                    if notes_key in st.session_state:
                        del st.session_state[notes_key]
        st.rerun()
if st.sidebar.button("Edit Previous Inspection"):
    st.session_state._edit_form_triggered = True
    st.session_state._new_form_triggered = False
    st.rerun()
if st.session_state.get('_edit_form_triggered', False):
    st.sidebar.markdown("---")
    st.sidebar.header("Lookup Inspections")
    building_filter = st.sidebar.selectbox("Building", ["All"] + BUILDINGS)
    inspectors = get_inspectors()
    inspector_filter = st.sidebar.selectbox("Inspector", ["All"] + inspectors)
    date_filter = st.sidebar.date_input("Date", value=None)
    photo_filter = st.sidebar.checkbox("Only show inspections with photos")
    # Store search results in session state to persist across reruns
    if st.sidebar.button("Search") or st.session_state.get("_search_triggered"):
        if not st.session_state.get("_search_triggered"):
            st.session_state["_search_triggered"] = True
            # Custom query for photo filter
            conn = get_conn()
            cur = conn.cursor()
            query = "SELECT i.id, i.building, i.inspection_date, i.inspector FROM inspections i"
            params = []
            if photo_filter:
                query = "SELECT DISTINCT i.id, i.building, i.inspection_date, i.inspector, i.inspection_type FROM inspections i "
                query += "INNER JOIN inspection_items ii ON ii.inspection_id = i.id "
                query += "INNER JOIN inspection_item_photos p ON p.inspection_item_id = ii.id WHERE 1=1 "
            else:
                query = "SELECT i.id, i.building, i.inspection_date, i.inspector, i.inspection_type FROM inspections i WHERE 1=1 "
            if building_filter != "All":
                query += " AND i.building = %s"
                params.append(building_filter)
            if inspector_filter != "All":
                query += " AND i.inspector ILIKE %s"
                params.append(inspector_filter)
            if date_filter:
                query += " AND i.inspection_date = %s"
                params.append(date_filter)
            query += " ORDER BY i.inspection_date DESC LIMIT 20"
            cur.execute(query, params)
            rows = cur.fetchall()
            cur.close()
            conn.close()
            st.session_state["_search_results"] = rows
        results = st.session_state.get("_search_results", [])
        st.sidebar.write("Results:")
        for result in results:
            if len(result) == 5:
                rid, bldg, dt, insp, form_type = result
            else:
                rid, bldg, dt, insp = result
                form_type = "Unknown"
            st.sidebar.markdown(f"<b>{form_type}</b> | <b>{bldg}</b> | {dt} | {insp}", unsafe_allow_html=True)
            st.sidebar.write(f"[DEBUG] Result: {result}")
            edit_btn_key = f"edit_{rid}_btn"
            if st.sidebar.button(f"Edit", key=edit_btn_key):
                st.session_state["edit_id"] = rid
                st.session_state.app_state = "edit_form"
                st.session_state._edit_form_triggered = False
                st.session_state._new_form_triggered = False
                st.session_state["_search_triggered"] = False
                # Clear widget keys for checklist before rerun
                for checklist_data in [CUSTODIAL_DATA, MAINTENANCE_DATA, GROUNDS_DATA]:
                    for category, items in checklist_data.items():
                        for item in items:
                            rating_key = f"{category}_{item}_rating"
                            notes_key = f"{category}_{item}_notes"
                            if rating_key in st.session_state:
                                del st.session_state[rating_key]
                            if notes_key in st.session_state:
                                del st.session_state[notes_key]
                st.rerun()
    else:
        # Clear previous search results if not searching
        st.session_state["_search_results"] = []
        st.session_state["_search_triggered"] = False

# --- Main Form ---
if "app_state" not in st.session_state:
    st.session_state["app_state"] = "login"
if st.session_state["app_state"] == "login":
    app_header()
    authenticate_user()
    st.stop()

if st.session_state["app_state"] == "home":
    # Add whitespace between header and action buttons
    st.markdown("<div style='height:32px;'></div>", unsafe_allow_html=True)
    action_cols = st.columns([1,1,1,1])
    with action_cols[0]:
        if st.button("Start New Inspection", use_container_width=True):
            st.session_state["app_state"] = "select_type"
            st.rerun()
    with action_cols[1]:
        if st.button("Edit Existing Inspection", use_container_width=True):
            st.session_state["app_state"] = "edit"
            st.rerun()
    with action_cols[2]:
        if st.session_state.get("is_admin") and st.button("Admin Page", use_container_width=True):
            st.session_state["app_state"] = "admin_page"
            st.rerun()
    with action_cols[3]:
        if st.button("Log Out", use_container_width=True):
            for k in ["user_email", "user_name", "user_position", "is_admin", "app_state"]:
                if k in st.session_state:
                    del st.session_state[k]
            st.session_state["app_state"] = "login"
            st.rerun()
    app_footer()
if st.session_state.get("app_state") == "admin_page" and st.session_state.get("is_admin"):
    st.markdown("<div style='height:32px;'></div>", unsafe_allow_html=True)
    st.markdown("# Admin Page")
    st.subheader("Add New User")
    with st.form("add_user_form"):
        email = st.text_input("Email")
        first_name = st.text_input("First Name")
        last_name = st.text_input("Last Name")
        position = st.text_input("Position")
        password = st.text_input("Password", type="password")
        is_admin = st.checkbox("Is Admin?")
        submitted = st.form_submit_button("Add User")
        if submitted:
            if email and first_name and last_name and password:
                password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
                conn = get_conn()
                cur = conn.cursor()
                try:
                    cur.execute("INSERT INTO users (email, password_hash, first_name, last_name, position, is_admin) VALUES (%s, %s, %s, %s, %s, %s)",
                                (email, password_hash, first_name, last_name, position, is_admin))
                    conn.commit()
                    st.success(f"User '{email}' added successfully.")
                except Exception as e:
                    st.error(f"Error adding user: {e}")
                finally:
                    cur.close()
                    conn.close()
            else:
                st.error("All fields except position are required.")

    # Reset password now part of manage users form below

    st.subheader("Manage Users")
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT email, first_name, last_name, position, is_admin FROM users ORDER BY email")
    users = cur.fetchall()
    cur.close()
    conn.close()
    user_emails = [u[0] for u in users]
    selected_user_email = st.selectbox("Select User to Manage", user_emails)
    selected_user = next((u for u in users if u[0] == selected_user_email), None)
    if selected_user:
        email, first_name, last_name, position, is_admin = selected_user
        with st.form("edit_user_form_single"):
            st.write(f"**{email}**")
            new_first_name = st.text_input("First Name", value=first_name)
            new_last_name = st.text_input("Last Name", value=last_name)
            new_position = st.text_input("Position", value=position)
            new_is_admin = st.checkbox("Is Admin?", value=is_admin)
            new_password = st.text_input("New Password (optional)", type="password")
            update_submitted = st.form_submit_button("Update User")
            delete_submitted = st.form_submit_button("Delete User")
            if update_submitted:
                conn = get_conn()
                cur = conn.cursor()
                try:
                    cur.execute("UPDATE users SET first_name = %s, last_name = %s, position = %s, is_admin = %s WHERE email = %s",
                                (new_first_name, new_last_name, new_position, new_is_admin, email))
                    if new_password:
                        password_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
                        cur.execute("UPDATE users SET password_hash = %s WHERE email = %s", (password_hash, email))
                    conn.commit()
                    st.success(f"User '{email}' updated.")
                    if new_password:
                        st.success(f"Password reset for user '{email}'.")
                except Exception as e:
                    st.error(f"Error updating user: {e}")
                finally:
                    cur.close()
                    conn.close()
            if delete_submitted:
                conn = get_conn()
                cur = conn.cursor()
                try:
                    cur.execute("DELETE FROM users WHERE email = %s", (email,))
                    conn.commit()
                    st.success(f"User '{email}' deleted.")
                except Exception as e:
                    st.error(f"Error deleting user: {e}")
                finally:
                    cur.close()
                    conn.close()

    colA, colB = st.columns([1,1])
    with colA:
        if st.button("Return to Main Page"):
            st.session_state["app_state"] = "home"
            st.rerun()
    with colB:
        if st.button("Log Out"):
            for k in ["user_email", "user_name", "user_position", "is_admin", "app_state"]:
                if k in st.session_state:
                    del st.session_state[k]
            st.session_state["app_state"] = "login"
            st.rerun()
    st.stop()

if st.session_state["app_state"] == "new":
    st.session_state['_new_form_triggered'] = True
    # ...existing code for new inspection form...
elif st.session_state["app_state"] == "edit":
    st.session_state['_edit_form_triggered'] = True
    st.session_state['edit_id'] = None  # Reset edit_id when entering selector
    st.markdown("---")
    st.header("Lookup Inspections")
    building_filter = st.selectbox("Building", ["All"] + BUILDINGS)
    inspectors = get_inspectors()
    inspector_filter = st.selectbox("Inspector", ["All"] + inspectors)
    date_filter = st.date_input("Date", value=None)
    photo_filter = st.checkbox("Only show inspections with photos")
    if st.button("Search") or st.session_state.get("_search_triggered"):
        if not st.session_state.get("_search_triggered"):
            st.session_state["_search_triggered"] = True
        conn = get_conn()
        cur = conn.cursor()
        params = []
        if photo_filter:
            query = "SELECT DISTINCT i.id, i.building, i.inspection_date, i.inspector, i.inspection_type FROM inspections i "
            query += "INNER JOIN inspection_items ii ON ii.inspection_id = i.id "
            query += "INNER JOIN inspection_item_photos p ON p.inspection_item_id = ii.id WHERE 1=1 "
        else:
            query = "SELECT i.id, i.building, i.inspection_date, i.inspector, i.inspection_type FROM inspections i WHERE 1=1 "
        if building_filter != "All":
            query += " AND i.building = %s"
            params.append(building_filter)
        if inspector_filter != "All":
            query += " AND i.inspector ILIKE %s"
            params.append(inspector_filter)
        if date_filter:
            query += " AND i.inspection_date = %s"
            params.append(date_filter)
        query += " ORDER BY i.inspection_date DESC LIMIT 20"
        cur.execute(query, params)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        st.session_state["_search_results"] = rows
    results = st.session_state.get("_search_results", [])
    st.write("Results:")
    for result in results:
        if len(result) == 5:
            rid, bldg, dt, insp, form_type = result
        else:
            rid, bldg, dt, insp = result
            form_type = "Unknown"
        edit_btn_key = f"edit_{rid}_btn"
        st.write(f"{form_type} | {bldg} | {dt} | {insp}")
        if st.button(f"Edit {bldg} {dt} {insp}", key=edit_btn_key):
            st.session_state["edit_id"] = rid
            st.session_state["app_state"] = "edit_form"
            st.session_state._edit_form_triggered = False
            st.session_state._new_form_triggered = False
            st.session_state["_search_triggered"] = False
            # Clear widget keys for checklist before rerun
            for checklist_data in [CUSTODIAL_DATA, MAINTENANCE_DATA, GROUNDS_DATA]:
                for category, items in checklist_data.items():
                    for item in items:
                        rating_key = f"{category}_{item}_rating"
                        notes_key = f"{category}_{item}_notes"
                        if rating_key in st.session_state:
                            del st.session_state[rating_key]
                        if notes_key in st.session_state:
                            del st.session_state[notes_key]
            st.rerun()
if st.session_state.get('_new_form_triggered', False):
    # Show inspection type selector before form
    st.session_state["app_state"] = "select_type"
    st.session_state["edit_id"] = None
if st.session_state.get("app_state") == "select_type":
    st.markdown("# Start New Inspection")
    valid_types = ["Custodial", "Maintenance", "Grounds"]
    selected_type = st.selectbox("Select Inspection Type", valid_types, key="new_type_select")
    if st.button("Begin Inspection"):
        st.session_state["new_inspection_type"] = selected_type
        st.session_state["app_state"] = "new_form"
        st.rerun()
elif st.session_state.get("app_state") == "new_form":
    selected_type = st.session_state.get("new_inspection_type", "Custodial")
    prefill = {
        "building": "",
        "inspection_date": None,
        "inspector": "",
        "inspection_type": selected_type
    }
    if selected_type == "Custodial":
        checklist_data = CUSTODIAL_DATA
    elif selected_type == "Maintenance":
        checklist_data = MAINTENANCE_DATA
    elif selected_type == "Grounds":
        checklist_data = GROUNDS_DATA
    else:
        checklist_data = CUSTODIAL_DATA
    item_prefill = {}
    building = prefill["building"]
    # Add navigation button above the form
    if st.button("Return to Main Page", key="return_home_new_form_top"):
        st.session_state["app_state"] = "home"
        st.rerun()
    ai_report_placeholder = st.empty()
    with st.form("inspection_form_new"):
        st.markdown(f"# {selected_type} Inspection Form")
        col1, col2, col3 = st.columns([2,2,2])
        hall_options = [
            "Swanson Hall", "Noren Hall", "Selke Hall", "Brannon Hall", "McVey Hall", "West Hall", "Smith Hall", "Johnstone Hall", "University Place"
        ]
        with col1:
            building = st.selectbox("Building", hall_options, index=hall_options.index(prefill.get("building", hall_options[0])) if prefill.get("building", "") in hall_options else 0, key="form_building_new")
        with col3:
            if st.session_state.get("is_admin"):
                inspectors = get_inspectors() if 'get_inspectors' in globals() else []
                inspector = st.selectbox("Inspector Name (Admin)", inspectors + [st.session_state.get("user_name", "")], index=(inspectors + [st.session_state.get("user_name", "")]).index(st.session_state.get("user_name", "")), key="form_inspector_admin_new")
            else:
                user_name = st.session_state.get('user_name', None)
                st.write(f"[DEBUG] Inspector Name: {user_name}")
                if user_name:
                    st.markdown(f"**Inspector Name:** {user_name}")
                else:
                    st.markdown("**Inspector Name:** _(Not logged in)_")
                inspector = user_name if user_name else ""
            inspection_date = st.date_input("Inspection Date", value=prefill.get("inspection_date", None), key="form_inspection_date_new")
        st.markdown("---")
        items_out = []
        for category, items in checklist_data.items():
            st.markdown(f"<div class='inspection-category' style='background: #f7f9fa; border-radius: 10px; padding: 18px 16px 8px 16px; margin-bottom: 18px; box-shadow: 0 2px 8px #e0e6ed;'>", unsafe_allow_html=True)
            st.markdown(f"<h4 style='margin-bottom: 8px; color: #2a3b4d;'>{category}</h4>", unsafe_allow_html=True)
            for item in items:
                st.markdown(f"<div class='inspection-item' style='background: #fff; border-radius: 8px; padding: 14px 12px; margin-bottom: 10px; box-shadow: 0 1px 4px #e0e6ed;'>", unsafe_allow_html=True)
                st.markdown(f"<span style='font-weight:600; font-size:1.08em; color:#1a2633;'>{item}</span>", unsafe_allow_html=True)
                rating, notes = item_prefill.get((category, item), ("Select", ""))
                widget_suffix = "_new"
                help_key = f"{category}_{item}_help{widget_suffix}"
                col_rating, col_help = st.columns([5,1])
                with col_rating:
                    rating_val = st.selectbox(
                        f"Rating for {item}",
                        ["Select", "Level 1", "Level 2", "Level 3", "Level 4", "Level 5"],
                        index=["Select", "Level 1", "Level 2", "Level 3", "Level 4", "Level 5"].index(rating),
                        key=f"{category}_{item}_rating{widget_suffix}"
                    )
                with col_help:
                    show_help = st.form_submit_button(f"Show Help for {item}", key=help_key)
                if show_help:
                    with st.expander(f"APPA Scoring Guidance for {item}", expanded=True):
                        appa_guidance = {
                            1: "Level 1: Orderly Spotlessness - Highest level, clean and well-maintained, no dust, dirt, or clutter.",
                            2: "Level 2: Ordinary Tidiness - Clean, but may have minor dust or dirt in corners, overall tidy.",
                            3: "Level 3: Casual Inattention - Acceptable, but more visible dust, dirt, or wear. Some clutter or minor issues.",
                            4: "Level 4: Moderate Dinginess - Noticeable dirt, wear, or neglect. Needs attention to restore standards.",
                            5: "Level 5: Unkempt Neglect - Major cleanliness or maintenance issues, significant dirt, damage, or clutter. Immediate action required."
                        }
                        for lvl in range(1,6):
                            st.markdown(f"**Level {lvl}:** {appa_guidance[lvl]}")
                st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
                notes_val = st.text_area(
                    f"Notes for {item}",
                    value=notes,
                    key=f"{category}_{item}_notes{widget_suffix}",
                    height=60,
                    placeholder="Add any specific observations or action items..."
                )
                st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
                photo_vals = []
                with st.expander("Attach photos (max 5, only for items of concern)"):
                    for i in range(1, 6):
                        photo_key = f"{category}_{item}_photo{i}{widget_suffix}"
                        photo_label = f"Photo {i} for {item} (optional)"
                        photo = st.camera_input(photo_label, key=photo_key)
                        if photo:
                            photo_vals.append(photo)
                st.markdown("</div>", unsafe_allow_html=True)
                items_out.append((category, item, rating_val, notes_val, photo_vals))
            st.markdown("</div>", unsafe_allow_html=True)
        # AI Analysis Section
        st.markdown("### 🤖 AI Analysis & APPA Assessment")
        ai_report_btn = st.form_submit_button("Generate AI Report & APPA Score")
        submitted = st.form_submit_button("Save Inspection")
        if ai_report_btn:
            if not items_out:
                st.error("Please complete some checklist items before generating a report.")
            else:
                with st.spinner("Generating comprehensive APPA analysis..."):
                    prompt = f"Generate a comprehensive APPA analysis for {building} with findings: {items_out}"
                    ai_report = call_gemini_api(prompt)
                    st.session_state["ai_report"] = ai_report
        if "ai_report" in st.session_state and st.session_state["ai_report"]:
            st.markdown('<div class="ai-report-area">', unsafe_allow_html=True)
            st.markdown(st.session_state["ai_report"])
            st.markdown('</div>', unsafe_allow_html=True)
        if submitted:
            data = {}
            data["building"] = building
            data["inspection_date"] = inspection_date
            data["inspector"] = inspector
            data["inspection_type"] = selected_type
            save_inspection(data, items_out, edit_id=None)
            st.success("Inspection saved!")
            st.session_state["edit_id"] = None
            st.session_state["app_state"] = "home"
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    app_footer()

if st.session_state.get("app_state") == "edit_form" and edit_id is not None:
    # Removed blank header divs for cleaner layout
    inspection_data, loaded_items = load_inspection(edit_id)
    prefill = inspection_data if inspection_data else {
        "building": "",
        "inspection_date": None,
        "inspector": "",
        "inspection_type": "Custodial"
    }
    # Placeholder for AI report display
    ai_report_placeholder = st.empty()
    # Navigation button above the form
    if st.button("Return to Main Screen", key="return_home_edit_form_top"):
        st.session_state["app_state"] = "home"
        st.rerun()
    # Define item_prefill for edit form
    # loaded_items is a list of tuples: (category, item, rating, notes, ...)
    item_prefill = {}
    if loaded_items:
        for entry in loaded_items:
            # Handle dict or tuple/list
            if isinstance(entry, dict):
                category = entry.get('category')
                item = entry.get('item')
                rating = entry.get('rating', "Select")
                notes = entry.get('notes', "")
            elif isinstance(entry, (list, tuple)) and len(entry) >= 4:
                category, item, rating, notes = entry[:4]
            else:
                continue
            if category and item:
                item_prefill[(category, item)] = (rating, notes)
    with st.form("inspection_form_edit2"):
        st.markdown(f"# {prefill.get('inspection_type', 'Custodial')} Inspection Form")
        col1, col2, col3 = st.columns([2,2,2])
        hall_options = [
            "Swanson Hall", "Noren Hall", "Selke Hall", "Brannon Hall", "McVey Hall", "West Hall", "Smith Hall", "Johnstone Hall", "University Place"
        ]
        with col1:
            building = st.selectbox("Building", hall_options, index=hall_options.index(prefill.get("building", hall_options[0])) if prefill.get("building", "") in hall_options else 0, key="form_building_edit")
        with col3:
            inspectors = get_inspectors() if 'get_inspectors' in globals() else []
            if st.session_state.get("is_admin"):
                inspector = st.selectbox("Inspector Name (Admin)", inspectors + [st.session_state.get("user_name", "")], index=(inspectors + [st.session_state.get("user_name", "")]).index(st.session_state.get("user_name", "")), key="form_inspector_admin_edit")
            else:
                user_name = st.session_state.get('user_name', None)
                st.write(f"[DEBUG] Inspector Name: {user_name}")
                if user_name:
                    st.markdown(f"**Inspector Name:** {user_name}")
                else:
                    st.markdown("**Inspector Name:** _(Not logged in)_")
                inspector = user_name if user_name else ""
        inspection_date = st.date_input("Inspection Date", value=prefill.get("inspection_date", None), key="form_inspection_date_edit")
        # Define checklist_data based on inspection_type
        inspection_type = prefill.get("inspection_type", "Custodial")
        if inspection_type:
            inspection_type = str(inspection_type).strip().capitalize()
        st.write(f"[DEBUG] Inspection Type: {inspection_type}")
        if inspection_type == "Custodial":
            checklist_data = CUSTODIAL_DATA
        elif inspection_type == "Maintenance":
            checklist_data = MAINTENANCE_DATA
        elif inspection_type == "Grounds":
            checklist_data = GROUNDS_DATA
        else:
            checklist_data = CUSTODIAL_DATA
        items_out = []
        # Define APPA guidance for each inspection type
        custodial_guidance = {
            1: "Level 1: Orderly Spotlessness - Highest level, clean and well-maintained, no dust, dirt, or clutter.",
            2: "Level 2: Ordinary Tidiness - Clean, but may have minor dust or dirt in corners, overall tidy.",
            3: "Level 3: Casual Inattention - Acceptable, but more visible dust, dirt, or wear. Some clutter or minor issues.",
            4: "Level 4: Moderate Dinginess - Noticeable dirt, wear, or neglect. Needs attention to restore standards.",
            5: "Level 5: Unkempt Neglect - Major cleanliness or maintenance issues, significant dirt, damage, or clutter. Immediate action required."
        }
        maintenance_guidance = {
            1: "Level 1: Fully Functional - All systems and components are in optimal working order, no repairs needed.",
            2: "Level 2: Minor Issues - Small repairs or maintenance needed, but does not affect overall function.",
            3: "Level 3: Noticeable Wear - Some systems/components show wear, may need attention soon.",
            4: "Level 4: Significant Deficiency - Major repairs needed, affects function or safety.",
            5: "Level 5: Critical Failure - System/component is non-functional or unsafe, immediate action required."
        }
        grounds_guidance = {
            1: "Level 1: Pristine - Grounds are perfectly maintained, no litter, weeds, or damage.",
            2: "Level 2: Well-kept - Minor imperfections, but overall neat and healthy.",
            3: "Level 3: Acceptable - Some weeds, litter, or minor damage present.",
            4: "Level 4: Neglected - Noticeable litter, weeds, or damage, needs attention.",
            5: "Level 5: Poor Condition - Major issues with cleanliness, safety, or appearance. Immediate action required."
        }
        for category, items in checklist_data.items():
            st.markdown(f"<div class='inspection-category' style='background: #f7f9fa; border-radius: 10px; padding: 18px 16px 8px 16px; margin-bottom: 18px; box-shadow: 0 2px 8px #e0e6ed;'>", unsafe_allow_html=True)
            st.markdown(f"<h4 style='margin-bottom: 8px; color: #2a3b4d;'>{category}</h4>", unsafe_allow_html=True)
            for item in items:
                st.markdown(f"<div class='inspection-item' style='background: #fff; border-radius: 8px; padding: 14px 12px; margin-bottom: 10px; box-shadow: 0 1px 4px #e0e6ed;'>", unsafe_allow_html=True)
                st.markdown(f"<span style='font-weight:600; font-size:1.08em; color:#1a2633;'>{item}</span>", unsafe_allow_html=True)
                rating, notes = item_prefill.get((category, item), ("Select", ""))
                widget_suffix = f"_{edit_id}" if edit_id is not None else ""
                col_rating, col_expander = st.columns([5,1])
                with col_rating:
                    rating_val = st.selectbox(
                        f"Rating for {item}",
                        ["Select", "Level 1", "Level 2", "Level 3", "Level 4", "Level 5"],
                        index=["Select", "Level 1", "Level 2", "Level 3", "Level 4", "Level 5"].index(rating),
                        key=f"{category}_{item}_rating{widget_suffix}"
                    )
                with col_expander:
                    with st.expander("APPA Guidance"):
                        if inspection_type == "Custodial":
                            guidance = custodial_guidance
                        elif inspection_type == "Maintenance":
                            guidance = maintenance_guidance
                        elif inspection_type == "Grounds":
                            guidance = grounds_guidance
                        else:
                            guidance = custodial_guidance
                        for lvl in range(1,6):
                            st.markdown(f"**Level {lvl}:** {guidance[lvl]}")
                st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
                notes_val = st.text_area(
                    f"Notes for {item}",
                    value=notes,
                    key=f"{category}_{item}_notes{widget_suffix}",
                    height=60,
                    placeholder="Add any specific observations or action items..."
                )
                st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
                # Prefill photo_vals with existing photos for this item
                photo_vals = []
                existing_photos = []
                if edit_id is not None and loaded_items:
                    for loaded_item in loaded_items:
                        if (
                            isinstance(loaded_item, dict)
                            and str(loaded_item.get("category")) == str(category)
                            and str(loaded_item.get("item")) == str(item)
                        ):
                            existing_photos = loaded_item.get("photos", [])
                            break
                photo_vals = existing_photos.copy() if existing_photos else []
                with st.expander("Attach photos (max 5, only for items of concern)"):
                    for i in range(1, 6):
                        photo_key = f"{category}_{item}_photo{i}{widget_suffix}"
                        photo_label = f"Photo {i} for {item} (optional)"
                        photo = st.camera_input(photo_label, key=photo_key)
                        if photo:
                            photo_vals.append(photo)
                st.markdown("</div>", unsafe_allow_html=True)
                items_out.append((category, item, rating_val, notes_val, photo_vals))
            st.markdown("</div>", unsafe_allow_html=True)
        # AI Analysis Section
        st.markdown("### 🤖 AI Analysis & APPA Assessment")
        ai_report_btn = st.form_submit_button("Generate AI Report & APPA Score")
        submitted = st.form_submit_button("Save Inspection")
        if ai_report_btn:
            if not items_out:
                st.error("Please complete some checklist items before generating a report.")
            else:
                with st.spinner("Generating comprehensive APPA analysis..."):
                    prompt = f"Generate a comprehensive APPA analysis for {building} with findings: {items_out}"
                    ai_report = call_gemini_api(prompt)
                    st.session_state["ai_report"] = ai_report
        if "ai_report" in st.session_state and st.session_state["ai_report"]:
            st.markdown('<div class="ai-report-area">', unsafe_allow_html=True)
            st.markdown(st.session_state["ai_report"])
            st.markdown('</div>', unsafe_allow_html=True)
        if submitted:
            data = {}
            data["building"] = building
            data["inspection_date"] = inspection_date
            data["inspector"] = inspector
            data["inspection_type"] = prefill.get("inspection_type", "Custodial")
            save_inspection(data, items_out, edit_id=edit_id)
            st.success("Inspection saved!")
            st.session_state["edit_id"] = None
            st.session_state["app_state"] = "home"
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
