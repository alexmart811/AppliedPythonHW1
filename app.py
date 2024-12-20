import streamlit as st
import pandas as pd
from utils import general_temp_city, main, fetch_data, get_curr_season
import time
import asyncio
import requests
import plotly.graph_objs as go
from datetime import datetime

# Настройка страницы
st.set_page_config(page_title="Анализ температуры по городам", layout="wide")

# Заголовок приложения
st.title("🌤️ Анализ температуры по городам")

# Боковая панель для загрузки файла и ввода API ключа
st.sidebar.header("Настройки")
uploaded_file = st.sidebar.file_uploader("Выберите CSV-файл", type=["csv"])
API_key = st.sidebar.text_input("Введите API ключ от OpenWeatherMap")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    cities = df['city'].unique()

    # Синхронный запрос
    start = time.time()
    for city in cities:
        general_temp_city(df, city)
    end = time.time()
    st.success(f'Время выполнения синхронного запроса составило {end - start:.4f} сек')

    # Многопоточный запрос
    start = time.time()
    result = asyncio.run(main(df, cities))
    end = time.time()
    st.success(f'Время выполнения многопоточного запроса составило {end - start:.4f} сек')

    # Время выполнения обоих запросов особо не отличается
    # Думаю, на бОльшем объеме данных результат был бы заметнее

    option_city = st.selectbox("Выберите город", cities, index=None, placeholder="Выбор города...")

    if st.sidebar.button("Получить данные"):
        if option_city and API_key:
            # Синхронный запрос к API
            response = requests.get(f"https://api.openweathermap.org/data/2.5/weather?q={option_city}&appid={API_key}")

            # Асинхронный запрос к API
            response = asyncio.run(fetch_data(f"https://api.openweathermap.org/data/2.5/weather?q={option_city}&appid={API_key}"))

            # Думаю, особой разницы между использованием асинхронного и синхронного
            # запросов нет, так как нет необходимости выполнять несколько запросов
            # одновременно. Мы лишь отправляем единственный запрос.

            if response['cod'] == 200:
                curr_temp = float(response['main']['temp']) - 273.15

                selected_result = list(filter(lambda x: x[0] == option_city, result))[0]
                selected_df = selected_result[1]

                # Визуализация данных
                st.subheader(f'Исторические данные города {option_city}')

                fig = go.Figure()
                fig.add_trace(go.Scatter(x=selected_df['timestamp'], 
                                          y=selected_df['temperature_win'], 
                                          mode='lines', 
                                          marker=dict(color='blue', size=5), 
                                          name='Температура'))

                outliers = selected_df[selected_df['is_outlier'] == 1]
                fig.add_trace(go.Scatter(x=outliers['timestamp'], 
                                          y=outliers['temperature_win'], 
                                          mode='markers',
                                          marker=dict(color='red', size=10, symbol='x'), 
                                          name='Аномалии'))

                fig.add_trace(go.Scatter(x=selected_df['timestamp'], 
                                          y=selected_df['y_pred'], 
                                          mode='lines', 
                                          line=dict(color='green', width=3, dash='dash'), 
                                          name='Линия тренда'))

                fig.update_layout(xaxis_title='Дата',
                                  yaxis_title='Температура (°C)',
                                  xaxis=dict(rangeslider=dict(visible=True)),
                                  showlegend=True)
                st.plotly_chart(fig)

                # Анализ температур
                st.subheader("Анализ температур")
                
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.metric(label="Медианная температура", value=f"{round(selected_result[3], 2)} °C", delta=None)
                
                with col2:
                    st.metric(label="Минимальная температура", value=f"{round(selected_result[4], 2)} °C", delta=None)

                with col3:
                    st.metric(label="Максимальная температура", value=f"{round(selected_result[5], 2)} °C", delta=None)

                with col4:
                    st.metric(label="Текущая температура", value=f"{round(curr_temp, 2)} °C", delta=None)

                season = selected_result[2]
                season_name = get_curr_season(datetime.now().month)
                if season['median'][season_name] - 1.5 * season['std'][season_name] <= curr_temp <= season['median'][season_name] + 1.5 * season['std'][season_name]:
                    st.success('Температура не является аномальной')
                else:
                    st.error('Температура является аномальной')
            else:
                st.error(response['message'])

            # Визуализация распределения температур за сезон
            st.subheader(f"Распределение температур за сезон {season_name} для {option_city}")
            
            # Генерация данных для распределения температур
            temperatures = selected_df[selected_df['season'] == season_name]['temperature']
            
            # Построение гистограммы распределения температур
            fig_dist = go.Figure()
            
            fig_dist.add_trace(go.Histogram(
                x=temperatures,
                name='Температуры',
                marker_color='blue',
                opacity=0.7,
                histnorm='probability density',
                
            ))

            fig_dist.add_trace(go.Scatter(
                x=[season['median'][season_name] - 1.5 * season['std'][season_name], 
                   season['median'][season_name] - 1.5 * season['std'][season_name]],
                y=[0.1, 0],
                mode='lines',
                line=dict(color='red', width=3),
                name='Медиана - 1.5 * Стандартное отклонение'
            ))

            fig_dist.add_trace(go.Scatter(
                x=[season['median'][season_name] + 1.5 * season['std'][season_name], 
                   season['median'][season_name] + 1.5 * season['std'][season_name]],
                y=[0.1, 0],
                mode='lines',
                line=dict(color='red', width=3),
                name='Медиана + 1.5 * Стандартное отклонение'
            ))

            fig_dist.add_trace(go.Scatter(
                x=[season['median'][season_name]],
                y=[0],
                mode='markers',
                marker=dict(color='green', size=10),
                name='Медианная температура'
            ))

            fig_dist.add_trace(go.Scatter(
                x=[curr_temp],
                y=[0],
                mode='markers',
                marker=dict(color='orange', size=10),
                name='Текущая температура'
            ))

            fig_dist.update_layout(xaxis_title='Температура (°C)',
                                    yaxis_title='Плотность вероятности',
                                    showlegend=True)

            st.plotly_chart(fig_dist)
        else:
            st.warning("Пожалуйста, выберите город и введите API ключ.")
