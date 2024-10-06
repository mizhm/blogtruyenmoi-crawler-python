from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import json
import time
import pandas as pd

base_url = 'https://blogtruyenmoi.com/danhsach/tatca'
total_pages = 1301 
chunk_size = 50 
max_retries = 10 

def fetch_manga_links(driver):
    links = []
    elements = driver.find_elements(By.CSS_SELECTOR, '.tiptip a')
    for element in elements:
        link = element.get_attribute('href')
        if link:
            links.append({
                'title': element.text.strip().rstrip(':'),
                'link': link if link.startswith('http') else f'https://blogtruyenmoi.com{link}'
            })
    return links

def fetch_manga_links_chunk(start_page, end_page, retries=0):
    try:
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        service = Service(ChromeDriverManager().install())  # Update with the path to your chromedriver
        driver = webdriver.Chrome(service=service, options=options)
        driver.get(base_url)
        # Wait until the document's ready state is complete
        WebDriverWait(driver, 60).until(
            lambda d: d.execute_script('return document.readyState') == 'complete'
        )
        # Load the specific page
        driver.execute_script(f'LoadListMangaPage({start_page})')
        WebDriverWait(driver, 60).until(
            EC.text_to_be_present_in_element((By.CSS_SELECTOR, '.current_page'), str(start_page))
        )

        all_manga_links = []
        current_page = start_page
        has_next_page = True

        while has_next_page and current_page <= end_page:
            try:
                manga_links = fetch_manga_links(driver)
                all_manga_links.extend(manga_links)

                # Check if there is a next page button and click it
                next_page_button = driver.find_element(By.CSS_SELECTOR, f'span.page > a[href="javascript:LoadListMangaPage({current_page + 1})"]')
                if next_page_button:
                    next_page_button.click()
                    WebDriverWait(driver, 60).until(
                        EC.text_to_be_present_in_element((By.CSS_SELECTOR, '.current_page'), str(current_page + 1))
                    )
                    current_page += 1
                else:
                    has_next_page = False
            except Exception as e:
                print(f'Error on page {current_page}: {e}')
                has_next_page = False

        driver.quit()
        return all_manga_links
    except Exception as e:
        print(f'Error fetching chunk {start_page} to {end_page}: {e}')
        if retries < max_retries:
            print(f'Retrying chunk {start_page} to {end_page} ({retries + 1}/{max_retries})')
            return fetch_manga_links_chunk(start_page, end_page, retries + 1)
        else:
            print(f'Failed to fetch chunk {start_page} to {end_page} after {max_retries} retries')
            return []

def fetch_all_manga_links():
    all_manga_links = []
    for i in range(0, total_pages, chunk_size):
        start_page = i + 1
        end_page = min(i + chunk_size, total_pages)
        print(f'Fetching pages {start_page} to {end_page}')
        manga_links_chunk = fetch_manga_links_chunk(start_page, end_page)
        if isinstance(manga_links_chunk, list):
            all_manga_links.extend(manga_links_chunk)
        else:
            print('manga_links_chunk is not a list:', manga_links_chunk)
    return all_manga_links

def fetch_manga_details(manga_links):
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    service = Service(ChromeDriverManager().install())  
    driver = webdriver.Chrome(service=service, options=options)
    manga_details = []

    for manga in manga_links:
        try:
            driver.get(manga['link'])
            WebDriverWait(driver, 60).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'h1'))
            )
            name = driver.find_element(By.CSS_SELECTOR, 'h1').text.strip()
            author = ', '.join([el.text.strip() for el in driver.find_elements(By.CSS_SELECTOR, 'a[href*="/tac-gia/"]')])
            genre = ', '.join([el.text.strip() for el in driver.find_elements(By.CSS_SELECTOR, '.description a[href*="/theloai/"]')])
            summary = driver.find_element(By.CSS_SELECTOR, '.detail .content').text.strip()
            page_views = driver.find_element(By.CSS_SELECTOR, '#PageViews').text.strip()
            like_count = driver.find_element(By.CSS_SELECTOR, '#LikeCount').text.strip()
            span_color_red = driver.find_elements(By.CSS_SELECTOR, '.description span.color-red')
            status = span_color_red[-1].text.strip() if span_color_red else ''
            another_name = ', '.join([span.text.strip() for span in span_color_red[:-1]]) if len(span_color_red) > 1 else 'Khong co ten khac'

            manga_details.append({
                'name': name,
                'author': author,
                'genre': genre,
                'summary': summary,
                'page_views': page_views,
                'like_count': like_count,
                'status': status,
                'another_name': another_name,
                'link': manga['link']
            })
        except Exception as e:
            print(f'Error fetching details for {manga["link"]}: {e}')

    driver.quit()
    return manga_details

def save_to_json(file_name, data):
    with open(file_name, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f'Saved to {file_name}')

def save_to_excel(filename, data):
    df = pd.DataFrame(data)
    df.to_excel(filename, index=False)

def main():
    manga_links = fetch_all_manga_links()
    save_to_json('manga_links.json', manga_links)
    manga_details = fetch_manga_details(manga_links)
    save_to_json('manga_details.json', manga_details)
    save_to_excel('manga_details.xlsx', manga_details)

if __name__ == '__main__':
    main()