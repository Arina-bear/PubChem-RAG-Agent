from mcp.server.fastmcp import FastMCP
import requests
import urllib.parse
from typing import Any
import httpx
import json
import asyncio

from app.errors.models import AppError, ErrorCode

from app.schemas.schemas import (SearchByNameInput,SearchBySMILESInput,SearchByFormulaInput,SearchByMassRangeArgs
                                 ,SearchByInChIKeyArgs)

"Создание mcp-сервера"""
#общий счетчик
global_sem = asyncio.Semaphore(1)
mcp = FastMCP("pubchem-tools")

import asyncio
import httpx
import urllib.parse
import json
from typing import Any

async def _fetch_props(cid: int, client: httpx.AsyncClient) -> dict:
    """Безопасно запрашивает свойства вещества. При ошибке возвращает базовую инфо."""
    prop_url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/property/MolecularFormula,MolecularWeight,Title/JSON"
    
    try:
        async with global_sem:
            response = await client.get(prop_url, timeout=5.0)
            await asyncio.sleep(0.1)
        
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

async def _perform_search(client: httpx.AsyncClient, url: str, query_val: str, limit: int) -> dict:
    """Общая логика поиска CID и сбора свойств для всех инструментов."""
    try:
        async with global_sem:
            response = await client.get(url, timeout=10.0)
            await asyncio.sleep(0.1)
        if response.status_code != 200:
            return {
                "ok": False, 
                "message": f"Запрос '{query_val}' не дал результатов в базе PubChem.", 
                "matches": []
            }

        data = response.json()
        cid_list = data.get('IdentifierList', {}).get('CID', [])[:limit]
        
        if not cid_list:
            return {"ok": False, "message": "Список идентификаторов пуст.", "matches": []}
        
        # Запускаем сбор свойств. return_exceptions=True гарантирует, что gather не выкинет Exception
        tasks = [_fetch_props(cid, client) for cid in cid_list]
        results_raw = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Очищаем результаты от возможных объектов исключений
        matches = [res for res in results_raw if isinstance(res, dict)]
        
        return {
            "ok": True if matches else False,
            "query": query_val,
            "matches": matches,
            "count": len(matches)
        }

    except Exception as e:
        # Ловим только критические ошибки (например, полный разрыв соединения)
        return {
            "ok": False, 
            "message": f"Сетевая ошибка при обращении к PubChem: {str(e)}", 
            "matches": []
        }

# --- TOOLS ---

@mcp.tool(name="search_compound_by_name")
async def search_compound_by_name(name: str, limit: int = 5) -> dict:
    clean_name = name.replace(" ", "").strip()
    args = SearchByNameInput(name=clean_name, limit=limit)
    async with httpx.AsyncClient(timeout=15) as client:
        encoded_name = urllib.parse.quote(args.name)
        url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{encoded_name}/cids/JSON"
        return await _perform_search(client, url, args.name, args.limit)


@mcp.tool(name="search_compound_by_smiles")
async def search_compound_by_smiles(smiles: str, limit: int = 5) -> dict:
    clean_smiles = smiles.replace(" ", "").strip()
    args = SearchBySMILESInput(smiles=clean_smiles, limit=limit)
    async with httpx.AsyncClient(timeout=15) as client:
        encoded_smiles = urllib.parse.quote(args.smiles)
        url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/smiles/{encoded_smiles}/cids/JSON"
        return await _perform_search(client, url, args.smiles, args.limit)


@mcp.tool(name="search_compound_by_formula")
async def search_compound_by_formula(formula: str, limit: int = 5) -> dict:
    clean_formula = formula.replace(" ", "").strip()
    args = SearchByFormulaInput(formula=clean_formula, limit=limit)
    async with httpx.AsyncClient(timeout=15) as client:
        encoded_formula = urllib.parse.quote(args.formula)
        url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/fastformula/{encoded_formula}/cids/JSON"
        return await _perform_search(client, url, args.formula, args.limit)


@mcp.tool(name="search_compound_by_inchikey")
async def search_compound_by_inchikey(inchikey: str, limit: int = 5) -> dict:
    clean_inchikey = inchikey.replace(" ", "").strip()
    args = SearchByInChIKeyArgs(inchikey=clean_inchikey, limit=limit)
    async with httpx.AsyncClient(timeout=15) as client:
        encoded_inchikey = urllib.parse.quote(args.inchikey)
        url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/inchikey/{encoded_inchikey}/cids/JSON"
        return await _perform_search(client, url, args.inchikey, args.limit)
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