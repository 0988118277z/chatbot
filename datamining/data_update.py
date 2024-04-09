from pttGossiping import PptGossiping
from concurrent.futures import ThreadPoolExecutor

def update_date():
    scrap = PptGossiping()
    # max_workers = (os.cpu_count() or 1) * 5
    # with ThreadPoolExecutor(max_workers=10) as executor: 
    with ThreadPoolExecutor() as executor: 
        url_ids, urls = scrap.update_message_data() #更新現有資料
        executor.map(scrap.get_message_data, url_ids, urls)
update_date()