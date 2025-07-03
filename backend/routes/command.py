
import subprocess
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class Command(BaseModel):
    command: str

@router.post("/")
def run_command(cmd: Command):
    try:
        result = subprocess.run(cmd.command, shell=True, capture_output=True, text=True)
        return {"output": result.stdout, "error": result.stderr}
    except Exception as e:
        return {"error": str(e)}
