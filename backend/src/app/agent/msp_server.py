from mcp.server.fastmcp import FastMCP
import requests
import urllib.parse
from typing import Any
import httpx
#from schemas import (SearchByNameInput, SearchBySMILESInput, SearchByFormulaInput)
import json
import asyncio

from app.errors.models import AppError, ErrorCode

from app.schemas.schemas import (SearchByNameInput,SearchBySMILESInput,SearchByFormulaInput,SearchByMassRangeArgs
                                 ,SearchByInChIKeyArgs)

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


#обработка
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
async def search_by_name_pubchem(arguments: SearchByNameInput) -> str:
    """Search PubChem for compounds matching a chemical name."""
    val = arguments.name
    limit = arguments.limit

    async with httpx.AsyncClient(timeout=10) as client:
        encoded_name = urllib.parse.quote(val)
        url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{encoded_name}/cids/JSON"

        try:
            response = await client.get(url, timeout=10)
            data = response.json()

            if response.status_code != 200:
                return json.dumps({
                    "ok": False, 
                    "message": f"Compound '{val}' not found", 
                    "matches": []
                }, ensure_ascii=False)

            cid_list = data.get('IdentifierList', {}).get('CID', [])[:limit]
            
            if not cid_list:
                return json.dumps({
                    "ok": False, 
                    "message": f"No compounds found for '{val}'", 
                    "matches": []
                }, ensure_ascii=False)
            
            results = await asyncio.gather(*[_fetch_props(cid, client) for cid in cid_list])
            
            # ФИНАЛЬНЫЙ RETURN: используем ok и matches
            return json.dumps({
                "ok": True,
                "query": val,
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
async def search_by_smiles_pubchem(arguments: SearchBySMILESInput) -> str:

    """Search PubChem for compounds matching a SMILES string."""

    val = arguments.smiles
    limit = arguments.limit

    async with httpx.AsyncClient(timeout=10) as client:
        try:
            encoded_smiles = urllib.parse.quote(val)
            url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/smiles/{encoded_smiles}/cids/JSON"
            response = await client.get(url, timeout=10)
            data = response.json()

            if response.status_code != 200:
                return json.dumps({
                    "ok": False, 
                    "message": f"Compound with SMILES '{val}' not found", 
                    "matches": []
                }, ensure_ascii=False)

            cid_list = data.get('IdentifierList', {}).get('CID', [])[:limit]
            
            if not cid_list:
                return json.dumps({
                    "ok": False, 
                    "message": f"No compounds found for SMILES '{val}'", 
                    "matches": []
                }, ensure_ascii=False)
            
            results = await asyncio.gather(*[_fetch_props(cid, client) for cid in cid_list])
            
            return json.dumps({
                "ok": True, 
                "query": val, 
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
async def search_by_formula_pubchem(arguments: SearchByFormulaInput) -> str:
    """Search PubChem for compounds matching a molecular formula."""

    val = arguments.formula 
    limit = arguments.limit
    
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            encoded_formula = urllib.parse.quote(val)
            url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/fastformula/{encoded_formula}/cids/JSON"
            response = await client.get(url)
            
            if response.status_code != 200:
                return json.dumps({
                    "ok": False, 
                    "message": f"Formula '{val}' not found", 
                    "matches": []
                }, ensure_ascii=False)
            
            data = response.json()
            cid_list = data.get('IdentifierList', {}).get('CID', [])[:limit]
            
            if not cid_list:
                return json.dumps({
                    "ok": False, 
                    "message": f"No compounds found for formula '{val}'", 
                    "matches": []
                }, ensure_ascii=False)
            
            results = await asyncio.gather(*[_fetch_props(cid, client) for cid in cid_list])
            
            return json.dumps({
                "ok": True,
                "query": val,
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
async def search_compound_by_inchikey(arguments: SearchByInChIKeyArgs) -> str:
    """Search PubChem compounds by exact InChIKey."""
    val = arguments.inchikey 
    limit = arguments.limit

    async with httpx.AsyncClient(timeout=10) as client:
        try:
            encoded = urllib.parse.quote(val.strip())
            url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/inchikey/{encoded}/cids/JSON"
            response = await client.get(url)
            
            if response.status_code != 200:
                return json.dumps({
                    "ok": False,
                    "message": f"InChIKey '{val}' not found",
                    "matches": []
                }, ensure_ascii=False)
            
            data = response.json()
            cid_list = data.get('IdentifierList', {}).get('CID', [])[:limit]
            
            if not cid_list:
                return json.dumps({
                    "ok": False,
                    "message": f"No compounds found for InChIKey '{val}'",
                    "matches": []
                }, ensure_ascii=False)
            
            results = await asyncio.gather(*[_fetch_props(cid, client) for cid in cid_list])
            
            return json.dumps({
                "ok": True,             
                "query": val,
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

#tool 5
#@mcp.tool()
#async def search_compound_by_mass_range(
 #   min_mass: float,
  #  max_mass: float,
  #  mass_type: str = "molecular_weight",
  #  limit: int = 5
#) -> str:
  #  """
 #   Search PubChem compounds by a bounded mass range.
  #  mass_type can be: 'molecular_weight', 'exact_mass', or 'monoisotopic_mass'.
   # """
    # Маппинг типов масс для URL PubChem
   # mass_map = {
    #    "molecular_weight": "MolecularWeight",
     #   "exact_mass": "ExactMass",
     #   "monoisotopic_mass": "MonoisotopicMass"
   # }
  #  pubchem_mass_type = mass_map.get(mass_type, "MolecularWeight")
    
   # async with httpx.AsyncClient(timeout=15) as client:
    #    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/{pubchem_mass_type}/{min_mass}:{max_mass}/cids/JSON"
     #   try:
        #    response = await client.get(url)
        #    if response.status_code != 200:
           #     return json.dumps({"ok": False, "message": "Mass range search failed", "matches": []})

          #  data = response.json()
           # cid_list = data.get('IdentifierList', {}).get('CID', [])[:limit]
            
          #  if not cid_list:
           #     return json.dumps({"ok": True, "matches": [], "count": 0})

          #  results = await asyncio.gather(*[_fetch_props(cid, client) for cid in cid_list])
          #  return json.dumps({
              #  "ok": True, 
             #   "query": {"min": min_mass, "max": max_mass, "type": mass_type}, 
             #   "matches": results, 
             #   "count": len(results)
           # }, ensure_ascii=False)
      #  except Exception as e:
           # return json.dumps({"ok": False, "message": str(e)})

#tool 6

#@mcp.tool()
#async def get_compound_summary(cid: int) -> str:
  #  """Fetch a compact PubChem summary and description for a single CID."""
  #  async with httpx.AsyncClient(timeout=10) as client:
   #     try:
            # 1. Получаем свойства
        #    props = await _fetch_props(cid, client)
            
            # 2. Получаем текстовое описание (дескрипшн)
          #  desc_url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/description/JSON"
          #  desc_res = await client.get(desc_url)
          #  description = "No description available"
            
           # if desc_res.status_code == 200:
           #     desc_data = desc_res.json()
           #     # Извлекаем первый доступный текст описания
            #    annotations = desc_data.get("InformationList", {}).get("Information", [])
            #    for info in annotations:
                 #   if "Description" in info:
                   #     description = info["Description"]
                    #    break

           # return json.dumps({
            #    "ok": True,
           #     "cid": cid,
          #      "compound": props,
           #     "description": description
          #  }, ensure_ascii=False)
    #   except AppError as e:
        # Ловим наши "красивые" ошибки (например, 404)
      #  return json.dumps(_error_payload(e), ensure_ascii=False)
        
 #   except Exception as e:
  #      # Ловим всё остальное (сломался код, упала сеть)
   #     return json.dumps(_unexpected_error_payload(e), ensure_ascii=False)

#tool 7
#t@mcp.tool()
#async def search_by_synonym_pubchem(synonym: str, limit: int = 5) -> str:
  # """Search PubChem compounds by synonym or alternative name."""
  #  # В PubChem поиск по имени и по синониму часто идет через один и тот же эндпоинт name
    # Но мы можем явно пометить это для агента как поиск синонимов
   # return await search_by_name_pubchem(name=synonym, limit=limit)

if __name__ == "__main__":#запуск цикла событий
    mcp.run(transport="stdio")