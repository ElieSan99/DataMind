import os
import json
from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.tools import tool
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
import langgraph.graph as lg
from dotenv import load_dotenv
from agents.sales_agent import SalesAgent
from agents.cohort_agent import CohortAgent
from agents.chart_agent import ChartAgent

load_dotenv("../.env")
LLM_MODEL = os.getenv('LLM_MODEL', 'llama-3.3-70b-versatile')

class OrchestratorState(TypedDict):
    messages:      Annotated[Sequence[BaseMessage], lg.add_messages]
    collected_data: dict
    charts:        list[dict]

class Orchestrator:
    def __init__(self):
        self.sales   = SalesAgent()
        self.cohort  = CohortAgent()
        self.chart   = ChartAgent()
        self.llm     = ChatGroq(model=LLM_MODEL, temperature=0)
        self._graph  = self._build_graph()

    def _build_tools(self) -> list:
        sales_agent_ref   = self.sales
        cohort_agent_ref  = self.cohort
        chart_agent_ref   = self.chart

        @tool
        async def call_sales_analyst(query: str) -> str:
            """
            Appelle l'agent analyse des ventes.
            Utiliser pour: revenus, tendances CA, top produits, panier moyen (AOV).
            query: question précise sur les ventes.
            """
            result = await sales_agent_ref.ainvoke(query)
            return json.dumps(result)

        @tool
        async def call_cohort_analyst(query: str) -> str:
            """
            Appelle l'agent analyse des cohortes et rétention client.
            Utiliser pour: rétention, cohortes, RFM, churn, fidélisation.
            query: question précise sur les clients.
            """
            result = await cohort_agent_ref.ainvoke(query)
            return json.dumps(result)

        @tool
        async def call_chart_generator(data_json: str, chart_type: str, title: str) -> str:
            """
            Génère un graphique Plotly depuis des données JSON.
            chart_type: 'line', 'bar', ou 'heatmap'.
            data_json: données sérialisées en JSON string.
            title: titre du graphique.
            """
            result = await chart_agent_ref.ainvoke(data_json, chart_type, title)
            return json.dumps(result)

        return [call_sales_analyst, call_cohort_analyst, call_chart_generator]

    def _build_graph(self) -> StateGraph:
        tools = self._build_tools()
        llm_with_tools = self.llm.bind_tools(tools)
        tool_node = ToolNode(tools)

        def orchestrator_node(state: OrchestratorState):
            system = """Tu es un orchestrateur d'analyse e-commerce expert.
Tu coordonnes 3 agents spécialisés.

FLUX DE TRAVAIL CRITIQUE :
1. Question de l'utilisateur -> Appelle call_sales_analyst ou call_cohort_analyst.
2. RÉCUPÈRE les données JSON du résultat de l'agent.
3. Si le résultat contient des données numériques (ventes, tendances, etc.), appelle TOUJOURS call_chart_generator avec ces données.
4. Synthétise le tout dans un rapport final markdown.

RÈGLES D'APPEL :
- Ne génère JAMAIS de graphique toi-même, utilise call_chart_generator.
- Pour call_chart_generator : data_json doit être la string JSON brute reçue de l'agent.
- Chart types: 'line' pour les séries temporelles, 'bar' pour les classements.
"""
            messages = [HumanMessage(content=system)] + list(state["messages"])
            response = llm_with_tools.invoke(messages)
            return {"messages": [response]}

        def should_continue(state: OrchestratorState) -> str:
            last = state["messages"][-1]
            if isinstance(last, AIMessage) and last.tool_calls:
                return "tools"
            return "end"

        graph = StateGraph(OrchestratorState)
        graph.add_node("orchestrator", orchestrator_node)
        graph.add_node("tools", tool_node)
        graph.set_entry_point("orchestrator")
        graph.add_conditional_edges("orchestrator", should_continue, {"tools":"tools","end":END})
        graph.add_edge("tools", "orchestrator")
        return graph.compile()

    def get_graph(self):
        return self._graph