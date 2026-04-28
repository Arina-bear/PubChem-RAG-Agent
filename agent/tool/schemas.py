##схемы входных параметров
from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator
import langchain
from pydantic import BaseModel, Field

class SearchByNameInput(BaseModel):
    name: str = Field(min_length=1, max_length=160, description="Compound name or search keyword from the user.")
    limit: int = Field(default=5, ge=1, le=10, description="Maximum number of candidate compounds to return.")
    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("name must not be blank")
        return cleaned
   
class SearchBySMILESInput(BaseModel):
    smiles: str = Field(min_length=1, max_length=512, description="SMILES string to resolve in PubChem.")
    limit: int = Field(default=5, ge=1, le=10, description="Maximum number of candidate compounds to return.")

    @field_validator("smiles", mode="before")
    @classmethod
    def strip_smiles(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("smiles must not be blank")
        return cleaned

class SearchByFormulaInput(BaseModel):
    formula: str = Field(min_length=1, max_length=64, description="Molecular formula to resolve in PubChem.")
    limit: int = Field(default=5, ge=1, le=10, description="Maximum number of candidate compounds to return.")

    @field_validator("formula", mode="before")
    @classmethod
    def strip_formula(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("formula must not be blank")
        return cleaned