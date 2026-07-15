import asyncio
from drivers.drivers_graph.graph import create_graph
from drivers.drivers_graph.state import AttributionState

async def run(ticker="AAPL", date="2024-11-01"):
    graph = create_graph()
    state = AttributionState(company_ticker=ticker, target_date=date, events=[], result={})
    result = await graph.ainvoke(state)
    return result["result"]

if __name__ == "__main__":
    print(asyncio.run(run()))