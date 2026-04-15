from mcp.server.fastmcp import FastMCP
import requests
import urllib.parse
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
                "name": props.get('Title', 'Unknown'),
                "formula": props.get('MolecularFormula', 'N/A'),
                "weight": props.get('MolecularWeight', 'N/A')
            }
    except Exception:
        pass
    
    return {
        "cid": cid,
        "name": "Unknown",
        "formula": "N/A",
        "weight": "N/A"
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

    """Search PubChem for compounds matching a chemical name.

    Parameters
    ----------
    name : str
        Chemical name to search for (e.g., "aspirin", "caffeine").
    limit : int, optional
        Maximum number of results to return, by default 5.

    Returns
    -------
    str
        JSON string with structure:
        - Success: {"error": false, "query": "...", "results": [...], "count": N}
        - Failure: {"error": true, "message": "...", "results": []}

    Notes
    -----
    - Results include full compound properties (CID, IUPAC name, formula, weight).
    - Name can be systematic, common, or trade name.
    """

    async with httpx.AsyncClient(timeout=10) as client:

        encoded_name = urllib.parse.quote(name)
        url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{encoded_name}/cids/JSON"

        try:
            response = await client.get(url, timeout=10)
            #response.raise_for_status()
            data = response.json()

        except Exception as e:
    
           return json.dumps({"error": True, "message": f"Failed to fetch CID: {str(e)}", "results": []})

        if response.status_code != 200:

            return json.dumps({"error": True, "message": f"Compound '{name}' not found", "results": []})

        cid_list = data.get('IdentifierList', {}).get('CID', [])[:limit]#достаем не более 5 cid из ответа 
        
        if not cid_list:
            return json.dumps({"error": True, "message": f"No compounds found for '{name}'", "results": []})
        
        results = await asyncio.gather(*[_fetch_props(cid, client) for cid in cid_list])
        
        return json.dumps({
            "error": False,
            "query": name,
            "results": results,
            "count": len(results)
        }, ensure_ascii=False)


##tool 2

@mcp.tool()
async def  search_by_smiles_pubchem(smiles: str, limit: int = 5) -> str:
    """Search PubChem for compounds matching a SMILES string.

    Parameters
    ----------
    smiles : str
        SMILES string to search for.
    limit : int, optional
        Maximum number of results to return, by default 5.

    Returns
    -------
    str
        JSON string with structure:
        - Success: {"error": false, "query": "...", "results": [...], "count": N}
        - Failure: {"error": true, "message": "...", "results": []}

    Notes
    -----
    - Results include CID, IUPAC name, formula, and molecular weight.
    - Returns JSON string even on error (no exceptions raised).
    """
    async with httpx.AsyncClient(timeout=10) as client:

        try:

            encoded_smiles = urllib.parse.quote(smiles)
            url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/smiles/{encoded_smiles}/cids/JSON"
            response = await client.get(url, timeout=10)
            data = response.json()

        except Exception as e:

            return json.dumps({"error": True, "message": f"Failed to fetch CID: {str(e)}", "results": []})

        if response.status_code != 200:

            return json.dumps({"error": True, "message": f"Compound with SMILES '{smiles}' not found", "results": []})

        cid_list = data.get('IdentifierList', {}).get('CID', [])[:limit]#достаем не более 5 cid из ответа 
        
        if not cid_list:
            return json.dumps({"error": True, "message": f"No compounds found for SMILES '{smiles}'", "results": []})
        
        results = await asyncio.gather(*[_fetch_props(cid, client) for cid in cid_list])
        
        return json.dumps({
            "error": False,
            "query": smiles,
            "results": results,
            "count": len(results)
        }, ensure_ascii=False)
        

#tool 3

@mcp.tool()
async def search_by_formula_pubchem(formula: str, limit: int = 5) -> str:
    """Search PubChem for compounds matching a molecular formula.

    Parameters
    ----------
    formula : str
        Molecular formula to search for (e.g., "C6H12O6").
    limit : int, optional
        Maximum number of results to return, by default 5.

    Returns
    -------
    str
        JSON string with structure:
        - Success: {"error": false, "query": "...", "query_type": "formula", "results": [{"cid": ..., "name": ...}], "count": N}
        - Failure: {"error": true, "message": "...", "results": []}

    Notes
    -----
    - Uses PubChem fastformula endpoint for efficient formula-based search.
    - Returns only CID and compound name in results (simplified output).
    - Empty formula input returns error immediately.
    """
    
    if not formula or not formula.strip():
        return json.dumps({"error": True, "message": "Formula cannot be empty", "results": []})
    
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            encoded_formula = urllib.parse.quote(formula)
            url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/fastformula/{encoded_formula}/cids/JSON"
            response = await client.get(url)
            data = response.json()

        except Exception as e:
            return json.dumps({"error": True, "message": f"Failed to fetch CID: {str(e)}", "results": []})
        
        if response.status_code != 200:
            return json.dumps({"error": True, "message": f"Formula '{formula}' not found", "results": []})
        
        cid_list = data.get('IdentifierList', {}).get('CID', [])[:limit]
        
        if not cid_list:
            return json.dumps({"error": True, "message": f"No compounds found for formula '{formula}'", "results": []})
        
        results = await asyncio.gather(*[_fetch_props(cid, client) for cid in cid_list])
        
        simplified_results = [
            {"cid": r["cid"], "name": r["name"]} 
            for r in results
        ]
        
        return json.dumps({
            "error": False,
            "query": formula,
            "query_type": "formula",
            "results": simplified_results,
            "count": len(results)
        }, ensure_ascii=False)


#tool 4
@mcp.tool()
async def search_compound_by_inchikey(inchikey: str, limit: int = 5) -> str:
    """
    Search PubChem compounds by exact InChIKey.
    
    Example: "BSYNRYMUTXBXSQ-UHFFFAOYSA-N" for aspirin
    
    Args:
        inchikey: InChIKey string (27-character identifier)
        limit: Maximum number of results (1-10, default: 5)
    """
    if not inchikey or not inchikey.strip():
        return json.dumps({
            "error": True,
            "message": "InChIKey cannot be empty",
            "results": []
        }, ensure_ascii=False)
    
    limit = max(1, min(limit, 10))
    
    async with httpx.AsyncClient(timeout=10) as client:

        try:
            encoded = urllib.parse.quote(inchikey.strip())
            url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/inchikey/{encoded}/cids/JSON"
            response = await client.get(url)
            
            if response.status_code != 200:
                return json.dumps({
                    "error": True,
                    "message": f"InChIKey '{inchikey}' not found",
                    "results": []
                }, ensure_ascii=False)
            
            data = response.json()
            cid_list = data.get('IdentifierList', {}).get('CID', [])[:limit]
            
            if not cid_list:
                return json.dumps({
                    "error": True,
                    "message": f"No compounds found for InChIKey '{inchikey}'",
                    "results": []
                }, ensure_ascii=False)
            

            results = await asyncio.gather(*[_fetch_props(cid, client) for cid in cid_list])
            
            return json.dumps({
                "error": False,
                "query": inchikey,
                "query_type": "inchikey",
                "results": results,
                "count": len(results)
            }, ensure_ascii=False)
            
        except httpx.TimeoutException:
            return json.dumps({
                "error": True,
                "error_type": "timeout",
                "message": "Request timed out",
                "retryable": True,
                "results": []
            }, ensure_ascii=False)
        
        except Exception as e:
            return json.dumps({
                "error": True,
                "error_type": "internal_error",
                "message": str(e),
                "results": []
            }, ensure_ascii=False)

if __name__ == "__main__":#запуск цикла событий
    mcp.run(transport="stdio")