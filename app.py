from fastapi import FastAPI
from pydantic import BaseModel
from validator import AddressValidator

app = FastAPI()

# Lazy loading validatoru kvůli nízké RAM na Render Free
validator = None

def get_validator():
    global validator
    if validator is None:
        validator = AddressValidator()
    return validator

class AddressInput(BaseModel):
    city: str
    psc: str
    street: str
    cp: str

@app.post("/validate")
def validate_address(data: AddressInput):
    v = get_validator()
    return v.validate(data.city, data.psc, data.street, data.cp)

