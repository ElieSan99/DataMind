import json
import os
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, ToolMessage
from dotenv import load_dotenv
from tools.chart_tools import create_line_chart, create_bar_chart, create_heatmap

load_dotenv("../.env")
LLM_MODEL = os.getenv('LLM_MODEL')

class ChartAgent:
    SYSTEM = """Tu es un spécialiste de la visualisation de données e-commerce.
Tu reçois des données JSON et génères des graphiques Plotly adaptés.
- line chart : tendances temporelles (CA par mois)
- bar chart  : classements (top produits, top états)
- heatmap    : matrices de cohortes
Retourne UNIQUEMENT un JSON : {"agent":"chart","chart_type":"...","plotly_json":"..."}"""

    def __init__(self):
        self.llm   = ChatGroq(model=LLM_MODEL, temperature=0)
        self.tools = {t.name: t for t in [create_line_chart, create_bar_chart, create_heatmap]}
        self.llm_with_tools = self.llm.bind_tools(list(self.tools.values()))

    async def ainvoke(self, data_json: str, chart_type: str, title: str) -> dict:
        prompt = f"{self.SYSTEM}\n\nDonnées: {data_json}\nType souhaité: {chart_type}\nTitre: {title}"
        messages = [HumanMessage(content=prompt)]
        response = await self.llm_with_tools.ainvoke(messages)
        messages.append(response)

        for tc in response.tool_calls:
            result = self.tools[tc["name"]].invoke(tc["args"])
            messages.append(ToolMessage(content=json.dumps(result), tool_call_id=tc["id"]))

        final = await self.llm.ainvoke(messages)
        try:
            text = final.content.strip()
            if "```" in text: text = text.split("```")[1].replace("json","").strip()
            return json.loads(text)
        except:
            return {"agent":"chart","chart_type":chart_type,"plotly_json":"{}"}