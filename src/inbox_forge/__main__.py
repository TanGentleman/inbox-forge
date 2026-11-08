import sys

from inbox_forge.cli import ingest, search

COMMANDS = {'ingest': ingest.main, 'search': search.main}
USAGE = """usage: inbox-forge {ingest,search} ...

  ingest FOLDER   Import .eml files from FOLDER into the data directory
  search QUERY    Search imported emails

Run 'inbox-forge <command> --help' for options."""


def main() -> None:
    args = sys.argv[1:]
    if not args or args[0] not in COMMANDS:
        print(USAGE)
        sys.exit(0 if args and args[0] in ('-h', '--help') else 2)
    COMMANDS[args[0]](args[1:])


if __name__ == '__main__':
    main()
