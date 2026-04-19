"""
Pydantic schemas for PubChem tool input validation.

These schemas define the structure and validation rules for all
PubChem search tools used by the chemistry agent.
"""

from pydantic import BaseModel, Field, field_validator
from typing import  Literal
def clean_string(value: str) -> str:
    return value.strip()


class SearchByNameInput(BaseModel):
    """
    This schema validates user input when searching for compounds
    using their common name, IUPAC name, or trade name.
    
    Attributes:
        name: The compound name or search keyword 
        limit: Maximum number of candidate compounds to return (1-10)
      
    Validation rules:
        - name must be 1-160 characters
        - name cannot be empty or whitespace only

    """
    name: str = Field(min_length=1, max_length=160, description="Compound name or search keyword from the user.")
    limit: int = Field(default=5, ge=1, le=10, description="Maximum number of candidate compounds to return.")

    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, value: str) -> str:
        """
        Validate and clean the compound name input.
        Removes leading/trailing whitespace and ensures the name is not empty.
        
        Args:
            value: Raw input string from user
            
        Returns:
            Stripped and validated name string
            
        """
        cleaned = clean_string(value)

        if not cleaned:
         
         raise ValueError("name must not be blank")
        
        return cleaned


class SearchBySMILESInput(BaseModel):
    """ 
    This schema validates SMILES (Simplified Molecular Input Line Entry System)
    strings used for structure-based compound search.
    
    Attributes:
        smiles: SMILES string
        limit: Maximum number of candidate compounds to return (1-10)
    
    Validation rules:
        - smiles must be 1-512 characters
        - smiles cannot be empty or whitespace only
    """
    smiles: str = Field(min_length=1, max_length=512, description="SMILES string to resolve in PubChem.")
    limit: int = Field(default=5, ge=1, le=10, description="Maximum number of candidate compounds to return.")

    @field_validator("smiles", mode="before")
    @classmethod
    def strip_smiles(cls, value: str) -> str:
        """
        Validate and clean the SMILES string input.
        
        Removes leading/trailing whitespace and ensures the string is not empty.
        
        Args:
            value: Raw SMILES string from user
            
        Returns:
            Stripped and validated SMILES string
        """
        cleaned = clean_string(value)

        if not cleaned:
         
         raise ValueError("SMILES must not be blank")
        
        return cleaned


class SearchByFormulaInput(BaseModel):
    """
    This schema validates molecular formula strings (Hill notation)
    for compound search based on elemental composition.
    
    Attributes:
        formula: Molecular formula in Hill notation (e.g., "C9H8O4", "CH3COOH")
        limit: Maximum number of candidate compounds to return (1-10)
    
    Validation rules:
        - formula must be 1-64 characters
        - formula cannot be empty or whitespace only
        - limit must be between 1 and 10
    """
    
    formula: str = Field(min_length=1, max_length=64, description="Molecular formula to resolve in PubChem.")
    limit: int = Field(default=5, ge=1, le=10, description="Maximum number of candidate compounds to return.")

    @field_validator("formula", mode="before")
    @classmethod
    def strip_formula(cls, value: str) -> str:
        """
        Validate and clean the molecular formula input.
        
        Removes leading/trailing whitespace, converts to uppercase,
        and ensures the formula is not empty.
        
        Args:
            value: Raw formula string from user
            
        Returns:
            Stripped and validated formula string (uppercase)
            
        """
        cleaned = clean_string(value)

        if not cleaned:
         
         raise ValueError("Formula must not be blank")
        
        return cleaned



class SearchByMassRangeArgs(BaseModel):
    """
    This schema validates mass range queries, allowing users to find compounds
    with molecular weights or exact masses within a specified interval.
    
    Use cases:
        - Find all compounds with molecular weight between 100-200 g/mol
        - Search for compounds with exact mass close to a target value
        - Filter compounds by monoisotopic mass for mass spectrometry analysis
    
    Validation rules:
        - min_mass must be >= 0
        - max_mass must be >= min_mass
        - limit must be between 1 and 10
        - mass_type must be one of: "molecular_weight", "exact_mass", "monoisotopic_mass"
    """
    min_mass: float = Field(description="Lower bound of the mass range.")
    max_mass: float = Field(description="Upper bound of the mass range.")
    mass_type: Literal["molecular_weight", "exact_mass", "monoisotopic_mass"] = Field(
        default="molecular_weight",
        description="Which PubChem mass field to search by.",
    )
    limit: int = Field(default=5, ge=1, le=10, description="Maximum number of candidate compounds to return.")



class SearchByInChIKeyArgs(BaseModel):
    """
    This schema validates InChIKey strings for compound search.
    
    InChIKey is a 27-character hashed version of the InChI identifier.
    
    Attributes:
        inchikey: InChIKey string 
        limit: Maximum number of candidate compounds to return (1-10)
    
    Validation rules:
        - inchikey must be 1-64 characters
    """
    inchikey: str = Field(min_length=1, max_length=64, description="InChIKey string to resolve in PubChem.")
    limit: int = Field(default=5, ge=1, le=10, description="Maximum number of candidate compounds to return.")

    @field_validator("inchikey", mode = "before")
    @classmethod
    def strip_inchikey(cls, value: str) -> str:
        cleaned = clean_string(value)

        if not cleaned:
         
         raise ValueError("InChIKey must not be blank")
        
        return cleaned


###############################
##########################
##new############
class CompoundSummaryArgs(BaseModel):
    cid: int = Field(gt=0, description="PubChem compound CID.")


class NameToSmilesArgs(BaseModel):
    name: str = Field(min_length=1, max_length=160, description="Compound name to resolve to canonical SMILES.")

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("name must not be blank")
        return cleaned


class SearchBySynonymArgs(BaseModel):
    synonym: str = Field(min_length=1, max_length=160, description="Alternative name or synonym for the compound.")
    limit: int = Field(default=5, ge=1, le=10, description="Maximum number of candidate compounds to return.")

    @field_validator("synonym")
    @classmethod
    def strip_synonym(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("synonym must not be blank")
        return cleaned


    