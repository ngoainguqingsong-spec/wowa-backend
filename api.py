# api.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from core.command_engine import CommandEngine
from core.tool_registry import register_tool
import uvicorn

app = FastAPI(title="WOWA Tool Executor")

class ToolRequest(BaseModel):
    tool: str
    input: str
    cloud: bool = False

class ToolSpec(BaseModel):
    name: str
    version: str
    schema_version: str
    command_template: str
    input_schema: dict
    output_schema: dict
    sandbox_config: dict

class RegisterRequest(BaseModel):
    spec: ToolSpec

@app.post("/tool")
def execute_tool(request: ToolRequest):
    command = {
        "version": "v1",
        "type": "req",           # type "req" để pipeline xử lý tool
        "payload": request.dict()
    }
    try:
        result = CommandEngine.run(command)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tool-register")
def register_tool_endpoint(req: RegisterRequest):
    try:
        register_tool(req.spec.dict())
        return {"status": "registered", "tool": req.spec.name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def root():
    return {"status": "ok", "message": "WOWA API is running"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)