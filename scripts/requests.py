from pydantic import BaseModel

class ProvisionRequest(BaseModel):
    is_provision: bool = False
    instance_count: int = 0
    ig_name: str
    zone: str