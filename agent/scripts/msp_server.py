from mcp.server.fastmcp import FastMCP
import requests
import urllib.parse
import logging
#from schemas import (SearchByNameInput, SearchBySMILESInput, SearchByFormulaInput)
from langchain.callbacks import get_callback_manager
import json

"Создание mcp-сервера"""
mcp = FastMCP("pubchem-tools")

@mcp.tool()
def search_by_name_pubchem(name: str, limit: int = 5) -> str:
    """Search for compound by name in PubChem"""
    
    try:
        encoded_name = urllib.parse.quote(name)
        url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{encoded_name}/cids/JSON"
        response = requests.get(url, timeout=10)
        
        if response.status_code != 200:
            error_result = {
                "error": True,
                "message": f"Compound '{name}' not found",
                "error_type": "not_found",
                "status_code": response.status_code,
                "results": []
            }
            return json.dumps(error_result, ensure_ascii=False)
        
        try:
            data = response.json()
        except json.JSONDecodeError:
            error_result = {
                "error": True,
                "error_type": "invalid_response",
                "message": "PubChem returned invalid JSON response",
                "results": []
            }
            return json.dumps(error_result, ensure_ascii=False)
        
        cid_list = data.get('IdentifierList', {}).get('CID', [])[:limit]
        
        if not cid_list:
            error_result = {
                "error": True,
                "message": f"No compounds found for '{name}'",
                "error_type": "no_results",
                "results": []
            }
            return json.dumps(error_result, ensure_ascii=False)
        
        results = []
        
        for cid in cid_list:
            try:
                prop_url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/property/MolecularFormula,MolecularWeight,Title/JSON"
                prop_resp = requests.get(prop_url, timeout=10)
                
                if prop_resp.status_code == 200:
                    try:
                        prop_data = prop_resp.json()
                        props = prop_data['PropertyTable']['Properties'][0]
                        results.append({
                            "cid": cid,
                            "name": props.get('Title', 'Unknown'),
                            "formula": props.get('MolecularFormula', 'N/A'),
                            "weight": props.get('MolecularWeight', 'N/A')
                        })
                    except (json.JSONDecodeError, KeyError, IndexError) as e:
                        results.append({
                            "cid": cid,
                            "name": "Unknown",
                            "formula": "N/A",
                            "weight": "N/A",
                            "warning": f"Error parsing properties: {str(e)}"
                        })
                else:
                    results.append({
                        "cid": cid,
                        "name": "Unknown",
                        "formula": "N/A",
                        "weight": "N/A",
                        "warning": f"Could not fetch properties (HTTP {prop_resp.status_code})"
                    })
            
            except Exception as e:
                logging.warning(f"Failed to fetch properties for CID {cid}: {e}")
                results.append({
                    "cid": cid,
                    "name": "Unknown",
                    "formula": "N/A",
                    "weight": "N/A",
                    "warning": f"Error: {str(e)}"
                })
                continue
    
        success_result = {
            "error": False,
            "query": name,
            "query_type": "name",
            "results": results,
            "count": len(results)
        }
        return json.dumps(success_result, ensure_ascii=False)
    
    except requests.exceptions.Timeout:
        error_result = {
            "error": True,
            "error_type": "timeout",
            "message": "Request to PubChem timed out. Please try again.",
            "retryable": True,
            "results": []
        }
        return json.dumps(error_result, ensure_ascii=False)
    
    except requests.exceptions.ConnectionError:
        error_result = {
            "error": True,
            "error_type": "connection_error",
            "message": "Could not connect to PubChem. Please check your network.",
            "retryable": True,
            "results": []
        }
        return json.dumps(error_result, ensure_ascii=False)
    
    except Exception as e:
        logging.exception(f"Unexpected error in search_by_name: {e}")
        error_result = {
            "error": True,
            "error_type": "internal_error",
            "message": f"Internal error: {str(e)}",
            "retryable": False,
            "results": []
        }
        return json.dumps(error_result, ensure_ascii=False)


##tool 2

@mcp.tool()
def search_by_smiles_pubchem(smiles: str) -> str:
    """Search for compound by SMILES in PubChem"""
    try:
        encoded_smiles = urllib.parse.quote(smiles)
        url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/smiles/{encoded_smiles}/cids/JSON"
        response = requests.get(url, timeout=10)
        
        if response.status_code != 200:
            error_result = {
                "error": True,
                "message": f"Compound with SMILES '{smiles}' not found",
                "error_type": "not_found",
                "status_code": response.status_code,
                "results": []
            }
            return json.dumps(error_result, ensure_ascii=False)
        
        data = response.json()
        cid_list = data.get('IdentifierList', {}).get('CID', [])

        if not cid_list:
            error_result = {
                "error": True,
                "message": f"No compounds found for SMILES '{smiles}'",
                "error_type": "no_results",
                "results": []
            }
            return json.dumps(error_result, ensure_ascii=False)
        
        # выбор наиболее релевантного CID
        cid = cid_list[0]
        prop_url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/property/MolecularFormula,MolecularWeight,Title/JSON"
        prop_resp = requests.get(prop_url, timeout=10)

        results = []
        
        if prop_resp.status_code == 200:
            prop_data = prop_resp.json()
            props = prop_data['PropertyTable']['Properties'][0]
            results.append({
                "cid": cid,
                "name": props.get('Title', 'Unknown'),
                "formula": props.get('MolecularFormula', 'N/A'),
                "weight": props.get('MolecularWeight', 'N/A')
            })
        else:
            results.append({
                "cid": cid,
                "name": "Unknown",
                "formula": "N/A",
                "weight": "N/A",
                "warning": f"Could not fetch properties (HTTP {prop_resp.status_code})"
            })
        
        success_result = {
            "error": False,
            "query": smiles,
            "query_type": "smiles",
            "results": results,
            "count": len(results)
        }
        return json.dumps(success_result, ensure_ascii=False)
    
    except requests.exceptions.Timeout:
        error_result = {
            "error": True,
            "error_type": "timeout",
            "message": "Request to PubChem timed out. Please try again.",
            "retryable": True,
            "results": []
        }
        return json.dumps(error_result, ensure_ascii=False)
    
    except requests.exceptions.ConnectionError:
        error_result = {
            "error": True,
            "error_type": "connection_error",
            "message": "Could not connect to PubChem. Please check your network.",
            "retryable": True,
            "results": []
        }
        return json.dumps(error_result, ensure_ascii=False)
    
    except Exception as e:
        logging.exception(f"Unexpected error in search_by_smiles: {e}")
        error_result = {
            "error": True,
            "error_type": "internal_error",
            "message": f"Internal error: {str(e)}",
            "retryable": False,
            "results": []
        }
        return json.dumps(error_result, ensure_ascii=False)
  
    
    

#tool 3

@mcp.tool()
def search_by_formula_pubchem(formula: str, limit: int = 5) -> str:
    """Search for compounds by molecular formula"""
    
    try:
        encoded_formula = urllib.parse.quote(formula)
        url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/fastformula/{encoded_formula}/cids/JSON"
        
        response = requests.get(url, timeout=10)
        
        if response.status_code != 200:
            error_result = {
                "error": True,
                "message": f"Formula '{formula}' not found in PubChem",
                "error_type": "not_found",
                "status_code": response.status_code,
                "results": []
            }
            return json.dumps(error_result, ensure_ascii=False)
        
        try:
            data = response.json()
        except json.JSONDecodeError:
            error_result = {
                "error": True,
                "error_type": "invalid_response",
                "message": "PubChem returned invalid JSON response",
                "results": []
            }
            return json.dumps(error_result, ensure_ascii=False)
        
        cid_list = data.get('IdentifierList', {}).get('CID', [])[:limit]
        
        if not cid_list:
            error_result = {
                "error": True,
                "message": f"No compounds found for formula '{formula}'",
                "error_type": "no_results",
                "results": []
            }
            return json.dumps(error_result, ensure_ascii=False)
        
        results = []
        
        for cid in cid_list:
            try:
                prop_url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/property/Title/JSON"
                prop_resp = requests.get(prop_url, timeout=10)
                
                if prop_resp.status_code == 200:
                    try:
                        prop_data = prop_resp.json()
                        name = prop_data['PropertyTable']['Properties'][0].get('Title', 'Unknown')
                        results.append({
                            "cid": cid,
                            "name": name
                        })
                    except (json.JSONDecodeError, KeyError, IndexError) as e:
                        results.append({
                            "cid": cid,
                            "name": "Unknown",
                            "warning": f"Error parsing response: {str(e)}"
                        })
                else:
                    results.append({
                        "cid": cid,
                        "name": "Unknown",
                        "warning": f"Could not fetch name (HTTP {prop_resp.status_code})"
                    })
            
            except Exception as e:
                logging.warning(f"Failed to fetch name for CID {cid}: {e}")
                results.append({
                    "cid": cid,
                    "name": "Unknown",
                    "warning": f"Error: {str(e)}"
                })
                continue
        
        # успех
        success_result = {
            "error": False,
            "query": formula,
            "query_type": "formula",
            "results": results,
            "count": len(results),
            "limit_applied": limit if len(cid_list) == limit else False
        }
        return json.dumps(success_result, ensure_ascii=False)
    
    except requests.exceptions.Timeout:
        error_result = {
            "error": True,
            "error_type": "timeout",
            "message": "Request to PubChem timed out. Please try again.",
            "retryable": True,
            "results": []
        }
        return json.dumps(error_result, ensure_ascii=False)
    
    except requests.exceptions.ConnectionError:
        error_result = {
            "error": True,
            "error_type": "connection_error",
            "message": "Could not connect to PubChem. Please check your network.",
            "retryable": True,
            "results": []
        }
        return json.dumps(error_result, ensure_ascii=False)
    
    except Exception as e:
        logging.exception(f"Unexpected error in search_by_formula: {e}")
        error_result = {
            "error": True,
            "error_type": "internal_error",
            "message": f"Internal error: {str(e)}",
            "retryable": False,
            "results": []
        }
        return json.dumps(error_result, ensure_ascii=False)


if __name__ == "__main__":
    mcp.run(transport="stdio")