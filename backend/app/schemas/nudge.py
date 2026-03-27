from pydantic import BaseModel


class NudgeResponse(BaseModel):
    nudges: list[str]
