import json
import os
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, ToolMessage
from dotenv import load_dotenv
from tools.sales_tools import get_revenue_trend, get_top_products, get_aov_analysis, get_top_products_trend

load_dotenv("../.env")
LLM_MODEL = os.getenv('LLM_MODEL', 'llama-3.3-70b-versatile')

class SalesAgent:
    SYSTEM = """Tu es un analyste des ventes e-commerce expert sur le dataset Olist brésilien.
Tu analyses revenus mensuels, catégories de produits et paniers moyens par région.
Utilise les outils disponibles pour récupérer les données réelles.
Pour les tendances par produit/catégorie, utilise get_top_products_trend.
Retourne UNIQUEMENT un JSON : {"agent":"sales","data":{...},"summary":"..."}"""

    def __init__(self):
        self.llm   = ChatGroq(model=LLM_MODEL, temperature=0)
        self.tools = {t.name: t for t in [get_revenue_trend, get_top_products, get_aov_analysis, get_top_products_trend]}
        self.llm_with_tools = self.llm.bind_tools(list(self.tools.values()))

    async def ainvoke(self, query: str) -> dict:
        messages = [HumanMessage(content=f"{self.SYSTEM}\n\nQuestion: {query}")]
        response = await self.llm_with_tools.ainvoke(messages)
        messages.append(response)

        for tc in response.tool_calls:
            result = self.tools[tc["name"]].invoke(tc["args"])
            messages.append(ToolMessage(content=json.dumps(result), tool_call_id=tc["id"]))

        final = await self.llm.ainvoke(messages)
        try:
            text = final.content.strip()
            if "```" in text:
                text = text.split("```")[1].replace("json","").strip()
            return json.loads(text)
        except:
            return {"agent":"sales","data":{},"summary":final.content}