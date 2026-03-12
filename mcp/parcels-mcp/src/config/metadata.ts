/**
 * Centralized tool metadata for the MCP server.
 *
 * This file contains all tool definitions with rich, LLM-friendly descriptions.
 * Benefits:
 * - Single source of truth for tool metadata
 * - Easy to maintain and update descriptions
 * - Natural language optimized for LLM understanding
 * - Consistent structure across all tools
 */

export interface ToolMetadata {
  name: string;
  title: string;
  description: string;
}

export const toolsMetadata = {
  check_package: {
    name: "check_package",
    title: "Sprawdź status paczki",
    description: `Sprawdź aktualny status i lokalizację paczki na podstawie jej ID.

Używaj tego narzędzia gdy:
- Klient lub operator pyta o status przesyłki
- Potrzebujesz potwierdzić lokalizację paczki przed przekierowaniem
- Chcesz sprawdzić czy paczka dotarła do miejsca docelowego

Zwraca status paczki, aktualną lokalizację oraz dodatkowe metadane z API.`,
  },
  redirect_package: {
    name: "redirect_package",
    title: "Przekieruj paczkę",
    description: `Przekieruj paczkę do nowego miejsca docelowego.

Używaj tego narzędzia gdy:
- Operator chce zmienić miejsce docelowe paczki
- Klient prosi o zmianę adresu dostawy

WAŻNE: Przed wywołaniem tego narzędzia MUSISZ uzyskać od operatora:
1. ID paczki (packageId)
2. Kod docelowego punktu odbioru (destination)
3. Kod zabezpieczający (code) - operator poda go podczas rozmowy

Po wykonaniu zwraca kod potwierdzenia (confirmation), który należy przekazać operatorowi.`,
  },
} as const satisfies Record<string, ToolMetadata>;

/**
 * Type-safe helper to get metadata for a tool.
 * Usage: getToolMetadata('example_api')
 */
export function getToolMetadata(
  toolName: keyof typeof toolsMetadata,
): ToolMetadata {
  return toolsMetadata[toolName];
}

/**
 * Get all registered tool names.
 */
export function getToolNames(): string[] {
  return Object.keys(toolsMetadata);
}

/**
 * Server-level metadata
 */
export const serverMetadata = {
  title: "MCP Server Template",
  instructions:
    "Use the available tools to inspect resources, run API calls, and keep responses concise.",
} as const;
