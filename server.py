from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict
from wechat import WeChat, find_process_id_by_name

app = FastAPI()

class Message(BaseModel):
    type: str
    content: str

class SendMessageRequest(BaseModel):
    target: str
    messages: List[Message]

class SendUrlRequest(BaseModel):
    url: str
    target: List[str] 

class SendCopyUrlRequest(BaseModel):
    url: str


@app.post("/login")
async def login():
    wechat_pid = find_process_id_by_name("WeChat.exe")
    if not wechat_pid:
        raise HTTPException(status_code=404, detail="WeChat process not found")
    
    elements = WeChat.find_elements(wechat_pid)
    if not elements:
        raise HTTPException(status_code=404, detail="WeChat window not found")
    
    first = elements[0]
    wechat = WeChat(first.handle, first.process_id, 0)
    result = wechat.login()
    return {"qrcode": result['qrcode']}

@app.post("/logout")
async def logout():
    wechat_pid = find_process_id_by_name("WeChat.exe")
    if not wechat_pid:
        raise HTTPException(status_code=404, detail="WeChat process not found")
    
    elements = WeChat.find_elements(wechat_pid)
    if not elements:
        raise HTTPException(status_code=404, detail="WeChat window not found")
    
    first = elements[0]
    wechat = WeChat(first.handle, first.process_id, 0)
    wechat.logout()
    return {"message": "Logged out successfully"}

@app.post("/send_private_messages")
async def send_private_messages(request: SendMessageRequest):
    wechat_pid = find_process_id_by_name("WeChat.exe")
    if not wechat_pid:
        raise HTTPException(status_code=404, detail="WeChat process not found")
    
    elements = WeChat.find_elements(wechat_pid)
    if not elements:
        raise HTTPException(status_code=404, detail="WeChat window not found")
    
    first = elements[0]
    wechat = WeChat(first.handle, first.process_id, 0)
    wechat.send_private_messages(request.dict())
    return {"message": "Messages sent successfully"}

@app.post("/send_url")
async def send_url(request: SendUrlRequest):
    wechat_pid = find_process_id_by_name("WeChat.exe")
    if not wechat_pid:
        raise HTTPException(status_code=404, detail="WeChat process not found")
    
    elements = WeChat.find_elements(wechat_pid)
    if not elements:
        raise HTTPException(status_code=404, detail="WeChat window not found")
    
    first = elements[0]
    wechat = WeChat(first.handle, first.process_id, 0)
    wechat.send_url(request.dict())
    return {"message": "URL sent successfully"}

@app.post("/copy_url")
async def send_url(request: SendCopyUrlRequest):
    wechat_pid = find_process_id_by_name("WeChat.exe")
    if not wechat_pid:
        raise HTTPException(status_code=404, detail="WeChat process not found")
    
    elements = WeChat.find_elements(wechat_pid)
    if not elements:
        raise HTTPException(status_code=404, detail="WeChat window not found")
    
    first = elements[0]
    wechat = WeChat(first.handle, first.process_id, 0)
    res = wechat.copy_url(request.dict())
    return {"data": res}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)