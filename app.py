from fastapi import FastAPI
from pydantic import BaseModel
from validator import AddressValidator

app = FastAPI()
validator = AddressValidator("data/addresses.csv")

class AddressInput(BaseModel):
    city: str
    psc: str = ""
    street: str = ""
    cp: str = ""
    co: str = ""

@app.post("/validate")
def validate_address(addr: AddressInput):
    result = validator.validate(
        addr.city,
        addr.psc,
        addr.street,
        addr.cp,
        addr.co
    )
    return result
