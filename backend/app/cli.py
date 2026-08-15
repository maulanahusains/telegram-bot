from __future__ import annotations

import argparse
import asyncio
import getpass
import json

from pydantic import SecretStr

from app.core.config import get_settings
from app.core.database import Database
from app.core.module_discovery import discover_modules
from app.core.registry import BotModuleRegistry
from app.platform.bots.schemas import BotUpsert
from app.platform.bots.services import BotConfigService
from app.shared.exceptions import InvalidBotModuleError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="telegram-platform")
    groups = parser.add_subparsers(dest="group", required=True)
    bots = groups.add_parser("bots", help="Manage Telegram bot configurations")
    commands = bots.add_subparsers(dest="command", required=True)

    upsert = commands.add_parser("upsert", help="Create or replace a bot config")
    upsert.add_argument("--name", required=True)
    upsert.add_argument("--module", required=True, dest="module_name")
    upsert.add_argument("--description")
    upsert.add_argument("--disabled", action="store_true")

    commands.add_parser("list", help="List bot configs without credentials")
    toggle = commands.add_parser("enable", help="Enable a bot")
    toggle.add_argument("name")
    toggle = commands.add_parser("disable", help="Disable a bot")
    toggle.add_argument("name")
    return parser


async def run(args: argparse.Namespace) -> None:
    settings = get_settings()
    database = Database(settings)
    service = BotConfigService.from_settings(database, settings)
    try:
        if args.command == "list":
            rows = await service.list_public()
            print(json.dumps([row.model_dump() for row in rows], indent=2))
            return
        if args.command in ("enable", "disable"):
            row = await service.set_enabled(args.name, args.command == "enable")
            print(json.dumps(row.model_dump(), indent=2))
            return
        if args.command == "upsert":
            modules = BotModuleRegistry()
            await discover_modules(modules)
            if args.module_name not in modules.factories:
                raise InvalidBotModuleError(
                    f"Module {args.module_name!r} was not discovered."
                )
            token = SecretStr(getpass.getpass("Telegram bot token: "))
            secret = SecretStr(getpass.getpass("Telegram webhook secret: "))
            row = await service.upsert(
                BotUpsert(
                    name=args.name,
                    module_name=args.module_name,
                    token=token,
                    secret_token=secret,
                    enabled=not args.disabled,
                    description=args.description,
                )
            )
            print(json.dumps(row.model_dump(), indent=2))
    finally:
        await database.dispose()


def main() -> None:
    args = build_parser().parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
