import json, uuid, os
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from langchain_core.messages import HumanMessage
from agents.orchestrator import Orchestrator


app = FastAPI(title="DataMind API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://*.vercel.app"],
    allow_methods=["*"],
    allow_headers=["*"],
)

orchestrator = Orchestrator()
graph = orchestrator.get_graph()


class AnalyzeRequest(BaseModel):
    question: str
    session_id: str = ""


@app.get("/health")
async def health():
    from sqlalchemy import text
    from db.connection import get_engine

    n = get_engine().connect().execute(
        text("SELECT COUNT(*) FROM orders WHERE order_status='delivered'")
    ).scalar()

    return {
        "status": "ok",
        "rows_loaded": n,
        "llm": os.getenv("LLM_MODEL", "unknown"),
    }


@app.post("/api/analyze")
async def analyze(req: AnalyzeRequest):
    if not req.question.strip():
        return {"error": "Question vide"}
    if len(req.question) > 1000:
        return {"error": "Question trop longue (max 1000 caractères)"}

    session_id = req.session_id or str(uuid.uuid4())

    initial_state = {
        "messages": [HumanMessage(content=req.question)],
        "collected_data": {},
        "charts": [],
    }

    async def event_stream():
        #session
        yield f"data: {json.dumps({'type': 'session', 'id': session_id})}\n\n"

        final_answer = None

        try:
            async for event in graph.astream_events(initial_state, version="v2"):
                kind = event.get("event")
                name = event.get("name", "")
                data = event.get("data", {})

                # CAPTURE du résultat final (selon versions langgraph)
                # On tente plusieurs endroits possibles.
                if kind in ("on_chain_end", "on_node_end"):
                    output = data.get("output")

                    if isinstance(output, dict) and output.get("messages"):
                        last_msg = output["messages"][-1]
                        content = getattr(last_msg, "content", None)
                        if content:
                            final_answer = content

                # STREAMING des tokens pour l'orchestrateur
                if kind == "on_chat_model_stream" and name == "ChatGroq":
                    content = data.get("chunk", {}).content
                    if content:
                        yield f"data: {json.dumps({'type': 'token', 'content': content})}\n\n"

                # Indicateur agent "running"
                if kind == "on_tool_start" and name in [
                    "call_sales_analyst",
                    "call_cohort_analyst",
                    "call_chart_generator",
                ]:
                    yield f"data: {json.dumps({'type':'agent','name':name,'status':'running'})}\n\n"

                # tool end
                elif kind == "on_tool_end":
                    output = data.get("output", "")

                    #ChartAgent renvoie {"agent":"chart", "chart_type":..., "plotly_json":...}
                    if isinstance(output, str):
                        try:
                            obj = json.loads(output)
                            if obj.get("agent") == "chart":
                                yield f"data: {json.dumps({'type':'chart','plotly_json': obj.get('plotly_json','{}'), 'chart_type': obj.get('chart_type','')})}\n\n"
                        except:
                            pass

                    if name in [
                        "call_sales_analyst",
                        "call_cohort_analyst",
                        "call_chart_generator",
                    ]:
                        yield f"data: {json.dumps({'type':'agent','name':name,'status':'done'})}\n\n"

            # IMPORTANT : on envoie TOUJOURS un final si on n'a rien eu d'autre (sécurité)
            # Mais si on a déjà streamé des tokens, on peut ne rien envoyer d'autre.
            # Pour la robustesse côté frontend, on envoie 'final' seulement si le content est significatif.
            if final_answer and not final_answer.startswith("(Aucune"):
                # On ne l'envoie que si le frontend n'a pas déjà tout reçu via 'token'
                # Ou alors on l'envoie comme complément de sécurité.
                yield f"data: {json.dumps({'type':'final','content': final_answer})}\n\n"
            else:
                # Fallback
                if not final_answer:
                    yield f"data: {json.dumps({'type':'final','content':'(Aucune réponse finale capturée. Vérifie les events on_chain_end/on_node_end.)'})}\n\n"

            yield "data: [DONE]\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type':'error','message': str(e)})}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")