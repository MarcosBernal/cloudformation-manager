#!/usr/bin/env python3
import argparse
import logging


CFM_VERSION = '0.0.1'


def validation():
    pass


def deployment():
    pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Deploying CloudFormation stacks through an easy way. Current version: {}'.format(CFM_VERSION))
    parser.add_argument('template_folders', metavar='folder', nargs='+', help='list of template folders that contain the CloudFormation template file (template.yml) and params files (config.yml) to deploy sequentially')
    parser.add_argument('-a', '--ask', action='store_true', help='Flag to ask for applying modifications')
    parser.add_argument('-c', '--condition', dest='condition_name', type=str, help='condition name to overwrite the params of the main template')
    parser.add_argument('-d', '--debug', action='store_true', help='Show debug traces and logs')
    args = parser.parse_args()

    # Configure logger
    logger = logging.Logger(name="cfm-v" + CFM_VERSION, level=logging.DEBUG if args.debug else logging.INFO)
    streamer = logging.StreamHandler()
    streamer.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)s in %(name)s: %(message)s'))
    logger.addHandler(streamer)

    try:
        validation(args)
        deployment(args)
    except Exception as e:
        logging.exception("Deployment has failed due to exception:")
        raise e

    logger.info("Stacks were deployed successfully")
