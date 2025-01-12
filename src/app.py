import streamlit as st
import requests
from bs4 import BeautifulSoup
import json
import pandas as pd
import time
from datetime import datetime

def log_message(container, message, level='info'):
    timestamp = datetime.now().strftime('%H:%M:%S')
    if level == 'info':
        container.info(f'[{timestamp}] {message}')
    elif level == 'error':
        container.error(f'[{timestamp}] {message}')
    elif level == 'success':
        container.success(f'[{timestamp}] {message}')

def parse_contract_block(block):
    contract = {}
    
    number = block.find('div', class_='registry-entry__header-mid__number')
    if number and number.find('a'):
        contract['number'] = number.find('a').text.strip()
        contract['url'] = 'https://zakupki.gov.ru' + number.find('a')['href']
    
    status = block.find('div', class_='registry-entry__header-mid__title')
    if status:
        contract['status'] = status.text.strip()
    
    customer = block.find('div', class_='registry-entry__body-href')
    if customer and customer.find('a'):
        contract['customer_name'] = customer.find('a').text.strip()
        contract['customer_url'] = 'https://zakupki.gov.ru' + customer.find('a')['href']
    
    contract_id = block.find('div', {'class': 'registry-entry__body-value'})
    if contract_id:
        contract['contract_identifier'] = contract_id.text.strip().replace('№', '').strip()
    
    price = block.find('div', class_='price-block__value')
    if price:
        contract['price'] = price.text.strip().replace('\xa0', ' ')
    
    dates = block.find_all('div', class_='data-block__value')
    if dates and len(dates) >= 3:
        contract['conclusion_date'] = dates[0].text.strip()
        contract['execution_date'] = dates[1].text.strip()
        contract['publication_date'] = dates[2].text.strip()
        if len(dates) >= 4:
            contract['update_date'] = dates[3].text.strip()
    
    return contract

def fetch_page(page_num, log_container):
    url = f"https://zakupki.gov.ru/epz/contract/search/results.html?page={page_num}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        log_message(log_container, f'Отправка запроса к странице {page_num}...')
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        log_message(log_container, f'Получен ответ от сервера, начинаю парсинг страницы {page_num}...')
        soup = BeautifulSoup(response.text, 'html.parser')
        contract_blocks = soup.find_all('div', class_='search-registry-entry-block')
        
        contracts = []
        for i, block in enumerate(contract_blocks, 1):
            contract_data = parse_contract_block(block)
            if contract_data:
                contracts.append(contract_data)
                log_message(log_container, f'Обработан контракт {i} на странице {page_num}')
        
        log_message(log_container, f'Завершена обработка страницы {page_num}', 'success')
        return contracts
    
    except requests.exceptions.RequestException as e:
        log_message(log_container, f"Ошибка при получении страницы {page_num}: {str(e)}", 'error')
        return []

def save_data(data, format='json', filename='contracts', log_container=None):
    if log_container:
        log_message(log_container, f'Сохранение данных в формате {format}...')
    
    try:
        if format == 'json':
            with open(f'{filename}.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            if log_container:
                log_message(log_container, f'Данные успешно сохранены в {filename}.json', 'success')
            return f'{filename}.json'
        
        elif format == 'csv':
            df = pd.DataFrame(data)
            df.to_csv(f'{filename}.csv', index=False, encoding='utf-8')
            if log_container:
                log_message(log_container, f'Данные успешно сохранены в {filename}.csv', 'success')
            return f'{filename}.csv'
    
    except Exception as e:
        if log_container:
            log_message(log_container, f'Ошибка при сохранении данных: {str(e)}', 'error')
        raise

def main():
    st.title('Парсер контрактов с zakupki.gov.ru')
    
    st.write('MAKE ZAKUPKI GREAT AGAIN :) ')
    
    col1, col2 = st.columns(2)
    
    with col1:
        num_pages = st.number_input('Количество страниц для парсинга', 
                                   min_value=1, 
                                   max_value=100, 
                                   value=1)
    
    with col2:
        output_format = st.selectbox('Формат выгрузки данных',
                                    ['JSON', 'CSV'])
    
    log_container = st.empty()
    with st.expander("Журнал процесса парсинга", expanded=True):
        log_area = st.container()
    
    if st.button('Начать парсинг'):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        all_contracts = []
        
        for i in range(num_pages):
            status_text.text(f'Обработка страницы {i+1} из {num_pages}...')
            contracts = fetch_page(i+1, log_area)
            all_contracts.extend(contracts)
            progress_bar.progress((i + 1) / num_pages)
            time.sleep(1)  # Добавляем задержку, чтобы не перегружать сервер
            
        if all_contracts:
            filename = f'contracts_{time.strftime("%Y%m%d_%H%M%S")}'
            saved_file = save_data(all_contracts, output_format.lower(), filename, log_area)
            
            st.success(f'Парсинг завершен! Собрано {len(all_contracts)} контрактов.')
            
            with open(saved_file, 'rb') as f:
                st.download_button(
                    label=f"Скачать данные ({output_format})",
                    data=f,
                    file_name=saved_file,
                    mime='application/octet-stream'
                )
        else:
            st.error('Не удалось получить данные о контрактах.')

if __name__ == '__main__':
    main()