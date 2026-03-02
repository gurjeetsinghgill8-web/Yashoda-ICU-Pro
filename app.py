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
# 1. UI SETUP & CONFIGURATION
# ==========================================
st.set_page_config(page_title="Yashoda ICU Pro - Master Edition", layout="wide", page_icon="🏥")

# --- APNA GOOGLE SHEET URL YAHAN DALEIN ---
WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbwIBxF5vh7uvdDnRblpyhfpQCtpcxWN3MlGjbt3SUeEO5KH3c9AIcU91BzeKVQKCn_L/exec" 

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    st.error("🚨 GEMINI_API_KEY is missing in Cloud Secrets!")
    st.stop()
client = genai.Client(api_key=api_key)

# ==========================================
# 2. SECURITY & SMART ACCESS (PIN SYSTEM)
# ==========================================
DOCTOR_PINS = {
    "1234": "Dr. G.S. Gill",
    "0000": "Dr. Shivam Tomar",
    "9999": "Dr. Alok Sehgal (HOD)"
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
                st.success(f"Welcome, {st.session_state.logged_in_doctor}!")
                st.rerun()
            else:
                st.error("🚨 Invalid PIN! Access Denied.")
    st.stop()

# ==========================================
# 3. CLOUD SYNC & TRUE PDF ENGINE
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
        pass # Silent auto-sync

if 'patients_db' not in st.session_state:
    st.session_state.patients_db = {}
    sync_from_cloud() 

def generate_true_pdf(title, patient_name, text_content):
    """Converts AI output into a clean Hospital Letterhead PDF (Removes ** stars)"""
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
    
    # STRICT HIERARCHY IN PDF
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 8, txt="Admitted Under: Dr. Alok Sehgal (HOD Cardiology)", ln=True)
    pdf.cell(0, 8, txt=f"Attending/Duty Doctor: {st.session_state.logged_in_doctor}", ln=True)
    pdf.cell(0, 8, txt=f"Patient Name: {patient_name} | Date: {datetime.date.today()}", ln=True)
    pdf.line(10, 70, 200, 70)
    pdf.ln(5)
    
    pdf.set_font("Arial", size=11)
    # Clean formatting
    clean_text = text_content.replace('**', '').replace('*', '-').replace('#', '')
    clean_text = clean_text.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 7, txt=clean_text)
    
    temp_dir = tempfile.mkdtemp()
    filepath = os.path.join(temp_dir, f"{patient_name}_{title.replace(' ', '_')}.pdf")
    pdf.output(filepath)
    return filepath

# ==========================================
# 4. APP ARCHITECTURE (The 4 Master Tabs)
# ==========================================
st.sidebar.success(f"👨‍⚕️ Logged in: **{st.session_state.logged_in_doctor}**")
st.sidebar.markdown("**HOD:** Dr. Alok Sehgal")
if st.sidebar.button("Logout"):
    st.session_state.logged_in_doctor = None
    st.rerun()

st.title("🏥 Yashoda Cardiology: ICU Command Center Pro")

tab1, tab2, tab3, tab4 = st.tabs(["🩺 ICU Frontline", "📊 HOD Dashboard & Docs", "📉 Flowsheet & Trends", "🔬 Academic Vault"])

# ---------------------------------------------------------
# TAB 1: THE ICU FRONTLINE (Jumbo Box & Camera)
# ---------------------------------------------------------
with tab1:
    st.header("Patient Triage & Clinical Entry")
    
    col_pt1, col_pt2 = st.columns(2)
    with col_pt1:
        patient_type = st.radio("Patient Status:", ["New Admission", "Existing Patient"], horizontal=True)
    
    with col_pt2:
        if patient_type == "New Admission":
            p_name = st.text_input("Enter New Patient Name:").strip().title()
        else:
            active_pts = [name for name, data in st.session_state.patients_db.items() if data["status"] == "Active"]
            p_name = st.selectbox("Select Existing Patient:", [""] + active_pts) if active_pts else ""

    st.markdown("---")
    
    # 1. THE JUMBO BOX
    st.subheader("📝 Clinical Notes & Vitals (The Jumbo Window)")
    st.info("💡 Tip: Press `Windows + H`. Dictate everything in one breath (e.g., 'Patient has chest pain, BP is 140/90, Sugar 200, HR 110'). AI will extract it all.")
    notes = st.text_area("Dictate complete clinical picture here:", height=200)

    # 2. MULTI-PAGE LIVE CAMERA & UPLOAD
    st.markdown("---")
    st.subheader("📸 Attach ECG, X-Ray, or Lab Reports")
    col_cam1, col_cam2 = st.columns(2)
    with col_cam1:
        st.write("**Option A: Live Camera** (Takes 1 photo at a time)")
        cam_pic = st.camera_input("Take a photo of the report")
    with col_cam2:
        st.write("**Option B: Multi-Page Upload** (Select 5-6 photos from gallery/phone)")
        uploaded_files = st.file_uploader("Upload images/PDFs", type=['jpg', 'jpeg', 'png', 'pdf'], accept_multiple_files=True)

    if st.button("🚨 Analyze Patient & Generate Treatment Plan", type="primary", use_container_width=True):
        if p_name and notes:
            with st.spinner("AI Medical Engine is analyzing the full clinical picture..."):
                prompt = f"""
                You are the Senior ICU Clinical AI at Yashoda Cardiology.
                Patient: {p_name}
                Raw Dictation (Extract Vitals & Symptoms from this): {notes}
                
                Provide a structured medical response:
                1. EXTRACTED VITALS: (List BP, HR, SpO2, Sugar clearly)
                2. CRITICAL ALERTS: (Highlight abnormal values in RED)
                3. DIFFERENTIAL DIAGNOSIS (DDx):
                4. FINAL WORKING DIAGNOSIS:
                5. MASTER TREATMENT PLAN: (Meds, Drips, Dosages)
                6. DDI & SAFETY ALERTS: (Drug interactions)
                
                Also, at the very end, suggest exactly 3 comma-separated specific Medical Topics/Guidelines related to this case, formatted exactly like this:
                TOPICS: Topic 1, Topic 2, Topic 3
                """
                
                content_to_send = [prompt]
                if cam_pic: content_to_send.append(Image.open(cam_pic))
                if uploaded_files:
                    for f in uploaded_files:
                        if f.name.lower().endswith(('png', 'jpg', 'jpeg')):
                            content_to_send.append(Image.open(f))

                try:
                    response = client.models.generate_content(model='gemini-2.5-flash', contents=content_to_send)
                    
                    # Smart Guidelines Extraction logic
                    res_text = response.text
                    topics_list = []
                    if "TOPICS:" in res_text:
                        split_text = res_text.split("TOPICS:")
                        res_text = split_text[0].strip()
                        topics_list = [t.strip() for t in split_text[1].split(",")]
                        st.session_state[f"auto_topics_{p_name}"] = topics_list

                    st.success("✅ Analysis Complete!")
                    st.markdown(res_text)
                    
                    # Save to Cloud
                    payload = {
                        "action": "new_entry",
                        "patient_name": p_name,
                        "doctor": st.session_state.logged_in_doctor,
                        "raw_notes": notes,
                        "summary": res_text
                    }
                    if WEBHOOK_URL.startswith("http"):
                        requests.post(WEBHOOK_URL, json=payload)
                        sync_from_cloud() 
                except Exception as e:
                    st.error(f"Error: {e}")
        else:
            st.warning("Please enter Patient Name and Notes.")

    # 3. SMART AI GUIDELINES (ON-SCREEN DROPDOWN)
    if p_name and f"auto_topics_{p_name}" in st.session_state and st.session_state[f"auto_topics_{p_name}"]:
        st.markdown("---")
        st.subheader("📚 Smart On-Screen Guidelines (Recommended by AI)")
        selected_topic = st.selectbox("Select a topic to read right now:", ["Choose a topic..."] + st.session_state[f"auto_topics_{p_name}"])
        
        if selected_topic != "Choose a topic...":
            with st.spinner(f"Loading latest guidelines for {selected_topic}..."):
                guide_res = client.models.generate_content(model='gemini-2.5-flash', contents=[f"Provide a brief, strict ICU clinical guideline on: {selected_topic}."])
                st.info(guide_res.text)

# ---------------------------------------------------------
# TAB 2: HOD DASHBOARD & A4 EDIT WINDOW
# ---------------------------------------------------------
with tab2:
    st.header("Master Dashboard & PDF Generators")
    active_pts = {k: v for k, v in st.session_state.patients_db.items() if v["status"] == "Active"}
    
    if not active_pts:
        st.info("No active patients in the ICU.")
    else:
        for pt_name, pt_data in active_pts.items():
            with st.expander(f"🛏️ {pt_name} | Under: Dr. Alok Sehgal | Duty Dr: {pt_data['history'][-1]['doctor']}"):
                latest = pt_data['history'][-1]
                
                # THE A4-SIZE HOD EDIT WINDOW (Height 500)
                st.markdown("### 📝 Master Edit Window (HOD & Senior Doctors)")
                st.caption("Review and edit the AI's generated summary below before converting it into a PDF.")
                edited_summary = st.text_area("Final Output & Remarks:", value=latest['summary'], height=500, key=f"edit_{pt_name}")

                st.markdown("### 🖨️ PDF Engine & Actions")
                col1, col2, col3, col4 = st.columns(4)
                
                # 1. CASE SUMMARY
                with col1:
                    if st.button("📄 Case Summary PDF", key=f"case_{pt_name}"):
                        with st.spinner("Drafting..."):
                            pdf_path = generate_true_pdf("INTERIM CASE SUMMARY", pt_name, edited_summary)
                            with open(pdf_path, "rb") as pdf_file:
                                st.download_button("📥 Download Case PDF", data=pdf_file, file_name=f"{pt_name}_CaseSummary.pdf", mime="application/pdf", key=f"dl_case_{pt_name}")

                # 2. DISCHARGE SUMMARY
                with col2:
                    if st.button("📝 Discharge Summary PDF", key=f"disc_{pt_name}"):
                        with st.spinner("Drafting..."):
                            prompt = f"Write a final Discharge Summary with Hospital Course, Final Diagnosis, and Discharge Meds based on: {edited_summary}. No markdown stars."
                            res = client.models.generate_content(model='gemini-2.5-flash', contents=[prompt])
                            pdf_path = generate_true_pdf("DISCHARGE SUMMARY", pt_name, res.text)
                            with open(pdf_path, "rb") as pdf_file:
                                st.download_button("📥 Download Discharge PDF", data=pdf_file, file_name=f"{pt_name}_Discharge.pdf", mime="application/pdf", key=f"dl_disc_{pt_name}")

                # 3. COUNSELING SHEET (THE MASTERSTROKE)
                with col3:
                    if st.button("🗣️ Attendant Counseling", key=f"rel_{pt_name}"):
                        with st.spinner("Translating to Hinglish..."):
                            prompt = f"Based on this: {edited_summary}. Write an ICU Patient Counseling Sheet for relatives in simple Hinglish. 4 Sections: 1. Bimari (Disease) 2. Current Condition 3. Progress 4. Prognosis. No medical jargon."
                            res = client.models.generate_content(model='gemini-2.5-flash', contents=[prompt])
                            pdf_path = generate_true_pdf("ICU ATTENDANT BRIEF (Counseling)", pt_name, res.text)
                            with open(pdf_path, "rb") as pdf_file:
                                st.download_button("📥 Download Counseling PDF", data=pdf_file, file_name=f"{pt_name}_Counseling.pdf", mime="application/pdf", key=f"dl_rel_{pt_name}")

                # 4. DISCHARGE & ARCHIVE BUTTON
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
        
        # 1. THE CHRONOLOGICAL FLOWSHEET (TABLE)
        st.subheader("🕒 Chronological Digital Flowsheet")
        flow_data = []
        for entry in reversed(history):
            flow_data.append({
                "Date/Time": entry['date'],
                "Duty Doctor": entry['doctor'],
                "Raw Clinical Dictation": entry['raw_notes']
            })
        st.dataframe(pd.DataFrame(flow_data), use_container_width=True)
        
        # 2. THE AI TREND ANALYZER
        st.markdown("---")
        if st.button("🔬 Analyze 48-Hour Clinical Trajectory", type="primary"):
            with st.spinner("AI is analyzing all historical notes to find trends..."):
                full_history = "\n".join([f"[{e['date']}] {e['raw_notes']}" for e in history])
                prompt = f"""
                You are a Senior Critical Care Specialist analyzing an ICU patient's timeline.
                Patient Data: {full_history}
                
                Write a highly professional "Clinical Trajectory Report".
                Tell me if the patient is deteriorating, stable, or improving. 
                Focus specifically on trends in BP, SpO2, and Sugar if mentioned.
                """
                res = client.models.generate_content(model='gemini-2.5-flash', contents=[prompt])
                st.warning("🤖 AI Trend Insight:")
                st.markdown(res.text)

# ---------------------------------------------------------
# TAB 4: THE ACADEMIC VAULT
# ---------------------------------------------------------
with tab4:
    st.header("🔬 The Academic Vault")
    topic = st.text_input("Search Clinical Topic to Generate PDF Guideline:")
    
    if st.button("Generate & Download PDF Guideline"):
        if topic:
            with st.spinner("Researching latest protocols..."):
                prompt = f"Write a detailed clinical guideline for {topic}. Include Pathophysiology, Diagnostics, and Pharmacological treatment. No markdown stars."
                res = client.models.generate_content(model='gemini-2.5-flash', contents=[prompt])
                
                pdf_path = generate_true_pdf("CLINICAL GUIDELINE", "The Academic Vault", res.text)
                with open(pdf_path, "rb") as pdf_file:
                    st.download_button("📥 Save Guideline to Offline Vault (PDF)", data=pdf_file, file_name=f"Guideline_{topic.replace(' ','_')}.pdf", mime="application/pdf")
