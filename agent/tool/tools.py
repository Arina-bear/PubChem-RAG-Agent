from langchain.tools import BaseTool
from typing import Type, Optional, Any, Dict
import requests
import urllib.parse
import logging
from schemas import (SearchByNameInput, SearchBySMILESInput, SearchByFormulaInput)
from pydantic import BaseModel
from langchain.callbacks import get_callback_manager

def search_by_name_pubchem(name: str, limit: int = 5) -> Dict[str, Any]:
    """Search for compound by name in PubChem"""

    encoded_name = urllib.parse.quote(name)
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{encoded_name}/cids/JSON"
    response = requests.get(url, timeout=10)
        
    if response.status_code != 200:
        return {"error": f"Compound '{name}' not found", "results": []}
        
    data = response.json()
    cid_list = data.get('IdentifierList', {}).get('CID', [])[:limit]
        
    if not cid_list:
        return {"error": f"No compounds found for '{name}'", "results": []}
        
    results = []
    
    for cid in cid_list:
        try:
            # Get properties
            prop_url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/property/MolecularFormula,MolecularWeight,Title/JSON"
            prop_resp = requests.get(prop_url, timeout=10)
            if prop_resp.status_code == 200:
                prop_data = prop_resp.json()
                props = prop_data['PropertyTable']['Properties'][0]
                results.append({
                    "cid": cid,
                    "name": props.get('Title', 'Unknown'),
                    "formula": props.get('MolecularFormula', 'N/A'),
                    "weight": props.get('MolecularWeight', 'N/A')
                })
        
        except Exception as e:
            logging.warning(f"Failed to fetch properties for CID {cid}: {e}")
            continue

    return {"query": name, "results": results, "count": len(results)}
           
    
def search_by_smiles_pubchem(smiles: str) -> Dict[str, Any]:
    """Search for compound by SMILES in PubChem"""
    try:
        encoded_smiles = urllib.parse.quote(smiles)
        url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/smiles/{encoded_smiles}/cids/JSON"
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
         return {"error": f"Compound '{smiles}' not found", "results": None}
      

        data = response.json()
        cid_list = data.get('IdentifierList', {}).get('CID', [])

        if not cid_list:# улучшить обработку исключений
            return {"error": f"No compound found for SMILES '{smiles}'", "results": None}
        
        cid = cid_list[0]#если несколько cid то берем самый релевантный
        prop_url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/property/MolecularFormula,MolecularWeight,Title/JSON"
        prop_resp = requests.get(prop_url, timeout=10)
        
        if prop_resp.status_code == 200:
            prop_data = prop_resp.json()
            props = prop_data['PropertyTable']['Properties'][0]
            return {
                "smiles": smiles,
                "cid": cid,
                "name": props.get('Title', 'Unknown'),
                "formula": props.get('MolecularFormula', 'N/A'),
                "weight": props.get('MolecularWeight', 'N/A')
            }
        
        return {"smiles": smiles, "cid": cid, "error": "Could not fetch properties"}
    except Exception as e:
        return {"error": str(e), "results": None}

def search_by_formula_pubchem(formula: str, limit: int = 5) -> Dict[str, Any]:
    """Search for compounds by molecular formula"""
    encoded_formula = urllib.parse.quote(formula)
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/fastformula/{encoded_formula}/cids/JSON"

    response = requests.get(url, timeout=10)
    if response.status_code != 200:
         return {"error": f"Compound '{formula}' not found", "results": None}
    
    data = response.json()
    cid_list = data.get('IdentifierList', {}).get('CID', [])

    if not cid_list:# улучшить обработку исключений
        return {"error": f"No compound found for formula '{formula}'", "results": None}
    
    results = []

    for cid in cid_list:
        try:
            prop_url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/property/Title/JSON"
            prop_resp = requests.get(prop_url, timeout=10)

            if prop_resp.status_code == 200:
                prop_data = prop_resp.json()
                name = prop_data['PropertyTable']['Properties'][0].get('Title', 'Unknown')
                results.append({"cid": cid, "name": name})
            else:
                results.append({"cid": cid, "name": "Unknown"})

        except Exception as e:
         logging.warning(f"Failed to fetch properties for CID {cid}: {e}")
         continue
        
    return {"formula": formula, "results": results, "count": len(results)}
    


###======tool 1===#####
class SearchCompoundByName(BaseTool):

    name: str = "SearchCompoundByName"
    description = (
        "Useful to find chemical information about a specific compound. "
        "Input the compound name (e.g., 'aspirin', 'paracetamol'). "
        "Returns CID, molecular formula, and molecular weight."
    )
    args_schema: Type[BaseModel] = SearchByNameInput

    def __init__(self):
        super().__init__()

    def _run(self, query: str) -> str:
        """Execute search by name"""

        result = search_by_name_pubchem(query)
        if result.get("error"):
            return f"Error: {result['error']}"
        
        if not result.get("results"):
            return f"No compounds found for '{query}'"
        
        output = f"Found {result['count']} compound(s) for '{query}':\n\n"
        for i, comp in enumerate(result['results'][:3], 1):
            output += f"{i}. {comp['name']}\n"
            output += f"   CID: {comp['cid']}\n"
            output += f"   Formula: {comp['formula']}\n"
            output += f"   MW: {comp['weight']} g/mol\n\n"
        
        return output.strip()
        
    async def _arun(self, query: str) -> str:
        """Use the tool asynchronously."""
        raise NotImplementedError("This tool does not support async")

##tool 2
class SearchCompoundBySMILES(BaseTool):
    name: str = "SearchCompoundBySMILES"
    description = (
        "Useful to find a compound by its SMILES notation. "
        "Input a SMILES string (e.g., 'CC(=O)OC1=CC=CC=C1C(=O)O' for aspirin). "
        "Returns compound name, CID, formula, and molecular weight."
    )


    args_schema: Type[BaseModel] = SearchBySMILESInput

    def __init__(self):
        super().__init__()

    def _run(self, query: str) -> str:
        """Search for compound by SMILES"""
        result = search_by_smiles_pubchem(query)

        if result.get("error"):
            return f"Error: {result['error']}"
        
        if not result.get("cid"):
            return f"No compound found for SMILES: {query}"
        return (
            f"Compound found for SMILES: {query[:50]}...\n"
            f"Name: {result['name']}\n"
            f"CID: {result['cid']}\n"
            f"Formula: {result['formula']}\n"
            f"Molecular Weight: {result['weight']} g/mol"
        )
    
    async def _arun(self, query: str) -> str:
        """Use the tool asynchronously."""
        raise NotImplementedError("This tool does not support async")
    
##tool 3
class SearchCompoundByFormula(BaseTool):
    name: str = "SearchCompoundByFormula"
    description = (
        "Useful to find compounds by molecular formula. "
        "Input a formula (e.g., 'C9H8O4', 'C6H12O6'). "
        "Returns matching compounds with their CIDs and names."
    )

    args_schema: Type[BaseModel] = SearchByFormulaInput

    def __init__(self):
        super().__init__()

    def _run(self, query: str) -> str:
        result = search_by_formula_pubchem(query)

        if result.get("error"):
            return f"Error: {result['error']}"
        
        if not result.get("results"):
            return f"No compounds found for formula '{query}'"
        
        output = f"Found {result['count']} compound(s) with formula {query}:\n\n"
        for i, comp in enumerate(result['results'], 1):
            output += f"{i}. {comp['name']} (CID: {comp['cid']})\n"
        
        return output.strip()

    async def _arun(self, query: str) -> str:
        """Use the tool asynchronously."""
        raise NotImplementedError("This tool does not support async")
