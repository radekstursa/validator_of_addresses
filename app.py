from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
from validator import AddressValidator

app = FastAPI()
validator = AddressValidator()

class AddressRequest(BaseModel):
    city: str
    psc: str
    street: str
    cp: str
    co: Optional[str] = None

@app.post("/validate")
def validate_address(req: AddressRequest):
    return validator.validate(req.city, req.psc, req.street, req.cp, req.co
    )
