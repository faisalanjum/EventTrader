import time
from docling_core.types.doc.document import DoclingDocument
from docling_agent.agents import BackendConfig, DoclingRAGAgent, ModelConfig, create_backend
M="qwen3.8:27b-mtp-q4_K_M"
agent=DoclingRAGAgent(backend=create_backend(BackendConfig(type="ollama",base_url="http://localhost:11434",models=ModelConfig(reasoning=M,writing=M))),tools=[],max_iterations=4,verbose=False)
jobs=[('ex99_full.json',"What was AMD's gross margin in Q4 2022?"),('ex99_full.json',"What revenue did AMD guide for Q1 2023?"),('ex99_full.json',"Why did AMD's Q4 2022 gross margin change versus a year ago?"),('10k_full.json',"What are Abbott's four reportable segments?")]
for f,q in jobs:
    d=DoclingDocument.load_from_json(f); t=time.time()
    r=agent.run_with_trace(task=q, document=d)
    print(f"\n### {f} | {q} ({time.time()-t:.0f}s)\n"+r.output.export_to_markdown()[:700], flush=True)
