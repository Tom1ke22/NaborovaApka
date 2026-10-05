import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.limits import MAX_CHAT_MESSAGE_CHARS


class ChatStartIn(BaseModel):
    position_id: uuid.UUID
    # Uchádzač sa pred chatom už nepredstavuje — meno pýtame až v prihláške.
    # Pole ostáva kvôli starším klientom, ktorí ho ešte posielajú.
    applicant_name: str | None = Field(default=None, max_length=200)


class ChatStartOut(BaseModel):
    session_id: str
    # Tajomstvo, ktoré sa vracia len tu. Klient ho posiela pri každej správe
    # a pri odoslaní prihlášky. Nikdy nepatrí do URL.
    claim_token: str
    greeting: str


class ChatStreamIn(BaseModel):
    """Jedna správa uchádzača.

    `message` má tvrdý strop: dlhší vstup pydantic odmietne s 422 ešte predtým,
    než sa čokoľvek uloží do DB alebo pošle jazykovému modelu. Bez toho vie
    jedna session poslať megabajty textu a každý znak je token, ktorý platíme.
    """

    # Session ID vyrába server ako UUID4, 100 znakov je strop stĺpca v DB.
    session_id: str = Field(min_length=1, max_length=100)
    claim_token: str = Field(min_length=1, max_length=200)
    message: str = Field(min_length=1, max_length=MAX_CHAT_MESSAGE_CHARS)


class ChatMsgOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    role: str
    content: str
    created_at: datetime
