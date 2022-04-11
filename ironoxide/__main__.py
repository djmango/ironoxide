import sys

# Turn off bytecode generation
sys.dont_write_bytecode = True

import os
import argparse

# Django specific settings
# https://github.com/dancaron/Django-ORM
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ironoxide.settings')
import ironoxide.settings
# import django

# django.setup()

from ironoxide import convert

def cli(args: argparse.Namespace):
    """
    This is the main function that will be called when the script is run.
    """

    if args.convert:
        # path should already be validated
        convert(args.convert)
        # upload and associate with course