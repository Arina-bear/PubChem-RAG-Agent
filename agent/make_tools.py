from langchain.tools import BaseTool
from typing import List, Optional
from tool.tools import (
    SearchCompoundByName,
    SearchCompoundBySMILES,
    SearchCompoundByFormula
)

def make_pubchem_tools() -> List[BaseTool]:
    """
    Создает и возвращает список инструментов для PubChem агента.    
    
    """

    all_tools = [ 
                SearchCompoundByName(),
                SearchCompoundBySMILES(),
                SearchCompoundByFormula()
                ]
    
    return all_tools