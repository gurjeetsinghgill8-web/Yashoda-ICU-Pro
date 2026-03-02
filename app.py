import streamlit as st
from google import genai
import os
import requests
import pandas as pd
import plotly.graph_objects as go
from fpdf import FPDF
import tempfile
import datetime

# ==========================================
# 1. UI SETUP & CONFIGURATION
# ==========================================
st.set_page_config(page_title="Yashoda ICU Pro 8.0", layout="wide", page_icon="🏥")

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
        st.info("Authorized Personnel Only")
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
                    "date": row.get("date", str(datetime.date.today())),
                    "doctor": row.get("doctor", "Unknown"),
                    "raw_notes": row.get("raw_notes", ""),
                    "summary": row.get("summary", "")
                })
            st.session_state.patients_db = new_db
    except Exception as e:
        pass # Silent fail to avoid ugly UI errors

if 'patients_db' not in st.session_state:
    st.session_state.patients_db = {}
    sync_from_cloud() # Initial silent sync

def generate_true_pdf(title, patient_name, text_content):
    """Converts AI output into a beautiful, clean Hospital PDF (Removes ** stars)"""
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
    pdf.cell(0, 8, txt=f"Patient Name: {patient_name} | Treating Doctor: {st.session_state.logged_in_doctor}", ln=True)
    pdf.line(10, 50, 200, 50)
    pdf.ln(5)
    
    pdf.set_font("Arial", size=11)
    # Clean up markdown symbols for professional printing
    clean_text = text_content.replace('**', '').replace('*', '-').replace('#', '')
    
    # Handle Unicode characters by encoding
    clean_text = clean_text.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 7, txt=clean_text)
    
    temp_dir = tempfile.mkdtemp()
    filepath = os.path.join(temp_dir, f"{patient_name}_{title.replace(' ', '_')}.pdf")
    pdf.output(filepath)
    return filepath

# ==========================================
# 4. APP ARCHITECTURE (The 4 Master Tabs)
# ==========================================
st.sidebar.success(f"👨‍⚕️ Logged in as: **{st.session_state.logged_in_doctor}**")
if st.sidebar.button("Logout"):
    st.session_state.logged_in_doctor = None
    st.rerun()

st.title("🏥 Yashoda Cardiology: ICU Command Center Pro")

tab1, tab2, tab3, tab4 = st.tabs(["🩺 ICU Frontline", "📊 HOD Dashboard & Docs", "📉 Vitals Radar", "🔬 Academic Vault"])

# ---------------------------------------------------------
# TAB 1: THE ICU FRONTLINE (JUMBO EDIT & GUIDELINES)
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
            active_patients = [name for name, data in st.session_state.patients_db.items() if data["status"] == "Active"]
            p_name = st.selectbox("Select Existing Patient:", [""] + active_patients) if active_patients else ""

    st.markdown("---")
    
    # Vitals Input
    col_v1, col_v2, col_v3, col_v4 = st.columns(4)
    bp = col_v1.text_input("BP (e.g. 120/80)")
    hr = col_v2.text_input("Heart Rate (bpm)")
    spo2 = col_v3.text_input("SpO2 (%)")
    sugar = col_v4.text_input("Blood Sugar/RBS")

    # JUMBO EDIT WINDOW
    st.subheader("📝 Clinical Notes & Dictation (Jumbo Window)")
    st.info("💡 Tip: Press `Windows + H` to dictate notes directly here.")
    notes = st.text_area("Enter History, Symptoms, and Current Meds:", height=250)

    # QUICK INLINE GUIDELINE BUTTON
    with st.expander("📚 Quick Inline Guideline Search (For this patient)"):
        quick_query = st.text_input("Type topic (e.g., 'Amiodarone dosing in VT')")
        if st.button("Search Guideline"):
            res = client.models.generate_content(model='gemini-2.5-flash', contents=[f"Brief clinical guideline on: {quick_query}. Keep it point-wise and action-oriented for an ICU doctor."])
            st.info(res.text)

    if st.button("🚨 Analyze Patient & Generate Treatment Plan", type="primary"):
        if p_name and notes:
            with st.spinner("AI is analyzing DDx and Treatment Protocols..."):
                prompt = f"""
                You are the ICU Clinical AI at Yashoda Cardiology.
                Patient: {p_name}
                Vitals: BP {bp}, HR {hr}, SpO2 {spo2}, Sugar {sugar}
                Notes: {notes}
                
                Provide a structured response:
                1. CRITICAL ALERTS (If any based on vitals/notes)
                2. DIFFERENTIAL DIAGNOSIS (DDx)
                3. FINAL WORKING DIAGNOSIS
                4. MASTER TREATMENT PLAN (Meds, Drips, Dosages)
                5. DDI & SAFETY ALERTS (Drug interactions)
                """
                try:
                    response = client.models.generate_content(model='gemini-2.5-flash', contents=[prompt])
                    st.success("✅ Analysis Complete!")
                    st.markdown(response.text)
                    
                    payload = {
                        "action": "new_entry",
                        "patient_name": p_name,
                        "doctor": st.session_state.logged_in_doctor,
                        "raw_notes": f"BP:{bp} HR:{hr} SpO2:{spo2} Sugar:{sugar} | Notes: {notes}",
                        "summary": response.text
                    }
                    if WEBHOOK_URL.startswith("http"):
                        requests.post(WEBHOOK_URL, json=payload)
                        sync_from_cloud() # Auto Sync after save
                except Exception as e:
                    st.error(f"Error: {e}")
        else:
            st.warning("Enter Patient Name and Notes.")

# ---------------------------------------------------------
# TAB 2: WIDE HOD DASHBOARD & THE 4-PILLAR COUNSELING
# ---------------------------------------------------------
with tab2:
    st.header("Master Dashboard & PDF Generator")
    active_pts = {k: v for k, v in st.session_state.patients_db.items() if v["status"] == "Active"}
    
    if not active_pts:
        st.info("Ward is empty or syncing...")
    else:
        for pt_name, pt_data in active_pts.items():
            with st.expander(f"🛏️ {pt_name} | Last update by {pt_data['history'][-1]['doctor']}"):
                latest = pt_data['history'][-1]
                full_course = "".join([f"[{e['date']}] {e['raw_notes']}\n" for e in pt_data['history']])
                
                # HOD LIVE EDIT BOX
                st.markdown("**Current AI Plan (Editable by HOD/Senior):**")
                edited_summary = st.text_area("Edit Remarks/Treatment before PDF generation:", value=latest['summary'], height=150, key=f"edit_{pt_name}")

                st.markdown("---")
                st.markdown("### 🖨️ PDF Generation Engine")
                col1, col2, col3 = st.columns(3)
                
                # 1. CASE SUMMARY
                with col1:
                    if st.button("📄 Case Summary PDF", key=f"case_{pt_name}"):
                        with st.spinner("Drafting PDF..."):
                            prompt = f"Write a formal Medical Case Summary based on this: {edited_summary}. Do not use markdown stars."
                            res = client.models.generate_content(model='gemini-2.5-flash', contents=[prompt])
                            pdf_path = generate_true_pdf("INTERIM CASE SUMMARY", pt_name, res.text)
                            with open(pdf_path, "rb") as pdf_file:
                                st.download_button("📥 Download Summary PDF", data=pdf_file, file_name=f"{pt_name}_CaseSummary.pdf", mime="application/pdf", key=f"dl_case_{pt_name}")

                # 2. DISCHARGE SUMMARY
                with col2:
                    if st.button("📝 Discharge Summary PDF", key=f"disc_{pt_name}"):
                        with st.spinner("Drafting PDF..."):
                            prompt = f"Write a final Discharge Summary with Hospital Course, Final Diagnosis, and Discharge Meds based on: {edited_summary}. No markdown stars."
                            res = client.models.generate_content(model='gemini-2.5-flash', contents=[prompt])
                            pdf_path = generate_true_pdf("DISCHARGE SUMMARY", pt_name, res.text)
                            with open(pdf_path, "rb") as pdf_file:
                                st.download_button("📥 Download Discharge PDF", data=pdf_file, file_name=f"{pt_name}_Discharge.pdf", mime="application/pdf", key=f"dl_disc_{pt_name}")

                # 3. RELATIVES COUNSELING SHEET (THE MASTERSTROKE)
                with col3:
                    if st.button("🗣️ Relatives Counseling Sheet", type="primary", key=f"rel_{pt_name}"):
                        with st.spinner("Translating to simple Hinglish..."):
                            prompt = f"""
                            Based on this medical data: {edited_summary}
                            Write a "Patient Counseling Sheet" for the patient's relatives in simple, comforting Hinglish (Hindi written in English alphabets).
                            NO complex medical jargon.
                            Divide exactly into 4 sections:
                            1. Bimari (What exactly is the disease/problem)
                            2. Current Condition (How is the patient right now in the ICU)
                            3. Progress (Is there improvement compared to yesterday?)
                            4. Prognosis (What is the future plan and risk level)
                            """
                            res = client.models.generate_content(model='gemini-2.5-flash', contents=[prompt])
                            pdf_path = generate_true_pdf("ICU ATTENDANT BRIEF (Counseling Sheet)", pt_name, res.text)
                            with open(pdf_path, "rb") as pdf_file:
                                st.download_button("📥 Download Attendant Brief PDF", data=pdf_file, file_name=f"{pt_name}_Counseling.pdf", mime="application/pdf", key=f"dl_rel_{pt_name}")

# ---------------------------------------------------------
# TAB 3: VISUAL VITALS RADAR
# ---------------------------------------------------------
with tab3:
    st.header("📉 Visual Vitals Radar")
    st.info("Tracks the Systolic BP trend for the selected patient over their ICU stay.")
    all_pts = list(st.session_state.patients_db.keys())
    
    if all_pts:
        selected_pt = st.selectbox("Select Patient for Radar:", all_pts)
        history = st.session_state.patients_db[selected_pt]['history']
        
        dates = []
        sys_bps = []
        
        for entry in history:
            # Simple extraction logic for BP from raw notes
            notes = entry['raw_notes']
            if "BP:" in notes:
                try:
                    bp_str = notes.split("BP:")[1].split()[0] # Gets e.g., "120/80"
                    sys_bp = int(bp_str.split("/")[0])
                    dates.append(entry['date'])
                    sys_bps.append(sys_bp)
                except: pass
                
        if len(sys_bps) > 1:
            fig = go.Figure(data=go.Scatter(x=dates, y=sys_bps, mode='lines+markers', line=dict(color='red', width=3)))
            fig.update_layout(title="Systolic BP Trend in ICU", xaxis_title="Timeline", yaxis_title="Systolic BP (mmHg)")
            st.plotly_chart(fig, use_container_width=True)
            
            # AI Trend Analysis
            trend_prompt = f"Systolic BP readings over time: {sys_bps}. Write a 1-line trend analysis."
            res = client.models.generate_content(model='gemini-2.5-flash', contents=[trend_prompt])
            st.warning(f"🤖 AI Trend Insight: {res.text}")
        else:
            st.warning("Not enough BP data formatted correctly (e.g., BP: 120/80) to plot a chart yet.")

# ---------------------------------------------------------
# TAB 4: THE ACADEMIC VAULT
# ---------------------------------------------------------
with tab4:
    st.header("🔬 The Academic Vault")
    topic = st.text_input("Search Clinical Topic to Generate PDF Guideline (e.g., Post-MI Ventricular Arrhythmias):")
    
    if st.button("Generate & Download PDF Guideline"):
        if topic:
            with st.spinner("Researching latest protocols..."):
                prompt = f"Write a detailed clinical guideline for {topic}. Include Pathophysiology, Diagnostics, and Pharmacological treatment. No markdown stars."
                res = client.models.generate_content(model='gemini-2.5-flash', contents=[prompt])
                
                pdf_path = generate_true_pdf("CLINICAL GUIDELINE", "The Academic Vault", res.text)
                with open(pdf_path, "rb") as pdf_file:
                    st.download_button("📥 Save Guideline to Offline Vault (PDF)", data=pdf_file, file_name=f"Guideline_{topic.replace(' ','_')}.pdf", mime="application/pdf")
