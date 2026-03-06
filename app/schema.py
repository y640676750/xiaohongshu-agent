from pydantic import BaseModel
from typing import List

class Brief(BaseModel):
    link: str
    selling_point: str
    audience: str
    keywords: List[str]

class PostResult(BaseModel):
    titles: List[str]
    body: str
    topics: List[str]
    pinned_comment: str
    compliance_notes: List[str] = []