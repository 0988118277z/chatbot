### 介紹

**1. 資料來源**
PPT八卦論壇上的資料，python套件Requests取得資料，並透過Threat多工提升速度。

**2. 資料儲存**
用Selite 與 Mongodb儲存資料。

**3. 前端顯示**
用python套件Streamlit，做資料的傳遞與呈現。[參考資料](https://blog.streamlit.io/how-to-build-an-llm-powered-chatbot-with-streamlit/?source=post_page-----6a3c30860fbc--------------------------------)

**4. 後端處理**
用OpenAI做為LLM，透過Langchain結合LLM與DB，Dbscan與TF-IDF做文字的前置處理。



## 使用說明

**1. 建立MongoDB**
建立完成後，要將Mongodb連線資訊寫到環境變數中。

**2. 安裝Python套件**
安裝 requirements.txt 清單的套件。

**3. 資料蒐集**
執行 url_update.py 與 data_update.py 來更新資料。

**4. 取得OpenAI API KEY**
註冊[OpenAi](https://platform.openai.com/settings/profile?tab=api-keys)的API KEY。

**5. 執行程式**
streamlit.exe run streamlit_app.py。

**6. 開始使用**
在WEB的文字輸入框，輸入內容。