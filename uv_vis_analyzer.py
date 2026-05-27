import streamlit as st
import pandas as pd
import numpy as np
import io

# إعدادات الواجهة المستقلة والذكية لموقع الـ UV-Vis
st.set_page_config(page_title="UV-Vis Optical Band Gap Analyzer", layout="wide")

st.markdown("<h1 style='text-align: center; color: #FF5722;'>UV-Vis Spectroscopic & Band Gap Analyzer</h1>", unsafe_allow_html=True)
st.markdown("<h4 style='text-align: center; color: #555;'>AUTOMATED OPTICAL CHARACTERIZATION & TAUC PLOT DIAGNOSIS</h4>", unsafe_allow_html=True)
st.write("---")

# قاعدة البيانات المرجعية القياسية المدمجة للتشخيص التلقائي الفوري
REFERENCE_UV_DATA = {
    "NiO (Nickel Oxide)": {"eg": 3.65, "lambda_max": 340.0},
    "ZnO (Zinc Oxide)": {"eg": 3.37, "lambda_max": 368.0},
    "TiO2 (Anatase Phase)": {"eg": 3.20, "lambda_max": 387.0},
    "TiO2 (Rutile Phase)": {"eg": 3.00, "lambda_max": 413.0},
    "a-Fe2O3 (Hematite)": {"eg": 2.10, "lambda_max": 590.0},
    "CoFe2O4 (Cobalt Ferrite)": {"eg": 2.00, "lambda_max": 620.0},
    "CuO (Cupric Oxide)": {"eg": 1.20, "lambda_max": 1033.0}
}

# شريط التحكم الجانبي للمعاملات الفيزيائية والميكانيكية للطيف
st.sidebar.header("⚙️ إعدادات الحساب العلمي")
transition_type = st.sidebar.selectbox(
    "اختر نوع الانتقال الإلكتروني (Transition Type):",
    ["Direct Transition (n=1/2)", "Indirect Transition (n=2)"]
)

exponent = 2.0 if "Direct" in transition_type else 0.5

# مركز رفع الملفات المعملية - تم تخصيصه لملفات الإكسل المحددة فقط
st.header("📥 رفع البيانات المعملية طيف الامتصاص")
uploaded_file = st.file_uploader("الرجاء رفع ملف جهاز UV-Vis بصيغة إكسل (Wavelength vs Absorbance):", type=["xlsx", "xls"])

if uploaded_file is not None:
    try:
        # قراءة آلية هجينة خالية تماماً من الاعتماد على المكتبات الخارجية لتفادي نقص السيرفر
        file_bytes = uploaded_file.read()
        try:
            df = pd.read_excel(io.BytesIO(file_bytes))
        except Exception:
            try:
                df = pd.read_excel(io.BytesIO(file_bytes), engine='openpyxl')
            except Exception:
                try:
                    df = pd.read_excel(io.BytesIO(file_bytes), engine='xlrd')
                except Exception:
                    html_data = pd.read_html(io.BytesIO(file_bytes))
                    df = html_data[0]
            
        # تنظيف وفلترة الصفوف النصية الأولى (الترويسات التعريفية للأجهزة)
        for i in range(min(len(df), 40)):
            v1 = pd.to_numeric(df.iloc[i:, 0], errors='coerce')
            v2 = pd.to_numeric(df.iloc[i:, 1], errors='coerce')
            if v1.notna().sum() > 5 and v2.notna().sum() > 5:
                df = df.iloc[i:].reset_index(drop=True)
                break

        # استخلاص المصفوفات الرقمية النقية
        col1 = pd.to_numeric(df.iloc[:, 0], errors='coerce').values
        col2 = pd.to_numeric(df.iloc[:, 1], errors='coerce').values
        
        # استبعاد الخلايا الفارغة أو الشاذة رياضياً لقفل النطاقات
        mask = ~np.isnan(col1) & ~np.isnan(col2) & ~np.isinf(col1) & ~np.isinf(col2)
        col1 = col1[mask]
        col2 = col2[mask]
        
        if len(col1) == 0:
            raise ValueError("الملف المرفوع لا يحتوي على قراءات رقمية متناسقة في أول عمودين.")
            
        # خوارزمية التمييز الذكي للمحاور (تحديد أطوال النانومتر الكبيرة مقابل قراءات الامتصاصية الصغيرة)
        if np.nanmean(col2) > np.nanmean(col1):
            wavelength = col2
            absorbance = col1
        else:
            wavelength = col1
            absorbance = col2

        # الترتيب الهندسي التصاعدي للمنحنيات الطيفية
        sort_idx = np.argsort(wavelength)
        wavelength = wavelength[sort_idx]
        absorbance = absorbance[sort_idx]

        # حصر النطاق الضوئي للـ UV-Vis وحماية المحور الشاقولي من التشتت والصفار
        real_mask = (wavelength >= 250) & (wavelength <= 950) & (absorbance >= 0) & (absorbance <= 10)
        wavelength = wavelength[real_mask]
        absorbance = absorbance[real_mask]

        if len(wavelength) == 0:
            raise ValueError("النطاق الرقمي داخل الملف يقع خارج حدود القياس البصري المعتمد.")

        # الحسابات الفيزيائية الكمية (معادلة تاوك واشتقاق حافة الامتصاص الحرجة)
        photon_energy = 1240.0 / wavelength
        tauc_y = (absorbance * photon_energy) ** exponent
        
        # اشتقاق فجوة الحزمة البصرية تلقائياً
        diff_abs = np.diff(absorbance) / np.diff(wavelength)
        edge_idx = np.argmin(diff_abs) if len(diff_abs) > 0 else 0
        measured_bg = round(1240.0 / wavelength[edge_idx], 2)
        measured_lambda = int(round(wavelength[edge_idx]))
        
        # عرض واجهة النتائج والتحليل التشخيصي المباشر
        st.success("✅ تم الفحص الرياضي الشامل وإعداد المنحنيات البيانية بنجاح!")
        
        res_col1, res_col2 = st.columns(2)
        with res_col1:
            st.metric(label="💡 فجوة الطاقة البصرية المقاسة (Measured Eg):", value=f"{measured_bg} eV")
            st.metric(label="🎯 حافة الامتصاص القياسية (Absorption Edge):", value=f"{measured_lambda} nm")
            
        with res_col2:
            matched_material = "Custom / Doped Material (مادة معدلة أو مشوبة)"
            min_diff = 999.0
            for mat, data in REFERENCE_UV_DATA.items():
                diff = abs(data["eg"] - measured_bg)
                if diff < min_diff and diff <= 0.35:
                    min_diff = diff
                    matched_material = mat
            st.info(f"🔍 المادة القياسية الأقرب للتطابق بناءً على المراجع: \n\n **{matched_material}**")
            
        st.write("---")
        
        # توليد الرسوم البيانية التفاعلية الثابتة والمحمية ذاتياً عبر محرك Area السحابي المدمج في ستريمليت
        plot_col1, plot_col2 = st.columns(2)
        
        with plot_col1:
            st.subheader("📊 طيف الامتصاصية التفاعلي (Absorbance Spectrum)")
            # صياغة جدول مفرغ ومحاذاة الفهرس مباشرة على الطول الموجي لإجبار المحور الصادي على إظهار المنحنى
            chart_data1 = pd.DataFrame({
                'Absorbance (a.u.)': absorbance
            }, index=np.round(wavelength, 1))
            st.area_chart(chart_data1, color='#FF5722')
            st.caption(f"ℹ️ طيف الامتصاصية الفعلي مقاساً بدقة من {int(wavelength.min())} نانومتر إلى {int(wavelength.max())} نانومتر.")
            
        with plot_col2:
            st.subheader("📈 مخطط تاوك التفاعلي (Tauc Plot Method)")
            y_label = 'Tauc Value (Alpha*hnu)^n'
            chart_data2 = pd.DataFrame({
                y_label: tauc_y
            }, index=np.round(photon_energy, 2))
            st.area_chart(chart_data2, color='#4CAF50')
            st.caption(f"ℹ️ المنحنى البياني المتقاطع مع محور طاقة الفوتونات (eV) لتحديد قيمة الفجوة تلقائياً عند {measured_bg} eV.")
            
        # جدول استعراض مراجع الأجهزة المقارن في أسفل الشاشة
        st.write("### 📋 جدول المراجع القياسية لفجوات الطاقة واللامدا ماكس (UV-Vis Reference Database)")
        rows = [{"المادة النانوية القياسية": k, "فجوة الطاقة المرجعية (eV)": v["eg"], "Lambda Max المرجعية (nm)": v["lambda_max"]} for k, v in REFERENCE_UV_DATA.items()]
        st.dataframe(pd.DataFrame(rows), use_container_width=True)
            
    except Exception as e:
        st.error(f"""
        ### ⚠️ تنبيه من بنية ملف جهاز الـ UV-Vis
        
        عذراً دكتور، تعذر استخراج الطيف. يرجى التأكد من أن الملف المرفوع هو ملف البيانات الرقمية الخام المستخرجة مباشرة من جهاز قياس الامتصاصية.
        
        ---
        🔍 **تفاصيل المشكلة التقنية المعالجة:** `{str(e)}`
        """)
else:
    st.info("بانتظار رفع ملف إكسل لجهاز الـ UV-Vis لرسم منحنى الامتصاص واستخراج مخطط تاوك وفجوة الطاقة فوراً.")

# ---------------------------------------------------------
# تذييل الصفحة المعتمد والثابت للدكتور مصطفى المسلماوي
# ---------------------------------------------------------
st.markdown("<br><br><hr>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #888888; font-size: 16px; font-weight: bold;'> تم تطويره بواسطة دكتور مصطفى المسلماوي</p>", unsafe_allow_html=True)
