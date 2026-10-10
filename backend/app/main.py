from pathlib import Path
import json
import re
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(title="PLC Archive Backend", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
DATA = Path(__file__).resolve().parents[1] / "data"
DATA.mkdir(exist_ok=True)
STATE = DATA / "state.json"

class ProjectState(BaseModel):
    project_name: str = Field(default="Motor Control Project", min_length=1, max_length=120)
    instructions: list[dict] = Field(default_factory=list)

INSTRUCTIONS = [
 {"id":"contact_no","name":"NO Contact","symbol":"--| |--","kind":"contact","implemented":True,"description":"Passes logic when the referenced Boolean value is ON.","default_address":"I0.0","tooltip":"Normally Open contact"},
 {"id":"contact_nc","name":"NC Contact","symbol":"--|/|--","kind":"contact","implemented":True,"description":"Passes logic when the referenced Boolean value is OFF.","default_address":"I0.1","tooltip":"Normally Closed contact"},
 {"id":"coil_output","name":"Output Coil","symbol":"--( )--","kind":"coil","implemented":True,"description":"Writes the rung result to an output or Boolean tag.","default_address":"Q0.0","tooltip":"Output coil"},
 {"id":"coil_set","name":"Set Bit","symbol":"--(S)--","kind":"coil","implemented":False,"description":"Set bit catalog entry; execution not implemented.","default_address":"M0.0","tooltip":"Set coil"},
 {"id":"coil_reset","name":"Reset Bit","symbol":"--(R)--","kind":"coil","implemented":False,"description":"Reset bit catalog entry; execution not implemented.","default_address":"M0.0","tooltip":"Reset coil"},
 {"id":"timer_ton","name":"TON","symbol":"TON","kind":"timer","implemented":False,"description":"On-delay timer; execution not implemented.","default_address":"T1","tooltip":"On-delay timer"},
 {"id":"timer_tof","name":"TOF","symbol":"TOF","kind":"timer","implemented":False,"description":"Off-delay timer; execution not implemented.","default_address":"T2","tooltip":"Off-delay timer"},
 {"id":"timer_tp","name":"TP","symbol":"TP","kind":"timer","implemented":False,"description":"Pulse timer; execution not implemented.","default_address":"T3","tooltip":"Pulse timer"},
 {"id":"counter_ctu","name":"CTU","symbol":"CTU","kind":"counter","implemented":False,"description":"Count-up counter; execution not implemented.","default_address":"C1","tooltip":"Count up"},
 {"id":"counter_ctd","name":"CTD","symbol":"CTD","kind":"counter","implemented":False,"description":"Count-down counter; execution not implemented.","default_address":"C2","tooltip":"Count down"},
 {"id":"compare_eq","name":"Equal","symbol":"==","kind":"compare","implemented":False,"description":"Equality comparison; execution not implemented.","default_address":"","tooltip":"Compare equal"},
 {"id":"compare_gt","name":"Greater Than","symbol":">","kind":"compare","implemented":False,"description":"Greater-than comparison; execution not implemented.","default_address":"","tooltip":"Compare greater than"},
 {"id":"compare_lt","name":"Less Than","symbol":"<","kind":"compare","implemented":False,"description":"Less-than comparison; execution not implemented.","default_address":"","tooltip":"Compare less than"},
 {"id":"math_add","name":"Add","symbol":"ADD","kind":"math","implemented":False,"description":"Addition; execution not implemented.","default_address":"","tooltip":"Add values"},
 {"id":"math_sub","name":"Subtract","symbol":"SUB","kind":"math","implemented":False,"description":"Subtraction; execution not implemented.","default_address":"","tooltip":"Subtract values"},
 {"id":"math_mul","name":"Multiply","symbol":"MUL","kind":"math","implemented":False,"description":"Multiplication; execution not implemented.","default_address":"","tooltip":"Multiply values"},
 {"id":"math_div","name":"Divide","symbol":"DIV","kind":"math","implemented":False,"description":"Division; execution not implemented.","default_address":"","tooltip":"Divide values"}
]
INSTRUCTION_BY_ID = {item["id"]: item for item in INSTRUCTIONS}
FOLDERS = [{"id":"instruction-folder","name":"Instruction Folder","children":[
 {"id":"bits","name":"Bits","instruction_ids":["contact_no","contact_nc","coil_output","coil_set","coil_reset"]},
 {"id":"timers","name":"Timers","instruction_ids":["timer_ton","timer_tof","timer_tp"]},
 {"id":"counters","name":"Counters","instruction_ids":["counter_ctu","counter_ctd"]},
 {"id":"comparators","name":"Comparators","instruction_ids":["compare_eq","compare_gt","compare_lt"]},
 {"id":"math","name":"Math Operators","instruction_ids":["math_add","math_sub","math_mul","math_div"]},
 {"id":"function-blocks","name":"Function Blocks","instruction_ids":[]},
 {"id":"program-control","name":"Program Control","instruction_ids":[]}
]}]

INPUT_ADDRESS = re.compile(r"^I0\.[0-7]$", re.IGNORECASE)
OUTPUT_ADDRESS = re.compile(r"^Q0\.[0-7]$", re.IGNORECASE)

def validate_ladder(instructions: list[dict]) -> None:
    """Validate addresses and enforce contacts-before-output-instructions."""
    output_seen = False

    for index, node in enumerate(instructions):
        instruction_id = node.get("instructionId")
        instruction = INSTRUCTION_BY_ID.get(instruction_id)

        if instruction is None:
            raise HTTPException(
                status_code=422,
                detail=f"Instruction {index + 1}: unknown instruction id."
            )

        kind = instruction["kind"]
        address = str(node.get("address", "")).strip()

        # Output coil, Set Bit, and Reset Bit all terminate the rung.
        if kind == "contact":
            if output_seen:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        f"Instruction {index + 1}: input contacts "
                        "cannot appear after an output, Set Bit, or Reset Bit."
                    )
                )

            if not INPUT_ADDRESS.fullmatch(address):
                raise HTTPException(
                    status_code=422,
                    detail=(
                        f"Instruction {index + 1}: input contacts "
                        "must use I0.0 through I0.7."
                    )
                )

        elif kind == "coil":
            output_seen = True

            if instruction_id == "coil_output":
                if not OUTPUT_ADDRESS.fullmatch(address):
                    raise HTTPException(
                        status_code=422,
                        detail=(
                            f"Instruction {index + 1}: output coils "
                            "must use Q0.0 through Q0.7."
                        )
                    )

@app.get("/api/health")
def health():
    return {"status": "ok", "service": "plc-archive-backend"}

@app.get("/api/archive")
def archive():
    return {"folders": FOLDERS, "instructions": INSTRUCTIONS}

@app.get("/api/state")
def get_state():
    if not STATE.exists():
        value = ProjectState().model_dump()
        STATE.write_text(json.dumps(value, indent=2), encoding="utf-8")
        return value
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ProjectState().model_dump()

@app.put("/api/state")
def save_state(state: ProjectState):
    if not state.project_name.strip():
        raise HTTPException(status_code=422, detail="Project name cannot be blank.")
    validate_ladder(state.instructions)
    value = state.model_dump()
    STATE.write_text(json.dumps(value, indent=2), encoding="utf-8")
    return {"status": "saved", **value}
