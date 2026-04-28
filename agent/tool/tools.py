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
    
