from typing import Annotated
from fastapi import Depends
from sqlalchemy.orm import Session

from core.database import get_db

# Reusable DB session dependency
DbSession = Annotated[Session, Depends(get_db)]

