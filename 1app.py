# Streamlit AI Analyzer — исправленная безопасная версия

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader

st.set_page_config(page_title="AI Анализ СОР/СОЧ", layout="wide")
st.title("📊 AI-Анализатор СОР/СОЧ и Тем Ошибок")

st.write("Загрузите Excel-файл из Кунделика. Приложение автоматически найдет строки СОР/СОЧ, построит цветные диаграммы и сформирует PDF-отчёт.")

uploaded = st.file_uploader("Загрузите файл Excel из Кунделика", type=["xlsx"])

if uploaded:
    df_raw = pd.read_excel(uploaded, header=None)

    # --- 1. Поиск строк СОР/СОЧ ---
    mask = df_raw[0].astype(str).str.contains("СОР|СОЧ", case=False, na=False)
    df = df_raw[mask].copy().reset_index(drop=True)

    # --- 2. Безопасный выбор нужных колонок ---
    desired_cols = [c for c in [0,1,2,7,8] if c in df.columns]
    df = df[desired_cols]

    column_names = ["Работа","Выполнили","Не выполнили","% качества","% успеваемости"]
    df.columns = column_names[:len(df.columns)]

    # --- 3. Безопасное преобразование числовых колонок ---
    for col in ["Выполнили","Не выполнили","% качества","% успеваемости"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace('%','').str.strip()
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    st.subheader("📄 Обработанные данные")
    st.dataframe(df)

    # --- 4. Диаграмма качества ---
    st.subheader("📈 Процент качества (цветная)")

    def color_quality(x):
        if x >= 85:
            return '#2ca02c'
        elif x >= 70:
            return '#ffcc00'
        else:
            return '#d62728'

    if '% качества' in df.columns:
        colors_q = [color_quality(x) for x in df['% качества']]
        fig_q, ax_q = plt.subplots(figsize=(6,4))
        bars = ax_q.bar(df['Работа'], df['% качества'], color=colors_q)
        ax_q.set_ylabel('% качества')
        ax_q.set_ylim(0,100)
        for bar, val in zip(bars, df['% качества']):
            ax_q.text(bar.get_x()+bar.get_width()/2, val+1, f"{val:.0f}%", ha='center')
        st.pyplot(fig_q)

    # --- 5. Диаграмма успеваемости ---
    st.subheader("📈 Процент успеваемости (цветная)")

    def color_pass(x):
        if x >= 90:
            return '#2ca02c'
        elif x >= 70:
            return '#ff9900'
        else:
            return '#d62728'

    if '% успеваемости' in df.columns:
        colors_p = [color_pass(x) for x in df['% успеваемости']]
        fig_p, ax_p = plt.subplots(figsize=(6,4))
        bars2 = ax_p.bar(df['Работа'], df['% успеваемости'], color=colors_p)
        ax_p.set_ylabel('% успеваемости')
        ax_p.set_ylim(0,100)
        for bar, val in zip(bars2, df['% успеваемости']):
            ax_p.text(bar.get_x()+bar.get_width()/2, val+1, f"{val:.0f}%", ha='center')
        st.pyplot(fig_p)

    # --- 6. AI-диагностика ---
    st.subheader("🔍 AI-диагностика проблемных тем")
    analysis = []
    for _, row in df.iterrows():
        work = str(row['Работа'])
        q = float(row['% качества']) if '% качества' in df.columns else 0
        if q < 70:
            analysis.append(f"❗ {work}: низкое качество ({q:.0f}%). Требуется повторение.")
        elif q < 85:
            analysis.append(f"⚠️ {work}: средние результаты ({q:.0f}%). Рекомендуется дополнительная работа.")
        else:
            analysis.append(f"✅ {work}: высокий уровень ({q:.0f}%).")

    st.write("<br>".join(analysis), unsafe_allow_html=True)

    # --- 7. Ученики по уровням ---
    students_by_level = {}
    for i, row in df_raw.iterrows():
        row_text = ' '.join([str(x) for x in row.astype(str).values])
        if 'Низкий' in row_text or 'Средний' in row_text or 'Высокий' in row_text:
            header_row = row
            for col_idx, val in header_row.items():
                if isinstance(val, str) and ('Низкий' in val or 'Средний' in val or 'Высокий' in val):
                    key = val.strip()
                    names = []
                    for c in range(col_idx+1, col_idx+4):
                        if c in header_row.index:
                            names.append(str(header_row[c]))
                    names_text = ', '.join([x for x in names if x and x not in ['nan','None']])
                    students_by_level[key] = names_text
            break

    if students_by_level:
        st.subheader('👥 Ученики по уровням')
        for k,v in students_by_level.items():
            st.write(f"**{k}**: {v}")

    # --- 8. Генерация PDF ---
    st.subheader('📥 Скачать PDF-отчёт')

    def create_pdf(df_table, fig_quality, fig_pass, analysis_lines, students_dict):
        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4

        # Заголовок
        p.setFont('Helvetica-Bold', 14)
        p.drawString(40, height-40, 'Анализ результатов СОР и СОЧ')

        # Таблица
        p.setFont('Helvetica', 10)
        y = height - 70
        for col_name in df_table.columns:
            p.drawString(40 + df_table.columns.get_loc(col_name)*80, y, col_name)
        y -= 15
        for _, r in df_table.iterrows():
            for col_name in df_table.columns:
                val = r[col_name]
                display_val = f"{int(val)}%" if '%' in col_name else str(int(val))
                p.drawString(40 + df_table.columns.get_loc(col_name)*80, y, display_val)
            y -= 15
            if y < 150:
                p.showPage()
                y = height - 40

        # Графики
        img_buf1 = BytesIO()
        fig_quality.savefig(img_buf1, format='png', bbox_inches='tight')
        img_buf1.seek(0)
        img1 = ImageReader(img_buf1)

        img_buf2 = BytesIO()
        fig_pass.savefig(img_buf2, format='png', bbox_inches='tight')
        img_buf2.seek(0)
        img2 = ImageReader(img_buf2)

        p.showPage()
        p.drawImage(img1, 40, height/2, width=500, preserveAspectRatio=True, mask='auto')
        p.drawImage(img2, 40, 40, width=500, preserveAspectRatio=True, mask='auto')

        # Анализ
        p.showPage()
        p.setFont('Helvetica-Bold', 12)
        p.drawString(40, height-40, 'AI-диагностика')
        p.setFont('Helvetica', 10)
        y = height - 70
        for line in analysis_lines:
            p.drawString(40, y, line)
            y -= 15
            if y < 40:
                p.showPage()
                y = height - 40

        # Ученики
        if students_dict:
            p.showPage()
            p.setFont('Helvetica-Bold', 12)
            p.drawString(40, height-40, 'Ученики по уровням')
            p.setFont('Helvetica', 10)
            y = height - 70
            for k,v in students_dict.items():
                p.drawString(40, y, f"{k}: {v}")
                y -= 15
                if y < 40:
                    p.showPage()
                    y = height - 40

        p.save()
        buffer.seek(0)
        return buffer.getvalue()

    if st.button('Сформировать и скачать PDF-отчёт'):
        pdf_bytes = create_pdf(df, fig_q, fig_p, analysis, students_by_level)
        st.download_button('Скачать PDF', data=pdf_bytes, file_name='report_SOR_SOCH.pdf', mime='application/pdf')

    st.info("Готово! PDF формируется кнопкой выше.")
