import streamlit as st
from google import genai
import os
import requests
import pandas as pd
from fpdf import FPDF
import tempfile
import datetime
from PIL import Image

# ==========================================
# 1. UI SETUP & CONFIGURATION (No Sidebar)
# ==========================================
st.set_page_config(page_title="Yashoda ICU Pro - Space Optimized", layout="wide", page_icon="🏥", initial_sidebar_state="collapsed")

# --- APNA GOOGLE SHEET URL YAHAN DALEIN ---
WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbwIBxF5vh7uvdDnRblpyhfpQCtpcxWN3MlGjbt3SUeEO5KH3c9AIcU91BzeKVQKCn_L/exec" 

# ==========================================
# 2. DYNAMIC API KEY (THE MASTER JUGAAD)
# ==========================================
if 'api_key' not in st.session_state:
    st.session_state.api_key = os.getenv("GEMINI_API_KEY")

client = None
if st.session_state.api_key:
    try:
        client = genai.Client(api_key=st.session_state.api_key)
    except Exception:
        pass

# ==========================================
# 3. SECURITY & SMART ACCESS (PIN SYSTEM)
# ==========================================
DOCTOR_PINS = {
    "1234": "Dr. G.S. Gill (Cardiac Physician)",
    "0000": "Dr. Shivam Tomar (Cardiac Physician)",
    "9999": "Dr. Alok Sehgal (Senior Interventional Cardiologist)"
}

if 'logged_in_doctor' not in st.session_state:
    st.session_state.logged_in_doctor = None

if not st.session_state.logged_in_doctor:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🔐 Yashoda ICU Security Portal")
        st.info("Strict Medical Protocol Active. Enter PIN.")
        pin_input = st.text_input("Enter your 4-Digit PIN:", type="password", max_chars=4)
        if st.button("Login to Command Center", type="primary"):
            if pin_input in DOCTOR_PINS:
                st.session_state.logged_in_doctor = DOCTOR_PINS[pin_input]
                st.rerun()
            else:
                st.error("🚨 Invalid PIN! Access Denied.")
    st.stop()

# --- TOP NAVIGATION BAR (Space Saver) ---
col_head1, col_head2, col_head3 = st.columns([6, 3, 1])
with col_head1:
    st.title("🏥 Yashoda Cardiology: ICU Command Center Pro")
with col_head2:
    st.markdown("**HOD: Dr. Alok Sehgal** *(Sr. Interventional Cardiologist)*")
    st.markdown(f"**Duty:** {st.session_state.logged_in_doctor}")
with col_head3:
    if st.button("🚪 Logout"):
        st.session_state.logged_in_doctor = None
        st.rerun()
st.markdown("---")

if not client:
    st.error("🚨 AI Engine API Key is missing! Dr. Gill, please go to the 'Master Admin' tab to enter a new key.")

# ==========================================
# 4. CLOUD SYNC & TRUE PDF ENGINE
# ==========================================
def sync_from_cloud():
    if not WEBHOOK_URL.startswith("http"): return
    try:
        res = requests.get(WEBHOOK_URL)
        if res.status_code == 200:
            cloud_data = res.json()
            new_db = {}
            for row in cloud_data:
                p_name = row.get("patient_name", "")
                if not p_name: continue
                status = row.get("status", "Active")
                if p_name not in new_db: new_db[p_name] = {"status": status, "history": []}
                if status == "Discharged": new_db[p_name]["status"] = "Discharged"
                
                new_db[p_name]["history"].append({
                    "date": row.get("date", str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))),
                    "doctor": row.get("doctor", "Unknown"),
                    "raw_notes": row.get("raw_notes", ""),
                    "summary": row.get("summary", "")
                })
            st.session_state.patients_db = new_db
    except Exception as e:
        pass 

if 'patients_db' not in st.session_state:
    st.session_state.patients_db = {}
    sync_from_cloud() 

def generate_true_pdf(title, patient_name, text_content):
    """Converts text into a clean Hospital Letterhead PDF (No Markdown Stars)"""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, txt="YASHODA SUPERSPECIALITY HOSPITAL", ln=True, align='C')
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, txt="Department of Cardiology & Critical Care", ln=True, align='C')
    pdf.line(10, 30, 200, 30)
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, txt=title, ln=True, align='C')
    
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 8, txt="Admitted Under: Dr. Alok Sehgal (Senior Interventional Cardiologist)", ln=True)
    pdf.cell(0, 8, txt=f"Attending/Duty Doctor: {st.session_state.logged_in_doctor}", ln=True)
    pdf.cell(0, 8, txt=f"Patient Name: {patient_name} | Date: {datetime.date.today()}", ln=True)
    pdf.line(10, 75, 200, 75)
    pdf.ln(5)
    
    pdf.set_font("Arial", size=11)
    clean_text = text_content.replace('**', '').replace('*', '-').replace('#', '')
    clean_text = clean_text.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 7, txt=clean_text)
    
    temp_dir = tempfile.mkdtemp()
    filepath = os.path.join(temp_dir, f"{patient_name}_{title.replace(' ', '_')}.pdf")
    pdf.output(filepath)
    return filepath

# ==========================================
# 5. APP ARCHITECTURE (Dynamic Tabs)
# ==========================================
tab_titles = ["🩺 ICU Frontline", "📊 HOD Dashboard & Docs", "📉 Flowsheet & Trends", "🔬 Academic Vault"]

# SECRET ADMIN CHECK: Only show 5th tab if it's Dr. Gill
is_admin = (st.session_state.logged_in_doctor == "Dr. G.S. Gill (Cardiac Physician)")
if is_admin:
    tab_titles.append("⚙️ Master Admin")

tabs = st.tabs(tab_titles)
tab1, tab2, tab3, tab4 = tabs[0], tabs[1], tabs[2], tabs[3]

# ---------------------------------------------------------
# TAB 1: THE ICU FRONTLINE
# ---------------------------------------------------------
with tab1:
    col_pt1, col_pt2 = st.columns(2)
    with col_pt1:
        patient_type = st.radio("Patient Status:", ["New Admission", "Existing Patient"], horizontal=True)
    with col_pt2:
        if patient_type == "New Admission":
            p_name = st.text_input("Enter New Patient Name:").strip().title()
        else:
            active_pts = [name for name, data in st.session_state.patients_db.items() if data["status"] == "Active"]
            p_name = st.selectbox("Select Existing Patient:", [""] + active_pts) if active_pts else ""

    st.subheader("📝 Clinical Notes & Vitals (The Jumbo Window)")
    notes = st.text_area("Dictate complete clinical picture here:", height=200)

    st.subheader("📸 Attach ECG, X-Ray, or Lab Reports")
    col_cam1, col_cam2 = st.columns(2)
    with col_cam1:
        cam_pic = st.camera_input("Take a photo of the report")
    with col_cam2:
        uploaded_files = st.file_uploader("Upload images/PDFs from gallery", type=['jpg', 'jpeg', 'png', 'pdf'], accept_multiple_files=True)

    if st.button("🚨 Analyze Patient & Generate Treatment Plan", type="primary", use_container_width=True):
        if not client:
            st.error("API Key is missing! Cannot analyze.")
        elif p_name and notes:
            with st.spinner("Analyzing..."):
                try:
                    prompt = f"""
                    You are the Senior ICU Clinical AI. Patient: {p_name}. Notes: {notes}
                    Provide: 1. EXTRACTED VITALS 2. CRITICAL ALERTS 3. DIFFERENTIAL DIAGNOSIS 4. FINAL WORKING DIAGNOSIS 5. MASTER TREATMENT PLAN 6. DDI & SAFETY ALERTS.
                    DO NOT USE ANY MARKDOWN ASTERISKS (**). WRITE IN PLAIN TEXT ONLY.
                    At the end, suggest 3 specific Medical Topics, formatted exactly:
                    TOPICS: Topic 1, Topic 2, Topic 3
                    """
                    content_to_send = [prompt]
                    if cam_pic: content_to_send.append(Image.open(cam_pic))
                    if uploaded_files:
                        for f in uploaded_files:
                            if f.name.lower().endswith(('png', 'jpg', 'jpeg')): content_to_send.append(Image.open(f))

                    response = client.models.generate_content(model='gemini-1.5-flash', contents=content_to_send)
                    res_text = response.text.replace('**', '') 
                    
                    topics_list = []
                    if "TOPICS:" in res_text:
                        split_text = res_text.split("TOPICS:")
                        res_text = split_text[0].strip()
                        topics_list = [t.strip() for t in split_text[1].split(",")]
                        st.session_state[f"auto_topics_{p_name}"] = topics_list

                    st.success("✅ Analysis Complete!")
                    st.text(res_text) 
                    
                    payload = {"action": "new_entry", "patient_name": p_name, "doctor": st.session_state.logged_in_doctor, "raw_notes": notes, "summary": res_text}
                    if WEBHOOK_URL.startswith("http"):
                        requests.post(WEBHOOK_URL, json=payload)
                        sync_from_cloud() 
                except Exception as e:
                    error_msg = str(e)
                    if "429" in error_msg:
                        st.error("🚨 Limit Reached. Please use your Admin tab to update API key, or wait 1 minute.")
                    else:
                        st.error("🚨 System Error: Unable to process. Please check data.")
        else:
            st.warning("Please enter Patient Name and Notes.")

    st.markdown("---")
    st.subheader("📚 Quick Medical Guidelines Search")
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        auto_opts = st.session_state.get(f"auto_topics_{p_name}", [])
        selected_topic = st.selectbox("Select an AI suggested topic:", ["Choose..."] + auto_opts)
    with col_g2:
        custom_topic = st.text_input("Or type your own (e.g., Recent Hypertension Guideline):")
    
    final_topic = custom_topic if custom_topic else (selected_topic if selected_topic != "Choose..." else "")

    if st.button("📖 Read & Download Guideline"):
        if not client:
             st.error("API Key missing!")
        elif final_topic:
            with st.spinner(f"Fetching latest guidelines for {final_topic}..."):
                try:
                    guide_res = client.models.generate_content(model='gemini-1.5-flash', contents=[f"Provide a strict, professional ICU clinical guideline on: {final_topic}. DO NOT USE MARKDOWN ASTERISKS (**). Use plain text and numbering only."])
                    clean_guide = guide_res.text.replace('**', '')
                    st.info(clean_guide)
                    pdf_path = generate_true_pdf(f"GUIDELINE: {final_topic.upper()}", "Academic Reference", clean_guide)
                    with open(pdf_path, "rb") as pdf_file:
                        st.download_button("📥 Download This Guideline as PDF", data=pdf_file, file_name=f"Guideline_{final_topic.replace(' ','_')}.pdf", mime="application/pdf")
                except Exception as e:
                    st.error("🚨 Connection Error. Limit reached or network issue.")

# ---------------------------------------------------------
# TAB 2: HOD DASHBOARD & A4 EDIT WINDOW
# ---------------------------------------------------------
with tab2:
    st.header("Master Dashboard & Final Discharges")
    active_pts = {k: v for k, v in st.session_state.patients_db.items() if v["status"] == "Active"}
    
    if not active_pts:
        st.info("No active patients in the ICU.")
    else:
        for pt_name, pt_data in active_pts.items():
            with st.expander(f"🛏️ {pt_name} | Duty Dr: {pt_data['history'][-1]['doctor']}"):
                latest = pt_data['history'][-1]
                
                st.markdown("### 📝 Master HOD Editor")
                edited_summary = st.text_area("Final Output & Remarks:", value=latest['summary'].replace('**', ''), height=600, key=f"edit_{pt_name}")

                st.markdown("### 🖨️ Final PDF Generation")
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    if st.button("📄 Case Summary PDF", key=f"case_{pt_name}"):
                        pdf_path = generate_true_pdf("INTERIM CASE SUMMARY", pt_name, edited_summary)
                        with open(pdf_path, "rb") as pdf_file:
                            st.download_button("📥 Download Case PDF", data=pdf_file, file_name=f"{pt_name}_CaseSummary.pdf", mime="application/pdf", key=f"dl_case_{pt_name}")

                with col2:
                    if st.button("📝 Discharge Summary PDF", key=f"disc_{pt_name}"):
                        if not client: st.error("API Key missing!")
                        else:
                            with st.spinner("Drafting Final Discharge..."):
                                try:
                                    prompt = f"Write a final Discharge Summary based on this: {edited_summary}. DO NOT USE ANY MARKDOWN ASTERISKS (**). PLAIN TEXT ONLY."
                                    res = client.models.generate_content(model='gemini-1.5-flash', contents=[prompt])
                                    pdf_path = generate_true_pdf("DISCHARGE SUMMARY", pt_name, res.text.replace('**',''))
                                    with open(pdf_path, "rb") as pdf_file:
                                        st.download_button("📥 Download Discharge PDF", data=pdf_file, file_name=f"{pt_name}_Discharge.pdf", mime="application/pdf", key=f"dl_disc_{pt_name}")
                                except Exception as e:
                                    st.error("🚨 Engine is busy. Please try again.")

                with col3:
                    if st.button("🗣️ Attendant Counseling", key=f"rel_{pt_name}"):
                        if not client: st.error("API Key missing!")
                        else:
                            with st.spinner("Translating to Hinglish..."):
                                try:
                                    prompt = f"Based on: {edited_summary}. Write an ICU Patient Counseling Sheet for relatives in simple Hinglish. 4 Sections: 1. Bimari 2. Current Condition 3. Progress 4. Prognosis. NO MEDICAL JARGON. NO MARKDOWN ASTERISKS."
                                    res = client.models.generate_content(model='gemini-1.5-flash', contents=[prompt])
                                    pdf_path = generate_true_pdf("ICU ATTENDANT BRIEF", pt_name, res.text.replace('**',''))
                                    with open(pdf_path, "rb") as pdf_file:
                                        st.download_button("📥 Download Counseling PDF", data=pdf_file, file_name=f"{pt_name}_Counseling.pdf", mime="application/pdf", key=f"dl_rel_{pt_name}")
                                except Exception as e:
                                    st.error("🚨 Engine is busy. Please try again.")

                with col4:
                    if st.button("🛑 DISCHARGE & ARCHIVE", type="primary", key=f"done_{pt_name}"):
                        if WEBHOOK_URL.startswith("http"):
                            requests.post(WEBHOOK_URL, json={"action": "discharge", "patient_name": pt_name})
                            st.success(f"{pt_name} has been Discharged and Removed from Active Ward!")
                            sync_from_cloud()
                            st.rerun()

# ---------------------------------------------------------
# TAB 3: DIGITAL FLOWSHEET & AI TREND ANALYZER
# ---------------------------------------------------------
with tab3:
    st.header("📉 Patient Flowsheet & AI Trend Analyzer")
    all_pts = list(st.session_state.patients_db.keys())
    if all_pts:
        selected_pt = st.selectbox("Select Patient History:", all_pts)
        history = st.session_state.patients_db[selected_pt]['history']
        
        st.subheader("🕒 Chronological Digital Flowsheet")
        flow_data = [{"Date/Time": e['date'], "Duty Doctor": e['doctor'], "Raw Notes": e['raw_notes']} for e in reversed(history)]
        st.dataframe(pd.DataFrame(flow_data), use_container_width=True)
        
        st.markdown("---")
        if st.button("🔬 Analyze 48-Hour Clinical Trajectory", type="primary"):
            if not client: st.error("API Key missing!")
            else:
                with st.spinner("Analyzing historical trends..."):
                    try:
                        full_history = "\n".join([f"[{e['date']}] {e['raw_notes']}" for e in history])
                        res = client.models.generate_content(model='gemini-1.5-flash', contents=[f"Analyze this patient's timeline: {full_history}. Tell me if they are deteriorating, stable, or improving based on vitals."])
                        st.warning(f"🤖 AI Trend Insight:\n\n{res.text}")
                    except Exception as e:
                        st.error("🚨 Speed limit reached. Please wait and try again.")

# ---------------------------------------------------------
# TAB 4: THE ACADEMIC VAULT
# ---------------------------------------------------------
with tab4:
    st.header("🔬 The Academic Vault")
    topic = st.text_input("Search Clinical Topic (e.g., Post-MI Ventricular Arrhythmias):")
    
    if st.button("Generate Guideline to Read"):
        if not client: st.error("API Key missing!")
        elif topic:
            with st.spinner("Researching latest protocols..."):
                try:
                    prompt = f"Write a detailed clinical guideline for {topic}. Include Pathophysiology, Diagnostics, and Pharmacological treatment. DO NOT USE MARKDOWN ASTERISKS (**). PLAIN TEXT ONLY."
                    res = client.models.generate_content(model='gemini-1.5-flash', contents=[prompt])
                    clean_text = res.text.replace('**', '')
                    
                    st.session_state['vault_guideline_text'] = clean_text
                    st.session_state['vault_guideline_topic'] = topic
                except Exception as e:
                    st.error("🚨 Engine is busy. Please try again.")

    if 'vault_guideline_text' in st.session_state:
        st.markdown("### 📘 Reading Mode")
        st.info(st.session_state['vault_guideline_text'])
        
        pdf_path = generate_true_pdf("CLINICAL GUIDELINE", "The Academic Vault", st.session_state['vault_guideline_text'])
        with open(pdf_path, "rb") as pdf_file:
            st.download_button("📥 Save this Guideline to Offline Vault (PDF)", data=pdf_file, file_name=f"Guideline_{st.session_state['vault_guideline_topic'].replace(' ','_')}.pdf", mime="application/pdf")

# ---------------------------------------------------------
# TAB 5: SECRET ADMIN OVERRIDE (Dr. Gill ONLY)
# ---------------------------------------------------------
if is_admin:
    with tabs[4]:
        st.header("⚙️ Master Admin Console")
        st.warning("🔒 **RESTRICTED AREA:** Only visible to Commander Gill. Other doctors cannot see this tab.")
        st.markdown("Baar-baar GitHub kholne ki zaroorat nahi! Agar purani key ki limit khatam ho jaye, toh yahan seedha nayi API Key daaliye.")
        
        new_dynamic_key = st.text_input("🔑 Paste New Gemini API Key here:", type="password")
        
        if st.button("🚀 Update Engine Key", type="primary"):
            if new_dynamic_key:
                st.session_state.api_key = new_dynamic_key
                st.success("✅ Master Engine API Key Updated Successfully for this session!")
                st.rerun()
            else:
                st.error("Please paste a key first!")
