# Дашборд по продажам и прибыли дочерних компаний холдинга
# Данные: Financial Sample от Microsoft (учебный датасет)
# Запуск: streamlit run app.py

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Отчёт по дочерним компаниям", layout="wide")


# ---------- Загрузка и очистка данных ----------

# декоратор cache_data нужен, чтобы файл не читался заново при каждом клике
@st.cache_data
def load_data():
    df = pd.read_excel("data/Financial_Sample.xlsx")

    # в названиях колонок есть лишние пробелы (например " Sales"), убираю их
    df.columns = df.columns.str.strip()

    # переименовываю колонки на русский, так удобнее читать
    df = df.rename(columns={
        "Segment": "Сегмент",
        "Country": "Компания",
        "Product": "Продукт",
        "Discount Band": "Уровень скидки",
        "Units Sold": "Продано единиц",
        "Manufacturing Price": "Цена производства",
        "Sale Price": "Цена продажи",
        "Gross Sales": "Выручка до скидок",
        "Discounts": "Скидки",
        "Sales": "Выручка",
        "COGS": "Себестоимость",
        "Profit": "Прибыль",
        "Date": "Дата",
        "Month Number": "Месяц",
        "Year": "Год",
    })

    # колонка с названием месяца на английском не нужна, есть номер месяца
    df = df.drop(columns=["Month Name"])

    # каждая страна - это отдельная дочерняя компания холдинга
    df["Компания"] = df["Компания"].replace({
        "Canada": "Канада",
        "France": "Франция",
        "Germany": "Германия",
        "Mexico": "Мексика",
        "United States of America": "США",
    })

    df["Сегмент"] = df["Сегмент"].replace({
        "Government": "Госсектор",
        "Midmarket": "Средний бизнес",
        "Channel Partners": "Партнёры",
        "Enterprise": "Крупный бизнес",
        "Small Business": "Малый бизнес",
    })

    # пропуски в уровне скидки - это строки, где скидки вообще не было (Скидки = 0)
    df["Уровень скидки"] = df["Уровень скидки"].fillna("Без скидки")
    df["Уровень скидки"] = df["Уровень скидки"].replace({
        "Low": "Низкая", "Medium": "Средняя", "High": "Высокая",
    })

    # на всякий случай проверяю тип даты и убираю полные дубликаты
    df["Дата"] = pd.to_datetime(df["Дата"])
    df = df.drop_duplicates()

    return df


df = load_data()


# ---------- Фильтры в боковой панели ----------

st.sidebar.header("Фильтры")

years = sorted(df["Год"].unique())
selected_years = st.sidebar.multiselect("Год", years, default=years)

companies = sorted(df["Компания"].unique())
selected_companies = st.sidebar.multiselect("Дочерние компании", companies, default=companies)

segments = sorted(df["Сегмент"].unique())
selected_segments = st.sidebar.multiselect("Сегмент клиентов", segments, default=segments)

st.sidebar.caption("За 2013 год в данных есть только сентябрь - декабрь.")

# оставляю только те строки, которые подходят под фильтры
data = df[
    df["Год"].isin(selected_years)
    & df["Компания"].isin(selected_companies)
    & df["Сегмент"].isin(selected_segments)
]

if data.empty:
    st.warning("По выбранным фильтрам нет данных. Попробуйте выбрать что-то ещё.")
    st.stop()


# ---------- Заголовок и главные цифры ----------

st.title("Отчёт по продажам дочерних компаний")
st.write("Выручка, себестоимость и прибыль пяти дочерних компаний холдинга по месяцам.")

total_sales = data["Выручка"].sum()
total_profit = data["Прибыль"].sum()
margin = total_profit / total_sales * 100
units = data["Продано единиц"].sum()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Выручка", f"${total_sales / 1_000_000:.1f} млн")
col2.metric("Прибыль", f"${total_profit / 1_000_000:.1f} млн")
col3.metric("Маржа", f"{margin:.1f}%")
col4.metric("Продано единиц", f"{units:,.0f}".replace(",", " "))


tab1, tab2, tab3, tab4 = st.tabs(
    ["Компании", "Динамика по месяцам", "Продукты и сегменты", "Таблица"]
)


# ---------- Вкладка 1: сравнение дочерних компаний ----------

with tab1:
    # группирую по компании и считаю суммы
    by_company = data.groupby("Компания")[["Выручка", "Себестоимость", "Прибыль"]].sum()
    by_company["Маржа, %"] = by_company["Прибыль"] / by_company["Выручка"] * 100
    by_company = by_company.sort_values("Выручка", ascending=False).reset_index()

    left, right = st.columns(2)

    with left:
        st.subheader("Выручка и прибыль по компаниям")
        # melt переводит таблицу в длинный вид, чтобы нарисовать два столбика рядом
        chart_data = by_company.melt(
            id_vars="Компания", value_vars=["Выручка", "Прибыль"],
            var_name="Показатель", value_name="Сумма",
        )
        fig = px.bar(chart_data, x="Компания", y="Сумма", color="Показатель", barmode="group",
                     color_discrete_sequence=["#2a78d6", "#1baf7a"])
        fig.update_layout(yaxis_title="$", xaxis_title="")
        st.plotly_chart(fig, width="stretch")

    with right:
        st.subheader("Маржа по компаниям, %")
        fig = px.bar(by_company, x="Компания", y="Маржа, %", text_auto=".1f",
                     color_discrete_sequence=["#2a78d6"])
        fig.update_layout(xaxis_title="")
        st.plotly_chart(fig, width="stretch")

    st.subheader("Сводный отчёт по компаниям")
    st.dataframe(
        by_company.style.format({
            "Выручка": "${:,.0f}",
            "Себестоимость": "${:,.0f}",
            "Прибыль": "${:,.0f}",
            "Маржа, %": "{:.1f}%",
        }),
        width="stretch",
        hide_index=True,
    )

    best = by_company.iloc[0]["Компания"]
    best_margin = by_company.sort_values("Маржа, %", ascending=False).iloc[0]["Компания"]
    st.info(f"Больше всего выручки у компании **{best}**, самая высокая маржа у **{best_margin}**.")


# ---------- Вкладка 2: как менялись продажи по месяцам ----------

with tab2:
    st.subheader("Выручка по месяцам")

    # по умолчанию показываю общую выручку холдинга, а по галочке - отдельно по компаниям
    split = st.checkbox("Разбить по компаниям")
    if split:
        # группирую по дате (в данных это первое число месяца) и по компании
        by_month = data.groupby(["Дата", "Компания"])["Выручка"].sum().reset_index()
        fig = px.line(by_month, x="Дата", y="Выручка", color="Компания", markers=True)
    else:
        total_by_month = data.groupby("Дата")["Выручка"].sum().reset_index()
        fig = px.line(total_by_month, x="Дата", y="Выручка", markers=True)

    fig.update_layout(xaxis_title="", yaxis_title="Выручка, $")
    st.plotly_chart(fig, width="stretch")

    st.subheader("Прибыль по месяцам")
    profit_by_month = data.groupby("Дата")["Прибыль"].sum().reset_index()
    fig = px.bar(profit_by_month, x="Дата", y="Прибыль", color_discrete_sequence=["#1baf7a"])
    fig.update_layout(xaxis_title="", yaxis_title="Прибыль, $")
    st.plotly_chart(fig, width="stretch")


# ---------- Вкладка 3: продукты и сегменты клиентов ----------

with tab3:
    left, right = st.columns(2)

    with left:
        st.subheader("Прибыль по продуктам")
        by_product = data.groupby("Продукт")["Прибыль"].sum().sort_values().reset_index()
        fig = px.bar(by_product, x="Прибыль", y="Продукт", orientation="h",
                     color_discrete_sequence=["#2a78d6"])
        fig.update_layout(xaxis_title="Прибыль, $", yaxis_title="")
        st.plotly_chart(fig, width="stretch")

    with right:
        st.subheader("Доля выручки по сегментам")
        by_segment = data.groupby("Сегмент")["Выручка"].sum().reset_index()
        fig = px.pie(by_segment, names="Сегмент", values="Выручка", hole=0.4)
        st.plotly_chart(fig, width="stretch")

    st.subheader("Как скидки влияют на прибыль")
    by_discount = data.groupby("Уровень скидки")[["Скидки", "Прибыль"]].sum().reset_index()
    order = ["Без скидки", "Низкая", "Средняя", "Высокая"]
    fig = px.bar(by_discount, x="Уровень скидки", y=["Скидки", "Прибыль"], barmode="group",
                 category_orders={"Уровень скидки": order},
                 color_discrete_sequence=["#eb6834", "#1baf7a"])
    fig.update_layout(xaxis_title="", yaxis_title="$", legend_title="")
    st.plotly_chart(fig, width="stretch")


# Вкладка 4: сами данные 

with tab4:
    st.subheader("Данные после очистки")
    st.write(f"Строк: {len(data)}, колонок: {data.shape[1]}")
    st.dataframe(data, width="stretch", hide_index=True)

    csv = data.to_csv(index=False).encode("utf-8")
    st.download_button("Скачать в CSV", csv, "report.csv", "text/csv")
