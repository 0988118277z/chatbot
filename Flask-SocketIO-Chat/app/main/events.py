from flask import session
from flask_socketio import emit, join_room, leave_room
from .. import socketio

@socketio.on('joined', namespace='/chat')
def joined(message):
    """Sent by clients when they enter a room.
    A status message is broadcast to all people in the room."""
    room = session.get('room')
    join_room(room)
    emit('status', {'msg': session.get('name') + ' has entered the room.'}, room=room)


@socketio.on('text', namespace='/chat')
def text(message):
    """Sent by a client when the user entered a new message.
    The message is sent to all people in the room."""
    room = session.get('room')
    emit('message', {'msg': session.get('name') + ':' + message['msg']}, room=room)
    if room == 'chatbot' and session.get('name') != 'chatbot':
        msg = mongodb_langchain(message['msg'])
        emit('message', {'msg': 'chatbot' + ':' + msg}, room=room)


@socketio.on('left', namespace='/chat')
def left(message):
    """Sent by clients when they leave a room.
    A status message is broadcast to all people in the room."""
    room = session.get('room')
    leave_room(room)
    emit('status', {'msg': session.get('name') + ' has left the room.'}, room=room)
    
def mongodb_langchain(prompt_txt):
    from langchain_openai import OpenAI
    from langchain.chains import LLMChain
    from langchain.prompts import PromptTemplate
    import pymongo, json
    import os
    
    api_key = os.getenv('openai_api_key')
    user = os.getenv('mongodb_user')
    passwd = os.getenv('mongodb_password')
    host = os.getenv('mongodb_ip')
    port = os.getenv('mongodb_port')
    db = os.getenv('mongodb_db')

    llm = OpenAI(api_key=api_key, temperature=0.3)

    mongo_dbs = pymongo.MongoClient(f"mongodb://{user}:{passwd}@{host}:{port}/{db}")
    mydb = mongo_dbs["pttdata"]
    mycollection = mydb["messages"]

    prompt_template = PromptTemplate(input_variables=["user_input"],template="""
        '_id': 八卦資料編號,
        'gossiping_user': 八卦發起人,
        'gossiping_title': 八卦標題,
        'gossiping_time': 八卦發起時間,
        'gossiping_content': 八卦簡介說明,
        'message': ['user': 討論者名稱, 'content': 討論內容,'user': 討論者名稱, 'content': 討論內容,'user': 討論者名稱, 'content': 討論內容]
        
        這是我的mongodb結構，請先分析 "{user_input}" 這個對話，分辨使用者是想了解的是主題類型還是內容類型，                         
        如果你分辨出的是主題類型，請從gossiping_title回復mongodb語法，範例: 輸入:有沒有地震的八卦  輸出:{{"gossiping_title":{{"$regex":"地震"}}}},{{"gossiping_title":1,"_id":0}}
        如果你分辨出的是內容類型，請從gossiping_title回復mongodb語法，範例: 輸入:下雨會不會影響到地震  輸出:{{"gossiping_title":{{"$regex":"地震"}},{{"message":1,"_id":0}}
        我要將你的回覆內容作為自動查詢資料庫的指令，所以不要有任何說明
        """)
    chain = LLMChain(llm=llm, prompt=prompt_template)
    result = chain.run(user_input=prompt_txt)
    # print(result)
    try:
        mongo_query = result.split('輸出:')[1].replace(' ','')
    except:
        mongo_query = result
    print(mongo_query.replace('},{','},,,{').split(',,,')[0])
    print(mongo_query.replace('},{','},,,{').split(',,,')[1].split('\n')[0])
    query = mongo_query.replace('},{','},,,{').split(',,,')[0]
    projection = mongo_query.replace('},{','},,,{').split(',,,')[1].split('\n')[0]
    query = json.loads(query)
    projection = json.loads(projection)
    
    query_result = mycollection.find(query,projection)
    results = [ str(i) for i in query_result]
    mongo_dbs.close()
    
    llm = OpenAI(api_key=api_key, temperature=0.8, max_tokens=4096)
    prompt_record = PromptTemplate(input_variables=["user_input","mongo_records"],template="""
        "{mongo_records}"是我蒐集的資料，請分析我的資料，然後從 "{user_input}" 的對話，了解這段話的意思，做出適當的回應。
        """)
    end_chain = LLMChain(llm=llm, prompt=prompt_record)
    result = end_chain.run(user_input=prompt_txt, mongo_records=results)
    print(result)
    return result

