from langchain.tools import tool, ToolRuntime
from langchain.messages import HumanMessage
from langchain.tools import BaseTool
from langchain.base_language import BaseLanguageModel
import langchain
from pydantic import BaseModel, Field
from typing import Optional, Type, Dict, Any

##схемы входных параметров
class SearchByNameInput(BaseModel):
    name: str = Field(description="Chemical compound name (e.g., 'aspirin', 'paracetamol', 'caffeine')")
    exact_match: bool = Field(default=True, description="If True, search exact name; if False, search partial matches")
   
class SearchBySMILESInput(BaseModel):
    smiles: str = Field(description="SMILES notation of the compound (e.g., 'CC(=O)OC1=CC=CC=C1C(=O)O' for aspirin)")
    detailed: bool = Field( default=False, description="If True, returns detailed information including synonyms and properties"
    )

class SearchByFormulaInput(BaseModel):
    formula: str = Field(description="Molecular formula (e.g., 'C9H8O4', 'C8H9NO2')")

###======tool===#####
class SearchCompoundByName(BaseTool):
    name: str = "SearchCompoundByName"
    description:  str =  "Useful to find chemical information about a specific compound."
    "Input the compound name (e.g., 'aspirin', 'paracetamol')."
    args_schema: Type[BaseModel] = SearchByNameInput

    def _run(self, name: str, exact_match: bool = True) -> str:
        """Execute search by name"""
        try: 
            ##здесь нужно прописать, как было в исходном коде
            url =""

        except Exception as e:
            return f"Error searching PubChem: {str(e)}"
        
    async def _arun():
        """Use the tool asynchronously."""


class SearchCompoundBySMILES(BaseTool):
    name: str = "SearchCompoundBySMILES"
    description:  str = "Useful to find a compound by its SMILES notation. "
    "Input a SMILES string (e.g., 'CC(=O)OC1=CC=CC=C1C(=O)O' for aspirin)."

    args_schema: Type[BaseModel] = SearchBySMILESInput

    def _run(self, smiles: str, detailed: bool = False) -> str:
        try:
            ## конвертация smiles в CID(убрать, если в исходном коде было не так)
            cid = self._smiles_to_cid(smiles)
            if not cid:
                return f"No compound found for SMILES: {smiles}\n\nPossible reasons:\n- Invalid SMILES syntax\n- Compound not in PubChem database\n- Check the SMILES string and try again"
        
        except Exception as e:
            return f"Error searching PubChem by SMILES: {str(e)}"

    def _smiles_to_cid(self, smiles: str) -> Optional[int]:##тоже убрать если этого не было
        import urllib.parse
        encoded_smiles = urllib.parse.quote(smiles)

    async def _arun(self, smiles: str, detailed: bool = False) -> str:
        """Use the tool asynchronously.""" #далее нужно будет скорее всего добавить асинхрон
        raise NotImplementedError("this tool does not support async")


class SearchCompoundByFormula(BaseTool):
    name: str = "SearchCompoundByFormula"
    description:  str = "Useful to find compounds by molecular formula. "
    "Input a formula (e.g., 'C9H8O4', 'C6H12O6'). Returns matching compounds."
    args_schema: Type[BaseModel] = SearchByFormulaInput

    def _run(self,formula: str) -> str:
        try:
            formula = formula.strip()
            #далее поиск по  CID

        except Exception as e:
            return f"Error searching PubChem by formula: {str(e)}"

    async def _arun(self):
        """Use the tool asynchronously."""
        raise NotImplementedError("this tool does not support async")
