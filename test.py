import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import sqlite3
import os

# Словарь диапазонов для контроля
component_ranges = {
    'CH4': (40, 99.97),
    'C2H6': (0.001, 15),
    'C3H8': (0.001, 6),
    'iC4H10': (0.001, 4),
    'nC4H10': (0.001, 4),
    'neoC5H12': (0.001, 0.05),
    'iC5H12': (0.001, 2),
    'nC5H12': (0.001, 2),
    'C6': (0.001, 1),
    'C6H6': (0.001, 0.05),
    'C7': (0.001, 0.05),
    'C7H8': (0.001, 0.05),
    'C8': (0.001, 0.05),
    'H2': (0.001, 0.5),
    'He': (0.001, 0.5),
    'O2': (0.005, 2),
    'N2': (0.005, 15),
    'CO2': (0.005, 10)
}

# --- Путь к базе данных ---
DB_PATH = r"D:\NG\passport.db"

# --- Проверка и подключение к базе данных ---
def load_passport_values():
    if not os.path.exists(DB_PATH):
        st.warning(f"⚠️ Файл базы данных не найден: {DB_PATH}")
        st.info("Создайте базу с помощью DB Browser for SQLite и таблицей `passport_values`.")
        return {}
    try:
        conn = sqlite3.connect(DB_PATH)
        query = "SELECT component, value FROM passport_values"
        df = pd.read_sql(query, conn)
        conn.close()
        return df.set_index("component")["value"].to_dict()
    except Exception as e:
        st.error(f"❌ Ошибка чтения базы данных: {e}")
        return {}

# --- Стили ---
st.set_page_config(layout="wide", page_title="Мониторинг газа")

st.markdown("""
<style>
    .big-title {
        font-size: 32px;
        font-weight: 600;
        color: #1f77b4;
        margin-bottom: 20px;
    }
    .small-caption {
        font-size: 14px;
        color: #666;
        text-align: center;
        margin-top: 10px;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="big-title">📊 Мониторинг состава природного газа</div>', unsafe_allow_html=True)

# --- Загрузка данных ---
@st.cache_data
def load_data():
    df = pd.read_csv(r"D:\NG\output_clean.csv")
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    df = df.set_index('date')
    return df

df = load_data()

# --- Компоненты ---
components = [
    'CH4','C2H6','C3H8','iC4H10','nC4H10','neoC5H12',
    'iC5H12','nC5H12','C6','C6H6','C7','C7H8','C8',
    'H2','He','O2','N2','CO2'
]

# --- Допуски ---
def get_tolerance(xi):
    if pd.isna(xi):
        return None, None
    if 0.0010 <= xi <= 0.010:
        return 0.5 * xi, 3 * xi
    elif 0.010 < xi <= 1.0:
        return 0.5 * xi, 2 * xi
    elif 1.0 < xi <= 15:
        return 0.5 * xi, 1.5 * xi
    elif 40 <= xi <= 75:
        return 0.8 * xi, 1.2 * xi
    elif 75 < xi <= 90:
        return 0.9 * xi, 1.1 * xi
    elif xi > 90:
        return 0.95 * xi, 1.05 * xi
    else:
        return None, None


def check_component(xi, x_pass, component):
    min_val, max_val = component_ranges.get(component, (None, None))

    if min_val is None or max_val is None:
        return None, None, "НН"

    lower, upper = get_tolerance(xi)

    if pd.isna(x_pass) or x_pass == 0:
        return lower, upper, "НН"

    if lower is None:
        return lower, upper, "НН"

    if min_val <= xi <= max_val:
        return lower, upper, (lower <= x_pass <= upper)
    else:
        return lower, upper, "НН"

# --- Форматирование ---
def format_value(x):
    if pd.isna(x):
        return "-"
    if abs(x) >= 1:
        return f"{x:.3f}"
    elif abs(x) >= 0.01:
        return f"{x:.4f}"
    else:
        return f"{x:.6f}"

# --- УПРАВЛЕНИЕ: НАЗВАНИЯ С ИКОНКАМИ ПОДСКАЗОК СПРАВА ---
col1, col2, col3 = st.columns(3, gap="medium")

# --- Компонент ---
with col1:
    st.markdown(
        '''
        <div style="font-weight: 500; font-size: 14px; margin-bottom: 6px; display: flex; align-items: center; gap: 6px;">
            Компонент
            <div style="font-size: 12px; color: #666;" title="Выберите компонент для анализа.">
                ℹ️
            </div>
        </div>
        ''',
        unsafe_allow_html=True
    )
    component = st.selectbox(
        "Компонент",
        components,
        label_visibility="collapsed",
        key="component_select"
    )

# --- Фильтрация шума ---
with col2:
    st.markdown(
        '''
        <div style="font-weight: 500; font-size: 14px; margin-bottom: 6px; display: flex; align-items: center; gap: 6px;">
            Фильтрация шума
            <div style="font-size: 12px; color: #666;" title="Сглаживает шум. Большее окно — чище тренд, но медленнее реагирует. 💡 Используйте для тренда, а не для деталей.">
                ℹ️
            </div>
        </div>
        ''',
        unsafe_allow_html=True
    )
    window = st.selectbox(
        "Скользящее среднее",
        options=[1, 3, 7, 14, 30],
        format_func=lambda x: "Без фильтра" if x == 1 else f"{x} дн",
        label_visibility="collapsed",
        key="window_select"
    )

# --- Период ---
with col3:
    st.markdown(
        '''
        <div style="font-weight: 500; font-size: 14px; margin-bottom: 6px; display: flex; align-items: center; gap: 6px;">
            Период
            <div style="font-size: 12px; color: #666;" title="Выберите диапазон дат. График и статистика будут пересчитаны.">
                ℹ️
            </div>
        </div>
        ''',
        unsafe_allow_html=True
    )
    date_range = st.date_input(
        "Период",
        value=(df.index.min().date(), df.index.max().date()),
        label_visibility="collapsed",
        key="date_input"
    )

# --- Загрузка паспортных значений из БД ---
passport_values = load_passport_values()

# --- Отображение текущего паспортного значения ---
x_pass = passport_values.get(component, 0.0)
if x_pass > 0:
    st.markdown(f"**📌 Паспортное значение для `{component}`:** `{format_value(x_pass)}` % мол.")
else:
    st.markdown(f"**⚠️ Нет паспортного значения для `{component}`**")
    st.info("Добавьте значение в таблицу `passport_values` в базе `D:\\NG\\passport.db`", icon="💡")

# --- Преобразование периода ---
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)
else:
    start_date = end_date = df.index.min()

if end_date < start_date:
    st.warning("Конечная дата не может быть раньше начальной.")
    st.stop()

# --- Фильтрация по периоду ---
df_filtered = df.loc[start_date:end_date].copy()

if df_filtered.empty:
    st.warning("Нет данных в выбранном диапазоне")
    st.stop()

data_series = df_filtered[component].copy()

# --- Применение сглаживания ---
if window > 1:
    data_series = data_series.rolling(window).mean()

data_series = data_series.dropna()

# --- График ---
st.markdown("### 📈 Динамика компонента")
fig = go.Figure()
fig.add_trace(go.Scatter(
    x=data_series.index,
    y=data_series,
    mode='lines',
    line=dict(width=2, color='#1f77b4')
))
fig.update_layout(
    height=400,
    yaxis_title="% мол.",
    hovermode="x unified",
    showlegend=False,
    plot_bgcolor='white',
    xaxis=dict(
        showgrid=True,
        gridcolor='lightgray',
        title="Дата",
        rangeslider_visible=True,
        rangeslider=dict(bgcolor='lightgray', thickness=0.05),
        tickformat='%d.%m.%Y'
    ),
    yaxis=dict(showgrid=True, gridcolor='lightgray'),
    margin=dict(l=40, r=20, t=20, b=60)
)
st.plotly_chart(fig, use_container_width=True)

# --- Расчёт метрик ---
if data_series.empty:
    mean_val = min_val = max_val = start_val = end_val = 0.0
    delta_abs = delta_pct = 0.0
else:
    start_val = data_series.iloc[0]
    end_val = data_series.iloc[-1]
    delta_abs = end_val - start_val
    delta_pct = ((delta_abs / start_val) * 100) if start_val != 0 else (float('inf') if delta_abs > 0 else 0.0)
    mean_val = data_series.mean()
    min_val = data_series.min()
    max_val = data_series.max()

# --- Отображение метрик ---
st.markdown('<div class="big-title">📈 Статистика по выбранному периоду</div>', unsafe_allow_html=True)
col1, col2, col3, col4 = st.columns(4)
col1.metric("Среднее", format_value(mean_val), help="Среднее значение компонента в периоде")
col2.metric("Мин", format_value(min_val), help="Минимальное значение в периоде")
col3.metric("Макс", format_value(max_val), help="Максимальное значение в периоде")
delta_pct_str = "∞%" if delta_pct == float('inf') else f"{round(delta_pct, 2)}%"
col4.metric("Δ", format_value(delta_abs), delta_pct_str, help="Изменение от начала до конца периода (по сглаженным данным)")

# --- Проверка соответствия для текущего компонента ---
if not data_series.empty and x_pass > 0:
    xi_current = data_series.iloc[-1]
    lower, upper, status = check_component(xi_current, x_pass, component)  # добавили component
    st.markdown("### 🧪 Проверка соответствия (последнее значение)")
    c1, c2, c3 = st.columns(3)
    c1.metric("Факт (xi)", format_value(xi_current))
    c2.metric("Допуск", f"{format_value(lower)} — {format_value(upper)}" if lower is not None else "-")
    c3.metric("Статус", "OK" if status else "OUT" if status is False else "нет данных")

# ... остальной код выше

# --- Полная картина соответствия по всем компонентам ---
st.markdown("### 🏁 Полная картина соответствия стандарту")
st.caption("На основе последнего значения и данных из `passport.db`")

rows = []
for comp in components:
    if comp not in passport_values:
        continue
    x_pass_saved = passport_values[comp]
    if x_pass_saved == 0:
        continue
    if comp not in df_filtered:
        continue

    xi_last = df_filtered[comp].iloc[-1] if not df_filtered[comp].dropna().empty else None
    if pd.isna(xi_last):
        continue

    lower, upper, status = check_component(xi_last, x_pass_saved, comp)  # добавили comp

    rows.append({
        "Компонент": comp,
        "Факт": format_value(xi_last),
        "Паспорт": format_value(x_pass_saved),
        "Допуск": f"{format_value(lower)} — {format_value(upper)}" if lower is not None else "-",
        "Статус": "✅ OK" if status == True
        else "❌ OUT" if status == False
        else status
    })

# Создаем DataFrame и отображаем его только один раз
if rows:
    summary_df = pd.DataFrame(rows)
    st.dataframe(
        summary_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Статус": st.column_config.TextColumn(
                "Статус",
                help="✅ Соответствует / ❌ Не соответствует / НН - Ненормируемый"
            )
        }
    )
else:
    st.info("Нет данных для отображения")


# Исправленная функция check_component
def check_component(xi, x_pass, component):
    # Получаем допустимый диапазон для компонента
    min_val, max_val = component_ranges.get(component, (None, None))

    # Проверяем, есть ли данные для компонента
    if min_val is None or max_val is None:
        return None, None, "НН"

    # Получаем допуск
    lower, upper = get_tolerance(xi)

    # Проверяем, попадает ли значение в диапазон
    if pd.isna(x_pass) or x_pass == 0:
        return lower, upper, "НН"

    # Проверяем соответствие
    if lower is None:
        return lower, upper, "НН"

    if min_val <= xi <= max_val:
        return lower, upper, (lower <= x_pass <= upper)
    else:
        return lower, upper, "НН"

