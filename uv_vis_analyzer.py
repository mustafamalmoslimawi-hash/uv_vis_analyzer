import streamlit as st
import pandas as pd
import numpy as np
import io

# إعدادات الواجهة المستقلة والذكية لموقع الـ UV-Vis
st.set_page_config(page_title="UV-Vis & Tauc Plot Analyzer", layout="wide")

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

# شريط التحكم الجانبي للمعاملات الفيزيائية
st.sidebar.header("⚙️ إعدادات الحساب العلمي")
transition_type = st.sidebar.selectbox(
    "اختر نوع الانتقال الإلكتروني (Transition Type):",
    ["Direct Transition (n=1/2)", "Indirect Transition (n=2)"]
)

exponent = 2.0 if "Direct" in transition_type else 0.5

# مركز رفع الملفات المعملية
st.header("📥 رفع البيانات المعملية طيف الامتصاص")
uploaded_file = st.file_uploader("الرجاء رفع ملف جهاز UV-Vis بصيغة إكسل (Wavelength vs Absorbance):", type=["xlsx", "xls"])

if uploaded_file is not None:
    try:
        file_bytes = uploaded_file.read()
        try:
            df = pd.read_excel(io.BytesIO(file_bytes))
        except Exception:
            try:
                df = pd.read_excel(io.BytesIO(file_bytes), engine='openpyxl')
            except Exception:
                df = pd.read_excel(io.BytesIO(file_bytes), engine='xlrd')
            
        # تنظيف وفلترة الصفوف النصية الأولى (الترويسات المتقدمة للأجهزة)
        for i in range(min(len(df), 40)):
            v1 = pd.to_numeric(df.iloc[i:, 0], errors='coerce')
            v2 = pd.to_numeric(df.iloc[i:, 1], errors='coerce')
            if v1.notna().sum() > 5 and v2.notna().sum() > 5:
                df = df.iloc[i:].reset_index(drop=True)
                break

        # استخلاص المصفوفات الرقمية النقية
        col1 = pd.to_numeric(df.iloc[:, 0], errors='coerce').values
        col2 = pd.to_numeric(df.iloc[:, 1], errors='coerce').values
        
        # استبعاد الخلايا الفارغة تماماً أو القيم اللانهائية
        mask = ~np.isnan(col1) & ~np.isnan(col2) & ~np.isinf(col1) & ~np.isinf(col2)
        col1 = col1[mask]
        col2 = col2[mask]
        
        if len(col1) == 0:
            raise ValueError("الملف المرفوع لا يحتوي على قراءات رقمية متناسقة.")
            
        # خوارزمية التمييز الذكي للمحاور بناءً على متوسط القيم المرفوعة
        if np.nanmean(col2) > np.nanmean(col1):
            wavelength = col2
            absorbance = col1
        else:
            wavelength = col1
            absorbance = col2

        # إجبار البيانات على الترتيب التصاعدي الصارم لضمان دقة فهرسة المحور السيني للرسم
        sort_idx = np.argsort(wavelength)
        wavelength = wavelength[sort_idx]
        absorbance = absorbance[sort_idx]

        # 🎯 تعديل دكتور مصطفى: التركيز الصارم على النطاق المطلوب من 200 إلى 800 نانومتر بالضبط
        real_mask = (wavelength >= 200) & (wavelength <= 800) & (absorbance >= -0.5) & (absorbance <= 10.0)
        wavelength = wavelength[real_mask]
        absorbance = absorbance[real_mask]

        if len(wavelength) == 0:
            raise ValueError("الملف المرفوع لا يحتوي على قراءات تقع في النطاق المحدد (200 - 800 nm).")

        # الحسابات الفيزيائية لمخطط تاوك وفجوة الحزمة
        photon_energy = 1240.0 / wavelength
        tauc_y = (absorbance * photon_energy) ** exponent
        
        # اشتقاق فجوة الحزمة البصرية تلقائياً عبر المشتقة الأولى للامتصاصية
        diff_abs = np.diff(absorbance) / np.diff(wavelength)
        edge_idx = np.argmin(diff_abs) if len(diff_abs) > 0 else 0
        measured_bg = round(1240.0 / wavelength[edge_idx], 2)
        measured_lambda = int(round(wavelength[edge_idx]))
        
        # عرض واجهة النتائج والتحليل التشخيصي المباشر
        st.success("✅ تم الفحص الرياضي وتعديل النطاق الطيفي بنجاح!")
        
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
        
        # توليد الرسوم الخطية التفاعلية النقية المستقرة آلياً ومباشرة جنباً إلى جنب
        plot_col1, plot_col2 = st.columns(2)
        
        with plot_col1:
            st.subheader("📊 طيف الامتصاصية التفاعلي (Absorbance Spectrum)")
            chart_data1 = pd.DataFrame({
                'Wavelength': wavelength,
                'Absorbance': absorbance
            })
            # رسم خطي مقيد بدقة بين 200 و 800 نانومتر
            st.line_chart(chart_data1.set_index('Wavelength'), color='#FF5722')
            st.caption(f"ℹ️ طيف الامتصاصية الفعلي مقاساً بدقة من {int(wavelength.min())} nm إلى {int(wavelength.max())} nm.")
            
        with plot_col2:
            st.subheader("📈 مخطط تاوك المسترجَع (Tauc Plot Method)")
            chart_data2 = pd.DataFrame({
                'Photon Energy': photon_energy,
                'Tauc Value': tauc_y
            })
            st.line_chart(chart_data2.set_index('Photon Energy'), color='#4CAF50')
            st.caption(f"ℹ️ المنحنى البياني المتقاطع مع محور طاقة الفوتونات (eV) لتحديد قيمة الفجوة تلقائياً عند {measured_bg} eV.")
            
        # جدول استعراض مراجع الأجهزة المقارن في أسفل الشاشة
        st.write("---")
        st.write("### 📋 جدول المراجع القياسية لفجوات الطاقة واللامدا ماكس (UV-Vis Reference Database)")
        rows = [{"المادة النانوية القياسية": k, "فجوة الطاقة المرجعية (eV)": v["eg"], "Lambda Max المرجعية (nm)": v["lambda_max"]} for k, v in REFERENCE_UV_DATA.items()]
        st.dataframe(pd.DataFrame(rows), use_container_width=True)
            
    except Exception as e:
        st.error(f"""
        ### ⚠️ تنبيه من بنية ملف جهاز الـ UV-Vis
        عذراً دكتور، تعذر استخراج الطيف. يرجى التأكد من مطابقة خلايا البيانات.
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
