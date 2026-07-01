import { spawn } from 'child_process';
import readline from 'readline';

const child = spawn('npx', ['-y', '@shinzolabs/gmail-mcp']);
child.stdout.on('data', (data) => {
  console.error('OUT:', data.toString());
});
child.stderr.on('data', (data) => {
  console.error('ERR:', data.toString());
});

// We can send an initialize request
const initReq = {
  jsonrpc: "2.0",
  id: 1,
  method: "initialize",
  params: { protocolVersion: "2024-11-05", capabilities: {}, clientInfo: { name: "test", version: "1" } }
};
child.stdin.write(JSON.stringify(initReq) + '\n');

setTimeout(() => {
  const toolsReq = {
    jsonrpc: "2.0",
    id: 2,
    method: "tools/list",
    params: {}
  };
  child.stdin.write(JSON.stringify(toolsReq) + '\n');
}, 2000);

setTimeout(() => child.kill(), 5000);
