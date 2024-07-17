import undetected_chromedriver as uc
from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import urllib.request
from urllib.error import URLError

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

class Browse:
    def __init__(self):
        options = uc.ChromeOptions()
        # 设置代理
        # options.add_argument('--proxy-server=http://your_proxy_server:port')
        self.driver = uc.Chrome(options=options)

    def get(self, url):
        try:
            self.driver.get(url)
            try:
                # 等待页面加载并查找验证按钮
                verify_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.ID, 'js_verify'))  # 替换为验证按钮的ID或其他定位方式
                )

                # 点击验证按钮
                verify_button.click()

                # 你可以添加更多操作，例如填写表单或等待验证完成等
                time.sleep(5)  # 等待几秒钟以查看验证结果
            except Exception as e:
                print(e)
            
            return self.driver.page_source
        except URLError as e:
            print(f"连接超时。错误信息: {e}")
            return None

    def __del__(self):
        if hasattr(self, 'driver'):
            self.driver.quit()

    def download_driver(self, url):
        try:
            file_path, _ = urllib.request.urlretrieve(url, timeout=60)  # 增加超时时间
            return file_path
        except URLError as e:
            print(f"下载驱动文件失败: {e}")
            return None


app = FastAPI()
browser = Browse()

class URLRequest(BaseModel):
    url: str

@app.post("/fetch_page")
def fetch_page(request: URLRequest):
    
    data = browser.get(request.url)
    if data:
        return {"message": "页面内容获取成功", "data": data}
    else:
        raise HTTPException(status_code=500, detail="页面内容获取失败")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
