from pttGossiping import PptGossiping
from concurrent.futures import ThreadPoolExecutor

def update_url():   
    scrap = PptGossiping()
    # with ThreadPoolExecutor(max_workers=10) as executor: 
    with ThreadPoolExecutor() as executor: 
        # urls = scrap.get_pttNews_urls()  #取得所有資料
        urls = scrap.update_url()  #更新現有資料
        executor.map(scrap.fetch_url, urls)
update_url()