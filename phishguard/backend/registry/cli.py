"""
Simple CLI to interact with the local registry.

Examples:
  python cli.py register --name meta_learner --artifact path/to/meta_learner.pkl
  python cli.py list
  python cli.py latest --name meta_learner
"""
import argparse
import os
from .registry import register_model, list_models, get_latest_model_path, get_model_metadata


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest='cmd')

    p_reg = sub.add_parser('register')
    p_reg.add_argument('--name', required=True)
    p_reg.add_argument('--artifact', required=True)
    p_reg.add_argument('--version', required=False)

    p_list = sub.add_parser('list')
    p_list.add_argument('--name', required=False)

    p_latest = sub.add_parser('latest')
    p_latest.add_argument('--name', required=True)

    args = p.parse_args()

    if args.cmd == 'register':
        dest = register_model(args.name, args.artifact, version=args.version)
        print('Registered to', dest)
    elif args.cmd == 'list':
        models = list_models(args.name) if args.name else list_models()
        print(models)
    elif args.cmd == 'latest':
        path = get_latest_model_path(args.name)
        print(path or 'None')
    else:
        p.print_help()

if __name__ == '__main__':
    main()
