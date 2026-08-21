from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from predict import predict_match_winner, predict_top_player

class MatchInput(BaseModel):
    home_team: str = Field(...)
    away_team: str = Field(...)
    date: str = Field(...)

class PlayerInput(BaseModel):
    team: str = Field(...)
    date: str = Field(...)
    top_n: int = Field(default=5, ge=1, le=20)

match_winner_prediction = StructuredTool.from_function(
    func=predict_match_winner,
    name="match_winner_prediction",
    description="Predict an AFL match winner using historical model features.",
    args_schema=MatchInput,
)

top_player_prediction = StructuredTool.from_function(
    func=predict_top_player,
    name="top_player_prediction",
    description="Predict top AFL players for a team.",
    args_schema=PlayerInput,
)
