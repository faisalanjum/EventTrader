import time
from docling_core.types.doc.document import DoclingDocument
from docling_agent.agents import BackendConfig, DoclingRAGAgent, ModelConfig, create_backend
M="qwen3.8:27b-mtp-q4_K_M"
d=DoclingDocument.load_from_json('ex99_full.json')
agent=DoclingRAGAgent(backend=create_backend(BackendConfig(type="ollama",base_url="http://localhost:11434",models=ModelConfig(reasoning=M,writing=M))),tools=[],max_iterations=4,verbose=False)
for q in ["What was AMD's gross margin in Q4 2022?","What revenue did AMD guide for Q1 2023?"]:
    t=time.time(); res=agent.run_with_trace(task=q, document=d) if hasattr(agent,'run_with_trace') else agent.run(task=q,document=d)
    out=res[0] if isinstance(res,tuple) else res
    txt=out.export_to_markdown() if hasattr(out,'export_to_markdown') else str(out)
    print(f"\nQ: {q}  ({time.time()-t:.0f}s)\nA: {txt[:600]}")
    if isinstance(res,tuple): print('trace:', str(res[1])[:600])
