from fastapi import FastAPI
from pydantic import BaseModel
from typing import Union
from validator import AddressValidator

app = FastAPI()
validator = AddressValidator()

class Address(BaseModel):
    city: str
    psc: Union[str, int]
    street: str
    cp: Union[str, int]

@app.post("/validate")
def validate_address(addr: Address):
    return validator.validate(
        addr.city,
        addr.psc,
        addr.street,
        addr.cp
    )
