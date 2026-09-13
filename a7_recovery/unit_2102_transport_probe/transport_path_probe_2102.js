export const meta = {
  name: 'a7-transport-path-probe-2102',
  description: 'Zero-agent probe: can Workflow execute a script at a recovery path',
}

// Nothing else may live here. No agent(), no phase(), no tool, no read, no
// network, no subprocess, no write, no A7 input. The ONLY question this asks
// is whether the platform read and ran this file at the path it was given.
// A returned object proves it did; a refusal naming the path proves it did not.
return {
  probe: 'a7_transport_path_2102',
  asks: 'did the platform read and execute this file at its recovery path',
  agents: 0,
  model_calls: 0,
}
