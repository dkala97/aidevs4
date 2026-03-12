import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { SetLevelRequestSchema } from '@modelcontextprotocol/sdk/types.js';
import { config } from '../config/env.js';
import { getLowLevelServer } from '../shared/mcp/server-internals.js';
import { registerPrompts } from '../shared/prompts/index.js';
import { registerResources } from '../shared/resources/index.js';
import { type ContextResolver, registerTools } from '../shared/tools/registry.js';
import { logger } from '../shared/utils/logger.js';
import { buildCapabilities } from './capabilities.js';

export interface ServerOptions {
  name: string;
  version: string;
  instructions?: string;
  /**
   * Called when initialization is complete (after client sends notifications/initialized).
   * Per review finding #3: This fires AFTER transport.onsessioninitialized.
   *
   * Guaranteed ordering:
   * 1. transport.onsessioninitialized(sid) - session ID assigned
   * 2. server.oninitialized() - client confirmed ready
   *
   * At this point, you can safely:
   * - Access client capabilities via server.server.getClientCapabilities()
   * - Send server→client requests (sampling, elicitation, roots)
   */
  oninitialized?: () => void;
  /**
   * Optional resolver to look up auth context by requestId.
   * Required for tools to receive authentication data.
   */
  contextResolver?: ContextResolver;
}

export function buildServer(options: ServerOptions): McpServer {
  const { name, version, instructions, oninitialized, contextResolver } = options;

  const server = new McpServer(
    { name, version },
    {
      capabilities: buildCapabilities(),
      instructions: instructions ?? config.MCP_INSTRUCTIONS,
    },
  );

  // Register oninitialized callback
  // Per review finding #3: This fires after onsessioninitialized
  const lowLevel = getLowLevelServer(server);
  if (oninitialized) {
    lowLevel.oninitialized = () => {
      logger.info('mcp', {
        message: 'Client initialization complete (notifications/initialized received)',
        clientVersion: lowLevel.getClientVersion?.(),
      });
      oninitialized();
    };
  }

  // Register handlers with context resolver for auth data
  registerTools(server, contextResolver);
  registerPrompts(server);
  registerResources(server);

  // Register logging/setLevel handler (required when logging capability is advertised)
  server.server.setRequestHandler(SetLevelRequestSchema, async (request) => {
    const level = request.params.level;
    logger.info('mcp', { message: 'Log level changed', level });
    return {};
  });

  return server;
}
