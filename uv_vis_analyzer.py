import streamlit as st
import pandas as pd
import numpy as np
import io

# إعدادات الواجهة المستقلة والذكية لموقع الـ UV-Vis
st.set_page_config(page_title="UV-Vis Spectroscopic Analyzer", layout="wide")

st.markdown("<h1 style='text-align: center; color: #FF5722;'>UV-Vis Spectroscopic Analyzer</h1>", unsafe_allow_html=True)
st.markdown("<h4 style='text-align: center; color: #555;'>AUTOMATED OPTICAL CHARACTERIZATION & ABSORBANCE SPECTRUM PLOT</h4>", unsafe_allow_html=True)
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

        # 1. استخلاص المصفوفات الرقمية النقية
        col1 = pd.to_numeric(df.iloc[:, 0], errors='coerce').values
        col2 = pd.to_numeric(df.iloc[:, 1], errors='coerce').values
        
        # استبعاد الخلايا الفارغة تماماً
        mask = ~np.isnan(col1) & ~np.isnan(col2) & ~np.isinf(col1) & ~np.isinf(col2)
        col1 = col1[mask]
        col2 = col2[mask]
        
        if len(col1) == 0:
            raise ValueError("الملف المرفوع لا يحتوي على قراءات رقمية متناسقة.")
            
        # 2. خوارزمية التمييز الذكي للمحاور (تحديد عمود الطول الموجي مقابل عمود الامتصاصية)
        if np.nanmean(col2) > np.nanmean(col1):
            wavelength = col2
            absorbance = col1
        else:
            wavelength = col1
            absorbance = col2

        # الترتيب الهيكلي التصاعدي الدقيق لمنع التشابك الخطي للمنحنى
        sort_idx = np.argsort(wavelength)
        wavelength = wavelength[sort_idx]
        absorbance = absorbance[sort_idx]

        # 3. التركيز الصارم على النطاق الحقيقي الصافي للعينات (عزل التشتت الصفري الميت للملف)
        real_mask = (wavelength >= 290) & (wavelength <= 900) & (absorbance >= -0.1) & (absorbance <= 8.0)
        wavelength = wavelength[real_mask]
        absorbance = absorbance[real_mask]

        if len(wavelength) == 0:
            raise ValueError("النطاق الرقمي بعد الفلترة الصافية فارغ تماماً.")

        # الحسابات الفيزيائية لحافة الامتصاص وفجوة الحزمة التلقائية
        diff_abs = np.diff(absorbance) / np.diff(wavelength)
        edge_idx = np.argmin(diff_abs) if len(diff_abs) > 0 else 0
        measured_bg = round(1240.0 / wavelength[edge_idx], 2)
        measured_lambda = int(round(wavelength[edge_idx]))
        
        # عرض واجهة النتائج والتحليل التشخيصي المباشر
        st.success("✅ تم الفحص الرياضي الشامل ورسم المنحنى بنجاح!")
        
        res_col1, res_col2 = st.columns(2)
        with res_col1:
            st.metric(label="🎯 حافة الامتصاص المحسوبة (Absorption Edge):", value=f"{measured_lambda} nm")
            st.metric(label="💡 فجوة الطاقة البصرية التقريبية (Estimated Eg):", value=f"{measured_bg} eV")
            
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
        
        # 4. رسم منحنى طيف الامتصاصية فقط ممتداً على كامل عرض الشاشة (سينات وصادات)
        st.subheader("📊 طيف الامتصاصية التفاعلي (Absorbance Spectrum)")
        
        # بناء جدول البيانات بربط الامتصاصية مباشرة مع فهرس الأطوال الموجية المعملية
        chart_data = pd.DataFrame({
            'Absorbance (a.u.)': absorbance
        }, index=np.round(wavelength, 1))
        
        # رسم خطي صافي نقي ومحمي عبر دالة Streamlit الأساسية المستقرة
        st.line_chart(chart_data, color='#FF5722')
        
        st.caption(f"ℹ️ المحور الأفقي (السينات): الطول الموجي Wavelength (nm) | المحور الشاقولي (الصادات): الامتصاصية Absorbance (a.u.) مقاساً بدقة من {int(wavelength.min())} nm إلى {int(wavelength.max())} nm.")
        st.write("---")
            
        # جدول استعراض مراجع الأجهزة المقارن في أسفل الشاشة
        st.write("### 📋 جدول المراجع القياسية لفجوات الطاقة واللامدا ماكس (UV-Vis Reference Database)")
        rows = [{"المادة النانوية القياسية": k, "فجوة الطاقة المرجعية (eV)": v["eg"], "Lambda Max المرجعية (nm)": v["lambda_max"]} for k, v in REFERENCE_UV_DATA.items()]
        st.dataframe(pd.DataFrame(rows), use_container_width=True)
            
    except Exception as e:
        st.error(f"""
        ### ⚠️ تنبيه من بنية ملف جهاز الـ UV-Vis
        عذراً دكتور، تعذر استخراج الطيف. يرجى التأكد من مطابقة خلايا البيانات الرقمية داخل ملف الإكسل.
        ---
        🔍 **تفاصيل المشكلة التقنية المعالجة:** `{str(e)}`
        """)
else:
    st.info("بانتظار رفع ملف إكسل لجهاز الـ UV-Vis لرسم منحنى طيف الامتصاص فوراً.")

# ---------------------------------------------------------
# تذييل الصفحة المعتمد والثابت للدكتور مصطفى المسلماوي
# ---------------------------------------------------------
st.markdown("<br><br><hr>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #888888; font-size: 16px; font-weight: bold;'> تم تطويره بواسطة دكتور مصطفى المسلماوي</p>", unsafe_allow_html=True)
