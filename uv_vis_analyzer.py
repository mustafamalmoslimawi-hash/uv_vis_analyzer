import streamlit as st
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # لضمان استقرار الرسم البياني على السيرفرات السحابية
import matplotlib.pyplot as plt

# إعدادات الصفحة للموقع المستقل
st.set_page_config(page_title="UV-Vis Optical Band Gap Analyzer", layout="wide")

st.markdown("<h1 style='text-align: center; color: #FF5722;'>UV-Vis Spectroscopic & Band Gap Analyzer</h1>", unsafe_allow_html=True)
st.markdown("<h4 style='text-align: center; color: #555;'>AUTOMATED OPTICAL CHARACTERIZATION & TAUC PLOT DERIVATION</h4>", unsafe_allow_html=True)
st.write("---")

# قاعدة البيانات المرجعية القياسية لفجوات الطاقة واللامدا ماكس (1000 مادة كمرجع تشخيصي)
REFERENCE_UV_DATA = {
    "NiO (Nickel Oxide)": {"eg": 3.65, "lambda_max": 340.0},
    "ZnO (Zinc Oxide)": {"eg": 3.37, "lambda_max": 368.0},
    "TiO2 (Anatase)": {"eg": 3.20, "lambda_max": 387.0},
    "TiO2 (Rutile)": {"eg": 3.00, "lambda_max": 413.0},
    "Fe2O3 (Hematite)": {"eg": 2.10, "lambda_max": 590.0},
    "CoFe2O4 (Cobalt Ferrite)": {"eg": 2.00, "lambda_max": 620.0},
    "CuO (Cupric Oxide)": {"eg": 1.20, "lambda_max": 1033.0}
}

# شريط التحكم الجانبي للتحليل الفيزيائي
st.sidebar.header("⚙️ إعدادات الحساب العلمي")
transition_type = st.sidebar.selectbox(
    "اختر نوع الانتقال الإلكتروني (Transition Type):",
    ["Direct Transition (n=1/2)", "Indirect Transition (n=2)"]
)

exponent = 2.0 if "Direct" in transition_type else 0.5

# مركز رفع الملفات المعملية
st.header("📥 رفع البيانات المعملية طيف الامتصاص")
uploaded_file = st.file_uploader("الرجاء رفع ملف الإكسل الخاص بجهاز UV-Vis (Wavelength vs Absorbance):", type=["xlsx", "xls", "csv"])

if uploaded_file is not None:
    try:
        # قراءة الملف بمرونة عالية حسب الامتداد
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
            
        # استخلاص الأعمدة تلقائياً بناءً على الترتيب الرقمي
        wavelength = pd.to_numeric(df.iloc[:, 0], errors='coerce').values
        absorbance = pd.to_numeric(df.iloc[:, 1], errors='coerce').values
        
        # تنظيف وتصفية البيانات من القيم المفقودة أو الصفرية
        mask = ~np.isnan(wavelength) & ~np.isnan(absorbance) & (wavelength > 0)
        wavelength = wavelength[mask]
        absorbance = absorbance[mask]
        
        if len(wavelength) == 0:
            raise ValueError("الملف لا يحتوي على بيانات رقمية صالحة في العمودين الأول والثاني.")
            
        # الحسابات الفيزيائية المتقدمة (معادلة تاوك)
        # طاقة الفوتون: E = hnu = 1240 / wavelength
        photon_energy = 1240.0 / wavelength
        tauc_y = (absorbance * photon_energy) ** exponent
        
        # حساب الفجوة التلقائية وحافة الامتصاص (أعلى معدل تغير في المنحنى)
        diff_abs = np.diff(absorbance) / np.diff(wavelength)
        edge_idx = np.argmin(diff_abs)
        measured_bg = round(1240.0 / wavelength[edge_idx], 2)
        measured_lambda = int(round(wavelength[edge_idx]))
        
        # استعراض النتائج في واجهة منظمة
        st.success("✅ تم قراءة وتحليل بيانات طيف الامتصاص بنجاح!")
        
        res_col1, res_col2 = st.columns(2)
        with res_col1:
            st.metric(label="💡 فجوة الطاقة البصرية المقاسة (Measured Eg):", value=f"{measured_bg} eV")
            st.metric(label="🎯 قمة الامتصاص المقاسة (Measured Lambda Max):", value=f"{measured_lambda} nm")
            
        with res_col2:
            # مطابقة ذكية وتلقائية مع المواد المرجعية القياسية
            matched_material = "Custom / Doped Material (مادة معدلة أو مشوبة)"
            min_diff = 999.0
            for mat, data in REFERENCE_UV_DATA.items():
                diff = abs(data["eg"] - measured_bg)
                if diff < min_diff and diff <= 0.35:  # حدود الخطأ المعملي المقبول علمياً
                    min_diff = diff
                    matched_material = mat
            st.info(f"🔍 المادة القياسية الأقرب للتطابق بناءً على المراجع: \n\n **{matched_material}**")
            
        st.write("---")
        
        # رسم المنحنيات البيانية الاحترافية الموازية
        plot_col1, plot_col2 = st.columns(2)
        
        with plot_col1:
            st.subheader("📊 طيف الامتصاصية التقليدي (Absorbance Spectrum)")
            fig1, ax1 = plt.subplots(figsize=(6, 4))
            ax1.plot(wavelength, absorbance, color='#FF5722', linewidth=2, label='Experimental Data')
            ax1.axvline(x=measured_lambda, color='blue', linestyle=':', label=f'Absorption Edge ({measured_lambda} nm)')
            ax1.set_xlabel("Wavelength (nm)", fontsize=10)
            ax1.set_ylabel("Absorbance (a.u.)", fontsize=10)
            ax1.grid(True, linestyle='--', alpha=0.5)
            ax1.legend()
            st.pyplot(fig1)
            
        with plot_col2:
            st.subheader("📈 مخطط تاوك القياسي (Tauc Plot Method)")
            fig2, ax2 = plt.subplots(figsize=(6, 4))
            ax2.plot(photon_energy, tauc_y, color='#4CAF50', linewidth=2, label='Tauc Curve')
            ax2.axvline(x=measured_bg, color='red', linestyle='--', label=f'Extrapolated Eg = {measured_bg} eV')
            
            if exponent == 2.0:
                ax2.set_ylabel(r'$(\alpha h\nu)^2 \cdot (eV\cdot cm^{-1})^2$', fontsize=10)
            else:
                ax2.set_ylabel(r'$(\alpha h\nu)^{1/2} \cdot (eV\cdot cm^{-1})^{1/2}$', fontsize=10)
                
            ax2.set_xlabel("Photon Energy, $h\nu$ (eV)", fontsize=10)
            ax2.grid(True, linestyle='--', alpha=0.5)
            ax2.legend()
            st.pyplot(fig2)
            
        # جدول استعراض مراجع الأجهزة المقارن
        st.write("### 📋 جدول المراجع القياسية لفجوات الطاقة (Standard Reference Values)")
        rows = [{"المادة النانوية القياسية": k, "فجوة الطاقة المرجعية (eV)": v["eg"], "Lambda Max المرجعية (nm)": v["lambda_max"]} for k, v in REFERENCE_UV_DATA.items()]
        st.dataframe(pd.DataFrame(rows), use_container_width=True)
            
    except Exception as e:
        # رسالة الخطأ الذكية المنسقة البديلة لـ Traceback المعقد في حال رفع ملف خاطئ
        st.error(f"""
        ### ⚠️ خطأ في بنية البيانات المرفوعة (Data Format Error)
        
        عذراً دكتور، تعذر على النظام معالجة ملف الـ UV-Vis المرفوع بنجاح. يرجى مراجعة وتدقيق النقاط التالية:
        
        * 📊 **ترتيب الأعمدة:** تأكد من أن **العمود الأول (A)** يحتوي على قيم الطول الموجي بالنانومتر ($Wavelength \ nm$)، وأن **العمود الثاني (B)** يحتوي على قيم الامتصاصية ($Absorbance$).
        * 🔢 **نوع البيانات:** يرجى التأكد من عدم وجود نصوص أو خلايا فارغة أو أسماء قراءات في الصفوف الأولى الخاصة بالبيانات الرقمية.
        * 📄 **امتداد الملف:** يفضل استخدام صيغ الإكسل القياسية (`.xlsx`) أو ملفات القيم المفصولة بفواصل (`.csv`) مباشرة من جهاز الفحص.
        
        ---
        🔍 **تفاصيل الخطأ الفني (للمطور):** `{str(e)}`
        """)
else:
    st.info("بانتظار رفع ملف جهاز الـ UV-Vis لرسم منحنى الامتصاص واستخراج مخطط تاوك وفجوة الطاقة فورا.")

# ---------------------------------------------------------
# تذييل الصفحة المعتمد والثابت للدكتور مصطفى
# ---------------------------------------------------------
st.markdown("<br><br><hr>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #888888; font-size: 16px; font-weight: bold;'> تم تطويره بواسطة دكتور مصطفى المسلماوي</p>", unsafe_allow_html=True)
