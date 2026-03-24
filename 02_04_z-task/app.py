#!/usr/bin/env python3

import sys

from src.config import (
    PROJECT_ROOT,
    ENV_PATH,
    INSTRUCTIONS,
    HUB_API_KEY
)

from generic_agent.config import AgentConfig
import generic_agent.app as generic_agent
from src.native_tools import TaskNativeToolsFactory

def main():
    """Main entry point for the failure log analysis agent."""

    if not HUB_API_KEY:
        print("Error: HUB_API_KEY not found in environment. Please set it in .env file.")
        return 1

    # Create agent configuration
    config = AgentConfig(
        dotenv_path=str(ENV_PATH),
        project_root=PROJECT_ROOT,
        instructions=INSTRUCTIONS
    )

    # Create argument parser with custom description
    parser = generic_agent.app_setup_arg_parser(
        app_description="MailBox Search tool"
    )
    args = parser.parse_args()

    # Create native tools factory for this task
    native_tools_factory = TaskNativeToolsFactory()

    # Run the generic agent with config, args, and native tools
    return generic_agent.app_main(config, args, native_tools_factory)


if __name__ == "__main__":
    sys.exit(main())
