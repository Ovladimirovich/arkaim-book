import argparse
import asyncio
import json
import os

from cli.hermes.client import HermesClient

API_KEY = os.getenv("HERMES_API_KEY", "")


async def do_chat(args):
    client = HermesClient(api_key=API_KEY)
    messages = [{"role": "user", "content": " ".join(args.message)}]
    result = await client.chat(messages, provider=args.provider)
    print(result.get("choices", [{}])[0].get("message", {}).get("content", ""))


async def do_stream(args):
    client = HermesClient(api_key=API_KEY)
    messages = [{"role": "user", "content": " ".join(args.message)}]
    async for token in client.stream(messages, provider=args.provider):
        print(token, end="", flush=True)
    print()


async def do_genome_extract(args):
    from core.genome.extractor import extract_genome

    provider = args.provider or "openrouter"
    genome = await extract_genome(provider_name=provider, max_chapters=args.max_chapters)
    print(json.dumps(genome.model_dump(mode="json"), ensure_ascii=False, indent=2))


def _main():
    parser = argparse.ArgumentParser(prog="hermes")
    sub = parser.add_subparsers(dest="command")

    chat_p = sub.add_parser("chat")
    chat_p.add_argument("message", nargs="+")
    chat_p.add_argument("--provider", default="")

    stream_p = sub.add_parser("stream")
    stream_p.add_argument("message", nargs="+")
    stream_p.add_argument("--provider", default="")

    genome_p = sub.add_parser("genome")
    genome_sub = genome_p.add_subparsers(dest="genome_command")
    extract_p = genome_sub.add_parser("extract")
    extract_p.add_argument("--provider", default="openrouter")
    extract_p.add_argument("--max-chapters", type=int, default=10)

    args = parser.parse_args()
    if args.command == "chat":
        asyncio.run(do_chat(args))
    elif args.command == "stream":
        asyncio.run(do_stream(args))
    elif args.command == "genome" and args.genome_command == "extract":
        asyncio.run(do_genome_extract(args))
    else:
        parser.print_help()


if __name__ == "__main__":
    _main()
