from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class AmountToQuery(BaseModel):
    amount : int