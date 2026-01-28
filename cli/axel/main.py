import argparse
import os
import json
import requests

# This is a placeholder for the actual backend URL, normally read from a config file.
# For now, it will be hardcoded, matching the example in axel-desing.md
BACKEND_URL = os.getenv("AXEL_BACKEND_URL", "https://axel-xxxx.a.run.app")

def chat_command(args):
    """Handles the 'axel chat' command."""
    print("Axel chat command initiated.")
    # In a real implementation, you'd read from stdin, files, etc.
    # For this placeholder, we'll use a fixed example.
    messages = [
        {"role": "system", "content": "You are Axel, a coding assistant..."},
        {"role": "user", "content": "Explain this code:\ndef add(a, b):\n    return a + b\n"}
    ]
    options = {
        "temperature": args.temperature,
        "max_tokens": args.max_tokens,
    }

    payload = {
        "messages": messages,
        "options": options
    }

    print(f"\nSending to {BACKEND_URL}/chat:")
    print(json.dumps(payload, indent=2))

    try:
        response = requests.post(f"{BACKEND_URL}/chat", json=payload)
        response.raise_for_status()  # Raise an exception for HTTP errors
        print("\nResponse from backend:")
        print(json.dumps(response.json(), indent=2))
    except requests.exceptions.RequestException as e:
        print(f"\nError communicating with backend: {e}")
        if e.response:
            print(f"Response status: {e.response.status_code}")
            print(f"Response content: {e.response.text}")


def fim_command(args):
    """Handles the 'axel fim' command."""
    print("Axel fim command initiated.")
    prompt = args.prompt
    suffix = args.suffix
    options = {
        "temperature": args.temperature,
        "max_tokens": args.max_tokens,
    }

    payload = {
        "prompt": prompt,
        "suffix": suffix,
        "options": options
    }

    print(f"\nSending to {BACKEND_URL}/fim:")
    print(json.dumps(payload, indent=2))

    try:
        response = requests.post(f"{BACKEND_URL}/fim", json=payload)
        response.raise_for_status()  # Raise an exception for HTTP errors
        print("\nResponse from backend:")
        print(json.dumps(response.json(), indent=2))
    except requests.exceptions.RequestException as e:
        print(f"\nError communicating with backend: {e}")
        if e.response:
            print(f"Response status: {e.response.status_code}")
            print(f"Response content: {e.response.text}")


def main():
    global BACKEND_URL
    parser = argparse.ArgumentParser(
        description="Axel CLI for coding assistance.",
        formatter_class=argparse.RawTextHelpFormatter
    )

    # Global options
    parser.add_argument("--backend-url", type=str, default=BACKEND_URL,
                        help=f"URL of the Axel backend. Defaults to {BACKEND_URL}")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Chat command
    chat_parser = subparsers.add_parser("chat", help="Engage in a coding chat with Axel.")
    chat_parser.add_argument("--temperature", type=float, default=0.2,
                             help="Sampling temperature for model output.")
    chat_parser.add_argument("--max-tokens", type=int, default=512,
                             help="Maximum number of tokens to generate.")
    chat_parser.set_defaults(func=chat_command)

    # FIM command
    fim_parser = subparsers.add_parser("fim", help="Perform fill-in-the-middle completion.")
    fim_parser.add_argument("--prompt", type=str, required=True,
                            help="The code before the cursor (prompt for FIM).")
    fim_parser.add_argument("--suffix", type=str, required=True,
                            help="The code after the cursor (suffix for FIM).")
    fim_parser.add_argument("--temperature", type=float, default=0.2,
                             help="Sampling temperature for model output.")
    fim_parser.add_argument("--max-tokens", type=int, default=512,
                             help="Maximum number of tokens to generate.")
    fim_parser.set_defaults(func=fim_command)

    args = parser.parse_args()

    if args.command:
        # Update BACKEND_URL if provided by the user
        if args.backend_url:
            BACKEND_URL = args.backend_url
        args.func(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
