// MCP routes for Hono
// Simplified provider-agnostic version from Spotify MCP

import { randomUUID } from 'node:crypto';
import type { HttpBindings } from '@hono/node-server';
import type { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StreamableHTTPServerTransport } from '@modelcontextprotocol/sdk/server/streamableHttp.js';
import { toFetchResponse, toReqRes } from 'fetch-to-node';
import { Hono } from 'hono';
import { config } from '../../config/env.js';
import { authContextStorage, contextRegistry } from '../../core/context.js';
import { getSessionStore } from '../../shared/storage/singleton.js';
import type { RequestContext } from '../../shared/types/context.js';
import { createCancellationToken } from '../../shared/utils/cancellation.js';
import { logger } from '../../shared/utils/logger.js';
import type { AuthContext } from '../middlewares/auth.js';

/**
 * Hono context with auth middleware extension.
 */
interface HonoContextWithAuth {
  authContext?: AuthContext;
}

type JsonRpcLike = {
  method?: string;
  params?: Record<string, unknown>;
};

function getJsonRpcMessages(body: unknown): JsonRpcLike[] {
  if (!body || typeof body !== 'object') return [];
  if (Array.isArray(body)) {
    return body.filter((msg) => msg && typeof msg === 'object') as JsonRpcLike[];
  }
  return [body as JsonRpcLike];
}

function resolveSessionApiKey(authContext?: AuthContext): string {
  const headers = authContext?.authHeaders ?? {};
  const apiKeyHeader = config.API_KEY_HEADER.toLowerCase();

  const directApiKey =
    headers[apiKeyHeader] ?? headers['x-api-key'] ?? headers['x-auth-token'];
  if (directApiKey) return directApiKey;

  if (authContext?.rsToken) return authContext.rsToken;

  const authHeader = headers.authorization;
  if (authHeader) {
    const match = authHeader.match(/^\s*Bearer\s+(.+)$/i);
    return match?.[1] ?? authHeader;
  }

  if (config.API_KEY) return config.API_KEY;

  return 'public';
}

export function buildMcpRoutes(params: {
  server: McpServer;
  transports: Map<string, StreamableHTTPServerTransport>;
}) {
  const { server, transports } = params;
  const app = new Hono<{ Bindings: HttpBindings }>();
  const sessionStore = getSessionStore();

  // Track which transports have been connected to avoid duplicate connect() calls
  const connectedTransports = new WeakSet<StreamableHTTPServerTransport>();

  const MCP_SESSION_HEADER = 'Mcp-Session-Id';

  /**
   * Connect transport to server only if not already connected.
   * McpServer.connect() should be called once per transport lifecycle.
   */
  async function ensureConnected(
    transport: StreamableHTTPServerTransport,
  ): Promise<void> {
    if (!connectedTransports.has(transport)) {
      await server.connect(transport);
      connectedTransports.add(transport);
    }
  }

  app.post('/', async (c) => {
    const { req, res } = toReqRes(c.req.raw);
    let requestId: string | number | undefined;

    try {
      const sessionIdHeader = c.req.header(MCP_SESSION_HEADER) ?? undefined;
      let body: unknown;
      try {
        body = await c.req.json();
      } catch {
        body = undefined;
      }

      const messages = getJsonRpcMessages(body);
      const isInitialize = messages.some((msg) => msg.method === 'initialize');
      const isInitialized = messages.some((msg) => msg.method === 'initialized');
      const initMessage = messages.find((msg) => msg.method === 'initialize');
      const protocolVersion =
        typeof (initMessage?.params as { protocolVersion?: string } | undefined)
          ?.protocolVersion === 'string'
          ? (initMessage?.params as { protocolVersion?: string }).protocolVersion
          : undefined;

      if (!isInitialize && !sessionIdHeader) {
        return c.json(
          {
            jsonrpc: '2.0',
            error: { code: -32000, message: 'Bad Request: Mcp-Session-Id required' },
            id: null,
          },
          400,
        );
      }

      // Server always generates session ID on initialize (per MCP spec)
      // Ignore client-provided session ID to prevent session fixation
      const plannedSid = isInitialize ? randomUUID() : undefined;
      const sessionId = plannedSid ?? sessionIdHeader;

      const authContext = (c as unknown as HonoContextWithAuth).authContext;
      const apiKey = resolveSessionApiKey(authContext);

      let existingSession: Awaited<ReturnType<typeof sessionStore.get>> | null = null;
      if (!isInitialize && sessionIdHeader) {
        try {
          existingSession = await sessionStore.get(sessionIdHeader);
        } catch (error) {
          void logger.warning('mcp_session', {
            message: 'Session lookup failed',
            error: (error as Error).message,
          });
        }
        if (!existingSession) {
          const staleTransport = transports.get(sessionIdHeader);
          if (staleTransport) {
            transports.delete(sessionIdHeader);
            staleTransport.close();
          }
          return c.text('Invalid session', 404);
        }
      }

      // Warn if API key changed but don't reject - allows legitimate re-auth scenarios
      // Session stays bound to original API key for limit enforcement
      if (sessionId && !isInitialize && existingSession?.apiKey && existingSession.apiKey !== apiKey) {
        void logger.warning('mcp_session', {
          message: 'Request API key differs from session binding',
          sessionId,
          originalApiKey: existingSession.apiKey.slice(0, 8) + '...',
          requestApiKey: apiKey.slice(0, 8) + '...',
        });
      }

      if (sessionId && isInitialized) {
        try {
          await sessionStore.update(sessionId, { initialized: true });
        } catch (error) {
          void logger.warning('mcp_session', {
            message: 'Failed to update session initialized flag',
            error: (error as Error).message,
          });
        }
      }

      void logger.info('mcp_request', {
        message: 'Processing MCP request',
        sessionId,
        isInitialize,
        hasSessionIdHeader: !!sessionIdHeader,
        hasAuthorizationHeader: !!req.headers.authorization,
        requestMethod: req.method,
        bodyMethod: messages[0]?.method,
      });

      let transport = sessionIdHeader ? transports.get(sessionIdHeader) : undefined;
      if (!transport) {
        if (!isInitialize) {
          if (sessionIdHeader) {
            void sessionStore.delete(sessionIdHeader).catch(() => {});
          }
          return c.text('Invalid session', 404);
        }
        const created = new StreamableHTTPServerTransport({
          sessionIdGenerator: () => sessionId as string,
          onsessioninitialized: async (sid: string) => {
            transports.set(sid, created);
            // Create session record AFTER SDK accepts initialize (prevents orphans)
            try {
              await sessionStore.create(sid, apiKey);
              if (protocolVersion) {
                await sessionStore.update(sid, { protocolVersion });
              }
            } catch (error) {
              void logger.warning('mcp_session', {
                message: 'Failed to create session record',
                error: (error as Error).message,
              });
            }
            void logger.info('mcp', {
              message: 'Session initialized',
              sessionId: sid,
            });
          },
          onsessionclosed: (sid: string) => {
            transports.delete(sid);
            void sessionStore.delete(sid).catch(() => {});
            contextRegistry.deleteBySession(sid);
          },
        });
        transport = created;
      }

      transport.onerror = (error) => {
        void logger.error('transport', {
          message: 'Transport error',
          error: error.message,
        });
      };

      // Extract requestId from body if present
      requestId =
        body && typeof body === 'object' && 'id' in body
          ? (body.id as string | number)
          : undefined;

      // Create request context (used by both registry and AsyncLocalStorage)
      const requestContext: RequestContext = {
        sessionId: plannedSid ?? sessionIdHeader,
        cancellationToken: createCancellationToken(),
        requestId,
        timestamp: Date.now(),
        authStrategy: authContext?.strategy,
        authHeaders: authContext?.authHeaders,
        resolvedHeaders: authContext?.resolvedHeaders,
        providerToken: authContext?.providerToken,
        provider: authContext?.provider,
        rsToken: authContext?.rsToken,
      };

      // Store in registry for legacy lookup by requestId
      if (requestId) {
        contextRegistry.create(requestId, plannedSid ?? sessionIdHeader, {
          authStrategy: authContext?.strategy,
          authHeaders: authContext?.authHeaders,
          resolvedHeaders: authContext?.resolvedHeaders,
          providerToken: authContext?.providerToken,
          provider: authContext?.provider,
          rsToken: authContext?.rsToken,
        });
      }

      await ensureConnected(transport);

      // Run transport handling within AsyncLocalStorage context
      // This makes auth context available to tool handlers via getCurrentAuthContext()
      await authContextStorage.run(requestContext, async () => {
        await transport.handleRequest(req, res, body);
      });

      // Event-driven cleanup: delete context when response closes
      res.on('close', () => {
        if (requestId !== undefined) {
          contextRegistry.delete(requestId);
          void logger.debug('mcp', {
            message: 'Request context cleaned up',
            requestId,
          });
        }
      });

      return toFetchResponse(res);
    } catch (error) {
      // Cleanup on error as well
      if (requestId !== undefined) {
        contextRegistry.delete(requestId);
      }
      void logger.error('mcp', {
        message: 'Error handling POST request',
        error: (error as Error).message,
      });
      return c.json(
        {
          jsonrpc: '2.0',
          error: { code: -32603, message: 'Internal server error' },
          id: null,
        },
        500,
      );
    }
  });

  app.get('/', async (c) => {
    const { req, res } = toReqRes(c.req.raw);
    const sessionIdHeader = c.req.header(MCP_SESSION_HEADER);
    if (!sessionIdHeader) {
      return c.json(
        {
          jsonrpc: '2.0',
          error: { code: -32000, message: 'Method not allowed - no session' },
          id: null,
        },
        405,
      );
    }
    try {
      let sessionRecord: Awaited<ReturnType<typeof sessionStore.get>> | null = null;
      try {
        sessionRecord = await sessionStore.get(sessionIdHeader);
      } catch (error) {
        void logger.warning('mcp_session', {
          message: 'Session lookup failed',
          error: (error as Error).message,
        });
      }
      if (!sessionRecord) {
        const staleTransport = transports.get(sessionIdHeader);
        if (staleTransport) {
          transports.delete(sessionIdHeader);
          staleTransport.close();
        }
        return c.text('Invalid session', 404);
      }

      const transport = transports.get(sessionIdHeader);
      if (!transport) {
        return c.text('Invalid session', 404);
      }
      await ensureConnected(transport);
      await transport.handleRequest(req, res);
      return toFetchResponse(res);
    } catch (error) {
      void logger.error('mcp', {
        message: 'Error handling GET request',
        error: (error as Error).message,
      });
      return c.json(
        {
          jsonrpc: '2.0',
          error: { code: -32603, message: 'Internal server error' },
          id: null,
        },
        500,
      );
    }
  });

  app.delete('/', async (c) => {
    const { req, res } = toReqRes(c.req.raw);
    const sessionIdHeader = c.req.header(MCP_SESSION_HEADER);
    if (!sessionIdHeader) {
      return c.json(
        {
          jsonrpc: '2.0',
          error: { code: -32000, message: 'Method not allowed - no session' },
          id: null,
        },
        405,
      );
    }
    try {
      let sessionRecord: Awaited<ReturnType<typeof sessionStore.get>> | null = null;
      try {
        sessionRecord = await sessionStore.get(sessionIdHeader);
      } catch (error) {
        void logger.warning('mcp_session', {
          message: 'Session lookup failed',
          error: (error as Error).message,
        });
      }
      if (!sessionRecord) {
        const staleTransport = transports.get(sessionIdHeader);
        if (staleTransport) {
          transports.delete(sessionIdHeader);
          staleTransport.close();
        }
        return c.text('Invalid session', 404);
      }

      const transport = transports.get(sessionIdHeader);
      if (!transport) {
        return c.text('Invalid session', 404);
      }
      await ensureConnected(transport);
      await transport.handleRequest(req, res);

      // Clean up all contexts for this session before closing
      const cleanedCount = contextRegistry.deleteBySession(sessionIdHeader);
      void logger.info('mcp', {
        message: 'Session terminated, contexts cleaned up',
        sessionId: sessionIdHeader,
        cleanedContexts: cleanedCount,
      });

      transports.delete(sessionIdHeader);
      transport.close();
      await sessionStore.delete(sessionIdHeader).catch(() => {});
      return toFetchResponse(res);
    } catch (error) {
      void logger.error('mcp', {
        message: 'Error handling DELETE request',
        error: (error as Error).message,
      });
      return c.json(
        {
          jsonrpc: '2.0',
          error: { code: -32603, message: 'Internal server error' },
          id: null,
        },
        500,
      );
    }
  });

  return app;
}
