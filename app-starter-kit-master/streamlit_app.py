import streamlit as st
from langchain_openai import OpenAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
import pymongo, json, os, jieba
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import DBSCAN
from itertools import islice

api_key = os.getenv('openai_api_key')
user = os.getenv('mongodb_user')
passwd = os.getenv('mongodb_password')
host = os.getenv('mongodb_ip')
port = os.getenv('mongodb_port')
db = os.getenv('mongodb_db')

# App title
st.set_page_config(page_title="🤗💬 HugChat")

st.markdown(
    r"""
    <style>
    .stDeployButton {visibility: hidden;}
    p {color: red;}
    </style>
    """, unsafe_allow_html=True
)

# Store LLM generated responses
if "messages" not in st.session_state.keys():
    st.session_state.messages = [{"role": "assistant", 
        "content": "我是八卦機器人，告訴我你想知道的八卦主題，我可以告訴你其他人討論的八卦內容，範例：我想知道富士山的八卦"}]

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# world process
def preprocess_text_chinese(text):
    import jieba
    stopwords = [".", "=", ",", "，", "。", "?", "！", "？", "推", "了", "啦", "的", "阿", "啊", "吧", "囉", "喔", "嗎", "哈"]
    if 'http' not in text:
        for i in stopwords:
            text = text.replace(i,'')
        text = ' '.join(jieba.cut(text))
        return text
    return ''

# Function for generating LLM response
def generate_response(prompt_txt):
    llm = OpenAI(api_key=api_key, temperature=0.1)

    mongo_dbs = pymongo.MongoClient(f"mongodb://{user}:{passwd}@{host}:{port}/{db}")
    mydb = mongo_dbs["pttdata"]
    mycollection = mydb["messages"]

    prompt_template = PromptTemplate(input_variables=["user_input"],template="""
        '_id': 八卦資料編號,
        'gossiping_user': 八卦發起人,
        'gossiping_title': 八卦標題,
        'gossiping_time': 八卦發起時間,
        'gossiping_content': 八卦說明,
        'message': ['user': 討論者名稱, 'content': 討論內容,'user': 討論者名稱, 'content': 討論內容,'user': 討論者名稱, 'content': 討論內容]
        
        這是我的mongodb結構，請先分析 "{user_input}" 這個對話，分辨使用者是想了解的是主題類型還是內容類型，                         
        如果你分辨出的是主題類型，請從gossiping_title回復mongodb語法，範例: 輸入:keyword的八卦  輸出:{{"gossiping_content":{{"$regex":"keyword"}}}},{{"gossiping_title":1,"message.content":1,"_id":0}}
        如果你分辨出的是內容類型，請從gossiping_title回復mongodb語法，範例: 輸入:下雨影響到keyword的八卦內容  輸出:{{"gossiping_title":{{"$regex":"keyword"}}}},{{"gossiping_title":1,"message.content":1,"_id":0}}
        我要將你的回覆內容作為自動查詢資料庫的指令，所以回覆內容不要有任何說明，不要有任何中文字。
        """)
    chain = LLMChain(llm=llm, prompt=prompt_template)
    result = chain.run(user_input=prompt_txt)

    try:
        mongo_query = result.split('輸出:')[1].replace(' ','')
    except:
        mongo_query = result
     
    separator_index = mongo_query.find('},') + 1
    query_str = mongo_query[:separator_index]
    projection_str = mongo_query[separator_index + 1:]

    query = json.loads(query_str)
    projection = json.loads(projection_str)
    
    query_result = mycollection.find(query,projection)
    mongo_data = [ i for i in query_result]
    mongo_dbs.close()

    mongo_data_list = {i['gossiping_title']:[j['content'] for j in i['message']] for i in mongo_data}
    
    if len(mongo_data_list) > 5:
        key_list = [ preprocess_text_chinese(keys) for keys, values in mongo_data_list.items()]

        # TF-IDF
        vectorizer = TfidfVectorizer()
        tfidf_matrix = vectorizer.fit_transform(key_list)
        
        cosine_sim_matrix = cosine_similarity(tfidf_matrix)
        cosine_dist_matrix = 1 - cosine_sim_matrix
        cosine_dist_matrix[cosine_dist_matrix < 0] = 0  # 將所有小於0的變0
        # dbscan
        dbscan = DBSCAN(eps=0.4, min_samples=1, metric='precomputed')
        dbscan.fit(cosine_dist_matrix)
        
        cluster_labels = dbscan.labels_
        clustered_data = {}

        for i, label in enumerate(cluster_labels):
            if label not in clustered_data:
                clustered_data[label] = []
            clustered_data[label].append(list(mongo_data_list.keys())[i])      
        
        return_keyword = '由於類型過多，請從選擇一個你想要知道的內容\n'
        # print(f'選擇一個你想要知道的內容')
        if len(clustered_data) > 100:  #避免顯示結果太多
            start_index = max(0, len(clustered_data) - 100)
            clustered_data = dict(islice(clustered_data.items(), start_index, None))
        for keys, values in clustered_data.items():
            try:
                return_keyword += f"{int(keys) + 1}:{values[0].split(']')[1]}"
                # print(keys,':',values[0].split(']')[1])
            except:
                return_keyword += f"{int(keys) + 1}:{values[0]}"
                # print(keys,':',values[0])
            return_keyword += '  \n'  #多行用換行顯示
        return return_keyword
        
    message_list = [] #過濾空白的留言 
    for key, values in mongo_data_list.items():
        for i in values:
            if preprocess_text_chinese(i) != ' ' and i != '':
                message_list.append(preprocess_text_chinese(i))
    if len(message_list) > 0:
        # TF-IDF
        vectorizer = TfidfVectorizer()
        tfidf_matrix = vectorizer.fit_transform(message_list)
        
        #餘閒計算
        cosine_sim = cosine_similarity(tfidf_matrix)
        unique_message = []
        for i in range(len(message_list)):
            if all(cosine_sim[i, j] < 0.5 for j in range(len(message_list)) if i != j):    #相關的留言不要
                unique_message.append(message_list[i].replace(' ',''))
    else:
        unique_message = None
                
    # print(len(str(unique_message)))
    llm2 = OpenAI(api_key=api_key, temperature=0.8, max_tokens=2048)
    prompt_record = PromptTemplate(input_variables=["user_input","mongo_records"],template="""
        "{mongo_records}"，這些是資料，請分析這些資料，然後從 "{user_input}" 的主題，回覆內容。
        """)
    end_chain = LLMChain(llm=llm2, prompt=prompt_record)
    result = end_chain.run(user_input=prompt_txt, mongo_records=unique_message)
    return result
    

# User-provided prompt
if prompt := st.chat_input():
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

# Generate a new response if last message is not from assistant
if st.session_state.messages[-1]["role"] != "assistant":
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response = generate_response(prompt)
            st.write(response) 
    message = {"role": "assistant", "content": response}
    st.session_state.messages.append(message)