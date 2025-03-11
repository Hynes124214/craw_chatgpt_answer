import concurrent.futures
import time
from selenium import webdriver
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pickle
import os
import uvicorn
from fastapi import FastAPI, UploadFile ,Request, Form
from fastapi.responses import JSONResponse
import os
import config
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sys
import json
import threading
import asyncio
from datetime import datetime
import shutil

app = FastAPI()

thread_local_data = threading.local()

CHROMEDRIVER_ORIGINAL = "C:/Users/Administrator/AppData/Roaming/undetected_chromedriver/undetected_chromedriver.exe"
CHROMEDRIVER_TEMP_DIR = "C:/Users/Administrator/AppData/Roaming/undetected_chromedriver/temp/"

os.makedirs(CHROMEDRIVER_TEMP_DIR, exist_ok=True)

def create_unique_chromedriver_copy():
    """Tạo bản sao duy nhất của chromedriver.exe."""
    process_id = os.getpid()
    unique_path = os.path.join(CHROMEDRIVER_TEMP_DIR, f"chromedriver_{process_id}_{datetime.now().timestamp()}.exe")
    shutil.copy(CHROMEDRIVER_ORIGINAL, unique_path)
    return unique_path

active_requests = 0
lock = asyncio.Lock()

def crawl_chatgpt(prompt,active_requests):
    try:
        unique_chromedriver_path = create_unique_chromedriver_copy()
        options = uc.ChromeOptions()
        options.debugger_address = "127.0.0.1:9222"
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--disable-extensions")
        options.add_argument("--use_subprocess")
        options.headless = True
        
        driver = uc.Chrome(driver_executable_path=unique_chromedriver_path, options=options)
        driver.execute_script("window.open('https://chatgpt.com/');")
        time.sleep(3)
        sleep_follow_request = (10-active_requests)*10 
        tabs = driver.window_handles
        cur_id = tabs[active_requests]
        driver.switch_to.window(cur_id)
        print(f"request {active_requests}: id: {cur_id}")
        try:
            a_xpath = "/html/body/div[1]/div[2]/main/div[1]/div[1]/div/div/div/div/article/div/div/div[2]/div/div[1]/div/div/div/pre/div/div[3]/code"
            # initial_code_count = len(driver.find_elements(By.XPATH, a_xpath))
            a_wait_xpath = "/html/body/div[1]/div[2]/main/div[1]/div[1]/div/div/div/div/article/div/div/div[2]/div/div[1]/div/div/div/p[2]"
            initial_p_count = len(driver.find_elements(By.XPATH, a_wait_xpath))
            prompt_input = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '#prompt-textarea > p'))
            )
            full_prompt = f"trả về văn bản json cho t copy, đưa thêm bình luận bằng 1 câu sau khi kết thúc: {prompt}"
            prompt_input.send_keys(full_prompt)
            prompt_input.send_keys(Keys.ENTER)
            try:
                WebDriverWait(driver, sleep_follow_request).until(
                    lambda driver: len(driver.find_elements(By.XPATH, a_wait_xpath)) > initial_p_count
                )
            except Exception as e:
                print(f"lỗi: {e}")
            all_code_elements = driver.find_elements("xpath", "//code[contains(@class, 'whitespace-pre') and contains(@class, 'hljs')]")
            print(f"trích xuất nội dung  ")
            last_code_element = all_code_elements[-1]
            last_code_text = last_code_element.text
            cleaned_text = "".join(last_code_text.splitlines())
            # print(cleaned_text)
            driver.close()
            return {
                "result": f"{cleaned_text}"
            }
        except Exception as e:
            end_time = time.time()
            readable_end_time = datetime.fromtimestamp(end_time).strftime('%Y-%m-%d %H:%M:%S')
            print(f"Lỗi: {e}")
            print(f"danh sách các tab id: {tabs}; thread {active_requests}: started at {readable_time}, end at {readable_end_time}, id: {cur_id}")
            time.sleep(5)
    except Exception as e:
        print(f"Lỗi: {e}")
        time.sleep(5)
        # driver.close()
    finally:
        driver.quit()

@app.post("/chatgpt_crawler")
async def crawl_request(prompt: str = Form(...)):
    global active_requests
    active_requests += 1
    start_time = time.time()
    readable_time = datetime.fromtimestamp(start_time).strftime('%Y-%m-%d %H:%M:%S')
    print(f"request {active_requests} started at {readable_time}")
    time.sleep(5)
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, crawl_chatgpt, prompt, active_requests)
    end_time = time.time()
    readable_end_time = datetime.fromtimestamp(end_time).strftime('%Y-%m-%d %H:%M:%S')            
    print(f"request {active_requests}: started at {readable_time}, end at {readable_end_time}")
    active_requests -= 1
    return result

if __name__ == '__main__':
    uvicorn.run("main:app",
                host=config.HOST,
                port=config.PORT,
                workers=config.WORKERS)
