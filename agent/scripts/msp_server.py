from mcp.server.fastmcp import FastMCP
import requests
import urllib.parse
from typing import Any
import httpx
#from schemas import (SearchByNameInput, SearchBySMILESInput, SearchByFormulaInput)
import json
import asyncio

from app.errors.models import AppError, ErrorCode

"Создание mcp-сервера"""

mcp = FastMCP("pubchem-tools")

async def _fetch_props(cid: int, client: httpx.AsyncClient) -> dict:
    """
    Fetch compound properties from PubChem by CID.
    
    Args:
        cid: PubChem Compound ID
        client: HTTP client for making requests
    
    Returns:
        Dictionary with cid, name, formula, and weight
    """
    prop_url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/property/MolecularFormula,MolecularWeight,Title/JSON"
    
    try:
        response = await client.get(prop_url)
        
        if response.status_code == 200:
            data = response.json()
            props = data['PropertyTable']['Properties'][0]
            return {
                "cid": cid,
                "title": props.get('Title'),
                "molecular_formula": props.get('MolecularFormula'),
                "molecular_weight": float(props['MolecularWeight']) if props.get('MolecularWeight') else None
            }
    except Exception:
        pass
    
    return {
        "cid": cid,
        "title": f"CID {cid}",
        "molecular_formula": None,
        "molecular_weight": None
    }

def _error_payload(error: AppError) -> dict[str, Any]:
    return {
        "ok": False,
        "error": {
            "code": error.code.value,
            "message": error.message,
            "retriable": error.retriable,
            "details": error.details or None,
        },
    }


def _unexpected_error_payload(error: Exception) -> dict[str, Any]:
    return {
        "ok": False,
        "error": {
            "code": ErrorCode.UPSTREAM_UNAVAILABLE.value,
            "message": f"Непредвиденная ошибка tool execution: {error}",
            "retriable": False,
            "details": None,
        },
    }


@mcp.tool()
async def search_by_name_pubchem(name: str, limit: int = 5) -> str:
    """Search PubChem for compounds matching a chemical name."""
    async with httpx.AsyncClient(timeout=10) as client:
        encoded_name = urllib.parse.quote(name)
        url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{encoded_name}/cids/JSON"

        try:
            response = await client.get(url, timeout=10)
            data = response.json()

            if response.status_code != 200:
                return json.dumps({
                    "ok": False, 
                    "message": f"Compound '{name}' not found", 
                    "matches": []
                }, ensure_ascii=False)

            cid_list = data.get('IdentifierList', {}).get('CID', [])[:limit]
            
            if not cid_list:
                return json.dumps({
                    "ok": False, 
                    "message": f"No compounds found for '{name}'", 
                    "matches": []
                }, ensure_ascii=False)
            
            results = await asyncio.gather(*[_fetch_props(cid, client) for cid in cid_list])
            
            # ФИНАЛЬНЫЙ RETURN: используем ok и matches
            return json.dumps({
                "ok": True,
                "query": name,
                "matches": results,
                "count": len(results)
            }, ensure_ascii=False)

        except Exception as e:

            return json.dumps({
                "ok": False, 
                "message": f"Failed to fetch CID: {str(e)}", 
                "matches": []
            }, ensure_ascii=False)

##tool 2

@mcp.tool()
async def search_by_smiles_pubchem(smiles: str, limit: int = 5) -> str:
    """Search PubChem for compounds matching a SMILES string."""
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            encoded_smiles = urllib.parse.quote(smiles)
            url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/smiles/{encoded_smiles}/cids/JSON"
            response = await client.get(url, timeout=10)
            data = response.json()

            if response.status_code != 200:
                return json.dumps({
                    "ok": False, 
                    "message": f"Compound with SMILES '{smiles}' not found", 
                    "matches": []
                }, ensure_ascii=False)

            cid_list = data.get('IdentifierList', {}).get('CID', [])[:limit]
            
            if not cid_list:
                return json.dumps({
                    "ok": False, 
                    "message": f"No compounds found for SMILES '{smiles}'", 
                    "matches": []
                }, ensure_ascii=False)
            
            results = await asyncio.gather(*[_fetch_props(cid, client) for cid in cid_list])
            
            # ФИНАЛЬНЫЙ RETURN: синхронизировано с common.py и AgentService
            return json.dumps({
                "ok": True, 
                "query": smiles, 
                "matches": results, 
                "count": len(results)
            }, ensure_ascii=False)

        except Exception as e:
            return json.dumps({
                "ok": False, 
                "message": f"Failed to fetch CID: {str(e)}", 
                "matches": []
            }, ensure_ascii=False)
        

#tool 3

@mcp.tool()
async def search_by_formula_pubchem(formula: str, limit: int = 5) -> str:
    """Search PubChem for compounds matching a molecular formula."""
    
    if not formula or not formula.strip():
        return json.dumps({
            "ok": False, 
            "message": "Formula cannot be empty", 
            "matches": []
        }, ensure_ascii=False)
    
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            encoded_formula = urllib.parse.quote(formula)
            url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/fastformula/{encoded_formula}/cids/JSON"
            response = await client.get(url)
            
            if response.status_code != 200:
                return json.dumps({
                    "ok": False, 
                    "message": f"Formula '{formula}' not found", 
                    "matches": []
                }, ensure_ascii=False)
            
            data = response.json()
            cid_list = data.get('IdentifierList', {}).get('CID', [])[:limit]
            
            if not cid_list:
                return json.dumps({
                    "ok": False, 
                    "message": f"No compounds found for formula '{formula}'", 
                    "matches": []
                }, ensure_ascii=False)
            
            results = await asyncio.gather(*[_fetch_props(cid, client) for cid in cid_list])
            
            # ВАЖНО: Используем "title", а не "name", так как это вернул _fetch_props
            # И упаковываем в "matches"
            return json.dumps({
                "ok": True,
                "query": formula,
                "query_type": "formula",
                "matches": results, 
                "count": len(results)
            }, ensure_ascii=False)

        except Exception as e:
            return json.dumps({
                "ok": False, 
                "message": f"Failed to fetch CID: {str(e)}", 
                "matches": []
            }, ensure_ascii=False)

#tool 4
@mcp.tool()
async def search_compound_by_inchikey(inchikey: str, limit: int = 5) -> str:
    """Search PubChem compounds by exact InChIKey."""
    if not inchikey or not inchikey.strip():
        return json.dumps({
            "ok": False,
            "message": "InChIKey cannot be empty",
            "matches": []
        }, ensure_ascii=False)
    
    limit = max(1, min(limit, 10))
    
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            encoded = urllib.parse.quote(inchikey.strip())
            url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/inchikey/{encoded}/cids/JSON"
            response = await client.get(url)
            
            if response.status_code != 200:
                return json.dumps({
                    "ok": False,
                    "message": f"InChIKey '{inchikey}' not found",
                    "matches": []
                }, ensure_ascii=False)
            
            data = response.json()
            cid_list = data.get('IdentifierList', {}).get('CID', [])[:limit]
            
            if not cid_list:
                return json.dumps({
                    "ok": False,
                    "message": f"No compounds found for InChIKey '{inchikey}'",
                    "matches": []
                }, ensure_ascii=False)
            
            results = await asyncio.gather(*[_fetch_props(cid, client) for cid in cid_list])
            
            return json.dumps({
                "ok": True,             
                "query": inchikey,
                "query_type": "inchikey",
                "matches": results,     
                "count": len(results)
            }, ensure_ascii=False)
            
        except Exception as e:
            return json.dumps({
                "ok": False,
                "error_type": "internal_error",
                "message": str(e),
                "matches": []
            }, ensure_ascii=False)

if __name__ == "__main__":#запуск цикла событий
    mcp.run(transport="stdio")