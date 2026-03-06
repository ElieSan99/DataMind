import json
import os
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, ToolMessage
from dotenv import load_dotenv
from tools.cohort_tools import get_cohort_retention, get_rfm_segments, get_churn_rate

load_dotenv("../.env")
LLM_MODEL = os.getenv('LLM_MODEL')

class CohortAgent:
    SYSTEM = """Tu es un analyste de rétention client expert sur le dataset Olist brésilien.
Tu analyses cohortes mensuelles, segmentation RFM et taux de churn.
Utilise les outils pour récupérer les données réelles.
Retourne UNIQUEMENT un JSON : {"agent":"cohort","data":{...},"summary":"..."}"""

    def __init__(self):
        self.llm   = ChatGroq(model=LLM_MODEL, temperature=0)
        self.tools = {t.name: t for t in [get_cohort_retention, get_rfm_segments, get_churn_rate]}
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
            return {"agent":"cohort","data":{},"summary":final.content}