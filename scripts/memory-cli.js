#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

const root = process.cwd();
const configPath = path.join(root, '.monkeycode/memory/config.json');

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

function ensureFile(filePath) {
  const dir = path.dirname(filePath);
  fs.mkdirSync(dir, { recursive: true });
  if (!fs.existsSync(filePath)) {
    fs.writeFileSync(filePath, '');
  }
}

function appendJsonl(filePath, payload) {
  ensureFile(filePath);
  fs.appendFileSync(filePath, `${JSON.stringify(payload)}\n`, 'utf8');
}

function getLayer(config, layerId) {
  const layer = config.layers.find((item) => item.id === layerId);
  if (!layer) {
    throw new Error(`Unknown layer: ${layerId}`);
  }
  return layer;
}

function makeEvent(op, layer, extra = {}) {
  return {
    id: `${layer.toLowerCase()}-${Date.now()}`,
    ts: new Date().toISOString(),
    op,
    layer,
    ...extra,
  };
}

function usage() {
  console.log('Usage:');
  console.log('  node scripts/memory-cli.js append <L0|L1|L2> <content>');
  console.log('  node scripts/memory-cli.js prune <L0|L1|L2> <targetId> <reason>');
  console.log('  node scripts/memory-cli.js init');
}

function init(config) {
  for (const layer of config.layers) {
    ensureFile(path.join(root, layer.file));
  }
  console.log('memory initialized');
}

function append(config, layerId, content) {
  const layer = getLayer(config, layerId);
  const event = makeEvent('append', layerId, { content });
  appendJsonl(path.join(root, layer.file), event);
  console.log(JSON.stringify(event));
}

function prune(config, layerId, targetId, reason) {
  const layer = getLayer(config, layerId);
  const event = makeEvent('prune', layerId, { targetId, reason });
  appendJsonl(path.join(root, layer.file), event);
  console.log(JSON.stringify(event));
}

function main() {
  const config = readJson(configPath);
  const [, , command, ...args] = process.argv;

  if (!command) {
    usage();
    process.exit(1);
  }

  if (command === 'init') {
    init(config);
    return;
  }

  if (command === 'append') {
    const [layerId, ...contentParts] = args;
    const content = contentParts.join(' ').trim();
    if (!layerId || !content) {
      usage();
      process.exit(1);
    }
    append(config, layerId, content);
    return;
  }

  if (command === 'prune') {
    const [layerId, targetId, ...reasonParts] = args;
    const reason = reasonParts.join(' ').trim();
    if (!layerId || !targetId || !reason) {
      usage();
      process.exit(1);
    }
    prune(config, layerId, targetId, reason);
    return;
  }

  usage();
  process.exit(1);
}

main();
