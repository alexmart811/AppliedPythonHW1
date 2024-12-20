from sklearn.linear_model import LinearRegression
import pandas as pd
import asyncio
from concurrent.futures import ThreadPoolExecutor
import aiohttp

def general_temp_city(df, select_city, win_size=30):
    df_selected = df.query(f"city == '{select_city}'")
    df_selected['temperature_win'] = df_selected['temperature'].rolling(win_size).mean().dropna()
    df_selected = df_selected.dropna()

    median_df_win = df_selected['temperature_win'].median()
    std_df_win = df_selected['temperature_win'].std()

    is_outlier = lambda x: 0 if median_df_win - 2 * std_df_win <= x <= median_df_win + 2 * std_df_win else 1
    df_selected['is_outlier'] = df_selected['temperature_win'].apply(is_outlier)

    df_selected['timestamp'] = pd.to_datetime(df_selected['timestamp'])
    df_selected['timestamp_num'] = df_selected['timestamp'].map(pd.Timestamp.timestamp)
    lr = LinearRegression()
    lr.fit(df_selected[['timestamp_num']], df_selected['temperature'])
    df_selected['y_pred'] = lr.predict(df_selected[['timestamp_num']])
    
    dct_season = df_selected.groupby('season')['temperature'].agg(['median', 'std']).to_dict()
    median_temperature = df_selected['temperature'].median()
    std_temperature = df_selected['temperature'].std()
    min_temperature = df_selected['temperature'].min()
    max_temperature = df_selected['temperature'].max()

    return (select_city, df_selected, dct_season, 
            median_temperature, min_temperature, max_temperature)

async def run_cpu_task(executor, df, city):
    # Запускаем CPU-bound задачу в пуле потоков
    return await asyncio.get_running_loop().run_in_executor(executor, general_temp_city, df, city)

async def main(df, cities):
    # Создаем пул потоков с 4 потоками
    with ThreadPoolExecutor(max_workers=5) as executor:
        # Запускаем несколько задач параллельно
        tasks = [run_cpu_task(executor, df, city) for city in cities]

        # Ожидаем завершения всех задач
        return await asyncio.gather(*tasks)
    
async def fetch_data(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()
        
def get_curr_season(month):
    if 3 <= month <= 5:
        return 'spring'
    elif 6 <= month <= 8:
        return 'summer'
    elif 9 <= month <= 11:
        return 'autumn'
    else:
        return 'winter'