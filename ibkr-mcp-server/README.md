# IBKR MCP Server

A FastAPI application that provides an MCP (Model Context Protocol) server for Interactive Brokers (IBKR) trading operations. The server automatically manages an IBKR Gateway Docker container and exposes trading functionality through both REST API and MCP endpoints.

## Features

- **Trading Operations**: Supports market data, positions, contracts, and scanners
- **Health Monitoring**: Health checks, restarts gateways when no market data
- **Docker Management**: IBKR Gateway container lifecycle (optional)

## Usage

### Helm (Kubernetes)

Install directly from this Git repository:

```bash
# Install from main branch
helm install ibkr-mcp-server git+https://github.com/your-username/ibkr-mcp-server@main?path=chart

# Install from a specific release
helm install ibkr-mcp-server git+https://github.com/your-username/ibkr-mcp-server@v1.0.0?path=chart
```

### Docker Compose

```bash
export IBKR_IB_GATEWAY_USERNAME="YOUR USERNAME"
export IBKR_IB_GATEWAY_PASSWORD="YOUR PASSWORD"
docker-compose up -d --build
```


### Development

1. **Clone and setup:**
   ```bash
   git clone <repository-url>
   cd ibkr-mcp-server
   ```

2. **Install dependencies:**
   ```bash
   uv sync
   ```

3. **Run the server:**
   ```bash
   python main.py --ib-gateway-username=$YOUR_USERNAME --ib-gateway-password=$YOUR_PASSWORD
   ```

The server will start on `http://localhost:8000` with API docs at `/docs`. MCP server will be available at `http://localhost:8000/mcp`.

## API Endpoints

### Gateway Management
These are not exposed to MCP by default
- `GET /gateway/status` - Gateway health and status
- `GET /gateway/logs` - Container logs

### IBKR Operations
- `GET /ibkr/positions` - Current positions
- `GET /ibkr/contract_details` - Contract information for a symbol
- `GET /ibkr/options_chain` - Options chain for underlying contracts
- `GET /ibkr/tickers` - Market data tickers for contract IDs
- `GET /ibkr/filtered_options_chain` - Filtered options chain with market data criteria
- `GET /ibkr/scanner/instrument_codes` - Available scanner instrument codes
- `GET /ibkr/scanner/location_codes` - Available scanner location codes
- `GET /ibkr/scanner/filter_codes` - Available scanner filter codes
- `GET /ibkr/scanner/results` - Scanner results with specified parameters

## Troubleshooting

- **Docker issues**: Ensure Docker daemon is running
- **Port conflicts**: Check if port 8000 is available
- **IBKR connection**: Verify credentials and TWS/Gateway setup

## License

MIT License
