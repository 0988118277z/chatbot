import requests, re, math, os
from bs4 import BeautifulSoup
from datetime import datetime
import sqlite3, pymongo

user = os.getenv('mongodb_user')
passwd = os.getenv('mongodb_password')
host = os.getenv('mongodb_ip')
port = os.getenv('mongodb_port')
db = os.getenv('mongodb_db')

class PptGossiping():
    def __init__(self):
        self.logfile = open(f'pttlog{datetime.now().date()}.txt', "a+")
        self.sess = requests.Session()
        self.payload = {'from':'/bbs/Gossiping/index.html', 'yes':'yes'}
        self.myHeader = {'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'}

    def get_pttNews_urls(self):
        self.sess.post("https://www.ptt.cc/ask/over18", headers = self.myHeader, data=self.payload)  #ppt 滿18歲的驗證
        url = 'https://www.ptt.cc/bbs/Gossiping/index.html'
        data = self.sess.get(url, headers = self.myHeader)
        soup = BeautifulSoup(data.text,'lxml')
        url_last2 = "https://www.ptt.cc"+soup.select('div.btn-group.btn-group-paging a')[1].get("href")  #找出倒數第二頁
        # print(url_last2)  #檢查抓到的連結
        utl_last = int(re.findall('\d+',url_last2)[0]) + 1  #取得倒數第二頁頁碼，加1變成最後一頁
        # print(utl_last)  #檢查號碼
        
        urls = [f'https://www.ptt.cc/bbs/Gossiping/index{page}.html' for page in range(1,utl_last+1)]
        
        conn = sqlite3.connect('sql.db')
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS records
                     (id INTEGER PRIMARY KEY, title TEXT, url TEXT UNIQUE)''')
        conn.close()

        # print('done', file=self.logfile, flush=True)
        return urls
        
    def update_url(self):  #更新DB內的八卦站頁數
        conn = sqlite3.connect('sql.db')
        c = conn.cursor()
        c.execute("select count(*) from records;")
        count_urls = c.fetchall()
        conn.close()
        currentpage = math.ceil(count_urls[0][0]/20)  #math.ceil(num)=無條件進位，一頁有20筆資料
        
        self.sess.post("https://www.ptt.cc/ask/over18", headers = self.myHeader, data=self.payload)  #ppt 滿18歲的驗證
        url = 'https://www.ptt.cc/bbs/Gossiping/index.html'
        data = self.sess.get(url, headers = self.myHeader)
        soup = BeautifulSoup(data.text,'lxml')

        url_last2 = "https://www.ptt.cc"+soup.select('div.btn-group.btn-group-paging a')[1].get("href")  #找出倒數第二頁
        # print(url_last2)  #檢查抓到的連結
        utl_last = int(re.findall('\d+',url_last2)[0]) + 1  #取得倒數第二頁頁碼，加1變成最後一頁
        # print(utl_last)  #檢查號碼
        
        urls = [f'https://www.ptt.cc/bbs/Gossiping/index{page}.html' for page in range(currentpage,utl_last+1)]

        return urls

    def fetch_url(self, url):  #抓指定八卦站頁數的資料
        data = self.sess.get(url, headers = self.myHeader)
        soup = BeautifulSoup(data.text,'lxml')
        titles = soup.select("div.r-ent div.title a")
        insert_data = [ ( i.text, 'https://www.ptt.cc/' + i.get('href') ) for i in titles ]
        
        conn = sqlite3.connect('sql.db')
        try:
            c = conn.cursor()
            c.executemany("INSERT INTO records (title, url) VALUES (?, ?)",insert_data)
            conn.commit()
            conn.close()  
        except:
            conn.close()  
        print(url)
    
    def update_message_data(self):
        mongo_dbs = pymongo.MongoClient(f"mongodb://{user}:{passwd}@{host}:{port}/{db}")
        mydb = mongo_dbs["pttdata"]
        mycol = mydb["messages"]
        try:
            datas = mycol.find().sort({"_id": -1 }).limit( 1 )  #找出_id最大的數
            data_id = datas[0]['_id']
        except:  
            data_id = 0
        print(f'data update start with {data_id}', file=self.logfile, flush=True)
        conn = sqlite3.connect('sql.db')
        c = conn.cursor()
        c.execute(f"select id,url from records where id>{data_id};")
        count_urls = c.fetchall()
        conn.close()

        url_ids = [ i[0] for i in count_urls]
        urls = [ i[1] for i in count_urls]
        return url_ids, urls
   
    def get_message_data(self, url_id, url):
        self.sess.post("https://www.ptt.cc/ask/over18", headers = self.myHeader, data=self.payload)  #ppt 滿18歲的驗證
        data = self.sess.get(url, headers = self.myHeader)
        soup = BeautifulSoup(data.text,'lxml')

        gossiping_titles = soup.select("div.article-metaline span.article-meta-tag")
        gossiping_contents = soup.select("div.article-metaline span.article-meta-value")
        # for i,j in zip(gossiping_titles,gossiping_contents):
            # print(f'{i.text}:{j.text}')

        pattern = re.compile(r'</span></div>\s*(.*?)\s*<span class=', re.DOTALL)
        matches = pattern.findall(str(soup.select("div.bbs-screen")))
        # for match in matches:
            # print(match)
        # print(matches[3])
            
        message_users = soup.select("div.push span.push-userid")
        message_contents = soup.select("div.push span.push-content")
        # for i,j in zip(message_users,message_contents):
            # print(f'{i.text}:{j.text[1:]}')  #[1:] 過濾掉留言是:開頭
        
        data = [{
            '_id':url_id,
            'gossiping_user':gossiping_contents[0].text,
            'gossiping_title':gossiping_contents[1].text,
            'gossiping_time':gossiping_contents[2].text,
            'gossiping_content':matches[3],
            'message': [{'user':user.text, 'content':message.text[1:]} for user,message in zip (message_users,message_contents)]
            }]
        # print(data)
        print('ready to connect mongo')
        mongo_dbs = pymongo.MongoClient(f"mongodb://{user}:{passwd}@{host}:{port}/{db}")
        mydb = mongo_dbs["pttdata"]
        mycol = mydb["messages"]
        print('ready to insert')
        data = mycol.insert_many(data)
        mongo_dbs.close()
        print(f'done:{url}')
