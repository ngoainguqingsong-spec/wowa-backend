# api.py
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from core.command_engine import CommandEngine

app = FastAPI()

class ToolRequest(BaseModel):
    tool: str
    input: str
    cloud: bool = False

@app.post("/tool")
async def tool_endpoint(req: ToolRequest):
    # Chuyển request thành command theo format CommandEngine yêu cầu
    command = {
        "version": "v1",
        "type": "req",          # bạn có thể đặt type bất kỳ, miễn pass validate
        "payload": req.dict()
    }
    try:
        result = CommandEngine.run(command)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)