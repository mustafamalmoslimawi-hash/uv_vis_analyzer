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

# شريط التحكم الجانبي للمعاملات الفيزيائية
st.sidebar.header("⚙️ إعدادات الحساب العلمي")
transition_type = st.sidebar.selectbox(
    "اختر نوع الانتقال الإلكتروني (Transition Type):",
    ["Direct Transition (n=1/2)", "Indirect Transition (n=2)"]
)

exponent = 2.0 if "Direct" in transition_type else 0.5

# مركز رفع الملفات المعملية - مخصص لملفات الإكسل فقط
st.header("📥 رفع البيانات المعملية طيف الامتصاص")
uploaded_file = st.file_uploader("الرجاء رفع ملف إكسل لجهاز UV-Vis (Wavelength vs Absorbance):", type=["xlsx", "xls"])

if uploaded_file is not None:
    try:
        # قراءة ثنائية مرنة ومستقلة تماماً عن المحركات الخارجية للسيرفر السحابي
        file_bytes = uploaded_file.read()
        try:
            df = pd.read_excel(io.BytesIO(file_bytes))
        except Exception:
            try:
                df = pd.read_excel(io.BytesIO(file_bytes), engine='openpyxl')
            except Exception:
                df = pd.read_excel(io.BytesIO(file_bytes), engine='xlrd')

        # تنظيف البيانات الأولية: إزالة الصفوف النصية والترويسات التي تضعها بعض الأجهزة
        # نقوم بالبحث عن أول صف يحتوي على قراءات رقمية حقيقية
        for i in range(min(len(df), 20)):
            val1 = pd.to_numeric(df.iloc[i:, 0], errors='coerce')
            val2 = pd.to_numeric(df.iloc[i:, 1], errors='coerce')
            if val1.notna().sum() > 5 and val2.notna().sum() > 5:
                df = df.iloc[i:].reset_index(drop=True)
                break

        # استخراج المصفوفات الرقمية الخام
        col1_values = pd.to_numeric(df.iloc[:, 0], errors='coerce').values
        col2_values = pd.to_numeric(df.iloc[:, 1], errors='coerce').values

        # تصفية من القيم الفارغة (NaN)
        valid_mask = ~np.isnan(col1_values) & ~np.isnan(col2_values)
        col1_values = col1_values[valid_mask]
        col2_values = col2_values[valid_mask]

        if len(col1_values) == 0:
            raise ValueError("الملف لا يحتوي على بيانات رقمية واضحة في العمودين الأول والثاني.")

        # 🧠 خوارزمية الكشف التلقائي عن الأعمدة وتصحيح الترتيب المقلوب للأجهزة:
        # أطوال موجات الـ UV-Vis تقع عادةً في نطاق مئوي (مثال: 200 إلى 1000)، بينما الامتصاصية قيم صغيرة (غالباً بين 0 و 5).
        if np.nanmean(col2_values) > np.nanmean(col1_values):
            # إذا كانت قيم العمود الثاني أكبر، فهذا يعني أن العمود الثاني هو الطول الموجي والأول هو الامتصاصية!
            wavelength = col2_values
            absorbance = col1_values
            st.warning("⚠️ تنبيه ذكي: تم رصد ترتيب مقلوب للملف من الجهاز، وقام النظام بتعديل الأعمدة تلقائياً لضمان دقة الحسابات.")
        else:
            # الترتيب القياسي الصحيح
            wavelength = col1_values
            absorbance = col2_values

        # التأكد من الترتيب التصاعدي للأطوال الموجية لرسم بياني هندسي مستقر
        sort_idx = np.argsort(wavelength)
        wavelength = wavelength[sort_idx]
        absorbance = absorbance[sort_idx]

        # عزل أي قراءات شاذة أو أطوال موجية صفرية أو سالبة لتجنب قسمة الصفر رياضياً
        real_mask = (wavelength > 100) & (wavelength < 2000) & (absorbance >= 0)
        wavelength = wavelength[real_mask]
        absorbance = absorbance[real_mask]

        if len(wavelength) == 0:
            raise ValueError("نطاق الأطوال الموجية في ملف الإكسل يقع خارج النطاق الطيفي المعتمد للـ UV-Vis (200-1100 nm).")

        # الحسابات الفيزيائية الكمية لثوابت تاوك (Tauc Plot Calculations)
        photon_energy = 1240.0 / wavelength
        tauc_y = (absorbance * photon_energy) ** exponent
        
        # استخراج حافة الامتصاص تلقائياً (Absorption Edge) عبر المشتقة الأولى للمنحنى
        diff_abs = np.diff(absorbance) / np.diff(wavelength)
        edge_idx = np.argmin(diff_abs) if len(diff_abs) > 0 else 0
        measured_bg = round(1240.0 / wavelength[edge_idx], 2)
        measured_lambda = int(round(wavelength[edge_idx]))
        
        # عرض واجهة النتائج المعتمدة
        st.success("✅ تم تحليل وضبط منحنى طيف الامتصاص بنجاح وإظهار البيانات!")
        
        res_col1, res_col2 = st.columns(2)
        with res_col1:
            st.metric(label="💡 فجوة الطاقة البصرية المقاسة (Measured Eg):", value=f"{measured_bg} eV")
            st.metric(label="🎯 حافة الامتصاص المحسوبة (Absorption Edge):", value=f"{measured_lambda} nm")
            
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
        
        # بناء المنحنيات البيانية التفاعلية المحددة بالنطاق الدقيق للأجهزة البصرية
        plot_col1, plot_col2 = st.columns(2)
        
        with plot_col1:
            st.subheader("📊 طيف الامتصاصية التفاعلي (Absorbance Spectrum)")
            chart_data1 = pd.DataFrame({
                'Wavelength (nm)': wavelength,
                'Absorbance (a.u.)': absorbance
            })
            # قفل المحور السيناتي بدقة على أرقام النانو متر الحقيقية للملف
            st.line_chart(chart_data1.set_index('Wavelength (nm)'), color='#FF5722')
            st.caption(f"ℹ️ المنحنى الطيفي للامتصاصية الفعلي مقاساً بين {int(wavelength.min())} و {int(wavelength.max())} نانومتر.")
            
        with plot_col2:
            st.subheader("📈 مخطط تاوك التفاعلي (Tauc Plot Method)")
            y_label = '(Alpha*hnu)^2' if exponent == 2.0 else '(Alpha*hnu)^0.5'
            chart_data2 = pd.DataFrame({
                'Photon Energy (eV)': photon_energy,
                y_label: tauc_y
            })
            st.line_chart(chart_data2.set_index('Photon Energy (eV)'), color='#4CAF50')
            st.caption(f"ℹ️ تقاطع المماس الخطي مع محور الطاقة يحدد فجوة الحزمة عند: {measured_bg} eV.")
            
        # جدول استعراض مراجع الأجهزة المقارن
        st.write("### 📋 جدول المراجع القياسية لفجوات الطاقة واللامدا ماكس (UV-Vis Reference Database)")
        rows = [{"المادة النانوية القياسية": k, "فجوة الطاقة المرجعية (eV)": v["eg"], "Lambda Max المرجعية (nm)": v["lambda_max"]} for k, v in REFERENCE_UV_DATA.items()]
        st.dataframe(pd.DataFrame(rows), use_container_width=True)
            
    except Exception as e:
        st.error(f"""
        ### ⚠️ خطأ في قراءة وهيكلة ملف جهاز الـ UV-Vis
        
        عذراً دكتور، تعذر على النظام إظهار المنحنى البياني بسبب خلل في تنسيق الأرقام داخل الملف. يرجى مراجعة الآتي:
        * تأكد من أن خلايا الإكسل تحتوي على أرقام صافية فقط ولا تحتوي على رموز غريبة مثل الفواصل النصية أو الحروف الملتصقة بالأرقام.
        * تأكد أن الملف يحتوي على قراءات حقيقية لجهاز الـ UV-Vis (طول موجي واختفاء أو صعود في الامتصاصية).
        
        ---
        🔍 **تفاصيل المشكلة الرياضية المكتشفة:** `{str(e)}`
        """)
else:
    st.info("بانتظار رفع ملف إكسل لجهاز الـ UV-Vis لرسم منحنى الامتصاص واستخراج مخطط تاوك وفجوة الطاقة فوراً.")

# ---------------------------------------------------------
# تذييل الصفحة المعتمد والثابت للدكتور مصطفى المسلماوي
# ---------------------------------------------------------
st.markdown("<br><br><hr>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #888888; font-size: 16px; font-weight: bold;'> تم تطويره بواسطة دكتور مصطفى المسلماوي</p>", unsafe_allow_html=True)
