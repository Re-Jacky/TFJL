from typing import Literal
from pydantic import BaseModel

FileTypeEnum = Literal['collab', 'activity']

class FileModel(BaseModel):
    file: str
    type: FileTypeEnum

class WithContentFileModel(FileModel):
    content: str

