#!/usr/bin/env python3
import os
import sys
import yaml
import boto3
import logging
import argparse
import datetime
import texttable


CFM_VERSION = '1.0.0'


def fetch_cloudformation_exports(cf_client, list_exports_params: dict = {}):
    local_cf_exports = {}
    while True:
        results = cf_client.list_exports(**list_exports_params)
        for export in results['Exports']:
            local_cf_exports[export['Name']] = export['Value']

        if 'NextToken' in results:
            list_exports_params['NextToken'] = results['NextToken']
        else:
            break
    return local_cf_exports

def request_yes_or_no_to_user(text, default_yes: bool = True) -> bool:
    defined_answer = " [Y/n]" if default_yes else " [y/N]"
    while True:
        value = input(text + defined_answer)
        if not value:
            return default_yes
        elif value.lower() == "y":
            return True
        elif value.lower() == "n":
            return False

def request_confirmation(question, yes_default: bool = False):
    valid = {"yes": True, "y": True, "ye": True, "no": False, "n": False}
    prompt = " [Y/n] " if yes_default else " [y/N] "

    while True:
        sys.stdout.write(question + prompt + "\n")
        choice = input().lower()
        if not choice:
            return yes_default
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' (or 'y' or 'n').\n")


def validate_files(absolute_folder_path, logger: logging.Logger):
    template_path = os.path.join(absolute_folder_path, "template.yml")
    config_path = os.path.join(absolute_folder_path, "config.yml")

    if not os.path.isfile(template_path):
        raise Exception("No template file under the path {}".format(template_path))
    if not os.path.isfile(config_path):
        raise Exception("No config file under the path {}".format(config_path))

    with open(template_path, 'r') as _f:
        template_body = _f.read()

    with open(config_path, 'r') as _f:
        config_yml = yaml.safe_load(_f)

    return template_body, config_yml, config_path


def calculate_parameters(config_dict, config_file_path, logger: logging.Logger):
    missing_keys = [compulsory_key for compulsory_key in ["StackName", "RegionName", "Tags"] if compulsory_key not in config_dict.keys()]
    if missing_keys:
        raise Exception("Missing key(s) '{}' in config file {}".format(missing_keys, config_file_path))

    calculated_parameters = {"StackName": config_dict["StackName"]}
    cf = boto3.client("cloudformation", region_name=config_dict["RegionName"])

    if "Parameters" in config_dict:
        parameters = {}
        config_params = config_dict["Parameters"]
        if "LiteralValues" in config_params:
            parameters.update(config_params["LiteralValues"])

        if "EnvironmentalValues" in config_params:
            duplicate_parameters = [key for key in config_params["EnvironmentalValues"].keys() if key in config_params]
            if duplicate_parameters:
                raise Exception("There are duplicate parameters in the config file. Check these variables {}".format(duplicate_parameters))

            try:
                parameters.update({key: os.environ[value] for key, value in config_params["EnvironmentalValues"].items()})
            except Exception as e:
                logger.error("Error trying to retrieve environmental variable")
                raise e

        if "CLIRequested" in config_params:
            duplicate_parameters = [key for key in config_params["CLIRequested"] if key in config_params]
            if duplicate_parameters:
                raise Exception("There are duplicate parameters in the config file. Check these variables {}".format(duplicate_parameters))

            try:
                previous_values = {item["ParameterKey"]: item["ParameterValue"] for item in
                                  cf.describe_stacks(StackName=calculated_parameters['StackName'])["Stacks"][0]["Parameters"]}
                logger.debug("Previous parameters are: {}".format(previous_values))
            except Exception as e:
                logger.warning("Raising error '{}' when retrieving previous values of CLIRequested parameters".format(e))
                previous_values = {}

            for param in config_params["CLIRequested"]:
                if param in previous_values and previous_values[param] != '****':
                    keep_previous_value = request_yes_or_no_to_user("Parameter '{}' was provided in previous deployment. Keep previous value?".format(param))
                    if keep_previous_value:
                        value = previous_values[param]
                    else:
                        value = input("Add new value for parameter '{}':".format(param))
                else:
                    value = input("Parameter '{}' is required to be added in the terminal, please provide the value:".format(param))
                parameters.update({param: value})

        if "CloudFormationExports" in config_params:
            duplicate_parameters = [key for key in config_params["CloudFormationExports"].keys() if key in config_params]
            if duplicate_parameters:
                raise Exception("There are duplicate parameters in the config file. Check these variables {}".format(duplicate_parameters))

            try:
                cloudformation_exports = fetch_cloudformation_exports(cf_client=cf)
                parameters.update({key: cloudformation_exports[value] for key, value in config_params["CloudFormationExports"].items()})
            except Exception as e:
                logger.error("Error trying to retrieve cloudformation export")
                raise e

        calculated_parameters["Parameters"] = [{"ParameterKey": key, "ParameterValue": value} for key, value in parameters.items()]

    if "Tags" in config_dict:
        tags = {}
        config_tags = config_dict["Tags"]
        if "LiteralValues" in config_tags:
            tags.update(config_tags["LiteralValues"])

        if "EnvironmentalValues" in config_tags:
            duplicate_parameters = [key for key in config_tags["EnvironmentalValues"].keys() if key in config_tags]
            if duplicate_parameters:
                raise Exception("There are duplicate tags in the config file. Check these variables {}".format(duplicate_parameters))
            try:
                tags.update({key: os.environ[value] for key, value in config_tags["EnvironmentalValues"].items()})
            except Exception as e:
                logger.error("Error trying to retrieve environmental variable")
                raise e

        if "CloudFormationExports" in config_tags:
            duplicate_parameters = [key for key in config_tags["CloudFormationExports"].keys() if key in config_tags]
            if duplicate_parameters:
                raise Exception("There are duplicate tags in the config file. Check these variables {}".format(duplicate_parameters))

            try:
                cloudformation_exports = fetch_cloudformation_exports(cf_client=cf)
                tags.update({key: cloudformation_exports[value] for key, value in config_tags["CloudFormationExports"].items()})
            except Exception as e:
                logger.error("Error trying to retrieve cloudformation export")
                raise e

        if "Capabilities" in config_dict:
            calculated_parameters["Capabilities"] = config_dict["Capabilities"]

        calculated_parameters["Tags"] = [{"Key": key, "Value": value} for key, value in tags.items()]

    logger.debug("Explicit parameters are {}".format(calculated_parameters))

    return calculated_parameters, cf


def deployment(template_body, parameters, cf_client, ask_for_changes: bool, logger: logging.Logger):

    triggered_error = False
    try:
        response = cf_client.describe_stacks(StackName=parameters['StackName'])
    except cf_client.exceptions.ClientError:
        stack_exists = False
        triggered_error = True

    if not triggered_error:
        for stack in response["Stacks"]:
            if stack["StackName"]:
                if "IN_PROGRESS" in stack["StackStatus"]:
                    raise Exception("Cloudformation is performing {} over stack {}. Deployment can not continue...".format(stack["StackStatus"], parameters['StackName']))
            if "ROLLBACK_COMPLETE" == stack["StackStatus"]:
                remove_previous_stack = request_yes_or_no_to_user("Stack '{}' was deployed previously for first time but failed. It needs to be removed before deploying it again. Should it be removed?")
                if remove_previous_stack:
                    logger.info("Removing previous stack...")
                    cf_client.delete_stack(StackName=parameters['StackName'])
                    cf_client.get_waiter('stack_delete_complete').wait(StackName=parameters['StackName'])
                    logger.info("Removal has been completed!")
                    stack_exists = False
                    break
            if "COMPLETE" in stack["StackStatus"] or "FAILED" in stack["StackStatus"]:
                stack_exists = True
                break

    if not stack_exists:
        logger.warning('Stack "{}" does not exists. Creating it...'.format(parameters['StackName']))
        cf_client.create_stack(
            TemplateBody=template_body,
            **parameters)
        cf_client.get_waiter('stack_create_complete').wait(StackName=parameters['StackName'])
    else:
        # As stack exists, it will create a stackset to allow reviewing the changes
        change_set_name = 'change-set-{}-{}'.format(datetime.datetime.now().strftime("%Y%m%dT%H%M%S%ZZ"), parameters["StackName"])
        response = cf_client.create_change_set(
            ChangeSetName=change_set_name,
            ChangeSetType='UPDATE',
            TemplateBody=template_body,
            **parameters)  # parameters <= "Parameters", "StackName", "Tags", ...

        change_set_id, stack_id = response["Id"], response["StackId"]
        logger.debug("Response from create_change_set was '{}'".format(response))

        try:
            cf_client.get_waiter('change_set_create_complete').wait(ChangeSetName=change_set_name, StackName=parameters["StackName"])
        except Exception as e:
            response = cf_client.list_change_sets(StackName=parameters["StackName"])

            summary = [s for s in response["Summaries"] if s["ChangeSetId"] == change_set_id][0]

            if summary:
                logger.info("Change set has the status '{}' with the reason '{}'".format(summary["Status"], summary["StatusReason"]))
                if summary["Status"] == "FAILED":
                    cf_client.delete_change_set(ChangeSetName=change_set_id, StackName=parameters["StackName"])
                    logger.info("Removing change set. No changes to apply!")
                    return True
            else:
                raise e

        response_create_change_set = cf_client.describe_change_set(
            ChangeSetName=change_set_name,
            StackName=parameters['StackName'])

        ascii_tab = texttable.Texttable()
        table_headings = ['Action', 'LogicalResourceId', 'PhysicalResourceId', 'Replacement']
        ascii_tab.header(table_headings)

        logger.debug("Changes from change set are specified as {}".format(response_create_change_set))
        for change_object in response_create_change_set['Changes']:
            c = change_object['ResourceChange']
            ascii_tab.add_row([c['Action'],
                               c['LogicalResourceId'],
                               c['PhysicalResourceId'] if 'PhysicalResourceId' in c else '',
                               c['Replacement'] if 'Replacement' in c else ''])

        if not response_create_change_set['Changes']:
            logger.info('There are no detected changes in the change set. Perhaps the value of some tags changed.')
            logger.info('The new ones are: "{}"'.format(parameters["Tags"]))
        else:
            logger.info('Changes detected are:')
            table_string = ascii_tab.draw()
            print(table_string)

        if ask_for_changes:
            if not request_confirmation('Do you want to deploy this changes?'):
                logger.error('Change set execution aborted by user.')
                logger.info("Removing change set...")
                cf_client.delete_change_set(ChangeSetName=change_set_id, StackName=parameters["StackName"])
                logger.info("Done!")
                exit(0)

        logger.info("Applying changes in '{}' stack".format(parameters['StackName']))

        cf_client.execute_change_set(
            ChangeSetName=change_set_name,
            StackName=parameters["StackName"]
        )

        cf_client.get_waiter('stack_update_complete').wait(StackName=parameters["StackName"])
        logger.info("Stack {} was successfully updated".format(parameters["StackName"]))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Deploying CloudFormation stacks through an easy way. Current version: {}'.format(CFM_VERSION))
    parser.add_argument('template_folders', metavar='folder', nargs='+', help='list of template folders that contain the CloudFormation template file (template.yml) and params files (config.yml) to deploy sequentially')
    parser.add_argument('-a', '--ask', action='store_true', help='Flag to ask for applying modifications')
    parser.add_argument('-d', '--debug', action='store_true', help='Show debug traces and logs')
    args = parser.parse_args()

    # Configure logger
    logger = logging.Logger(name="cloudformation_manager-v" + CFM_VERSION, level=logging.DEBUG if args.debug else logging.INFO)
    streamer = logging.StreamHandler()
    streamer.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)s in %(name)s: %(message)s'))
    logger.addHandler(streamer)
    current_dir = os.getcwd()

    logger.info("Starting process, checking the configuration file...")

    try:
        for folder_path in args.template_folders:
            absolute_path = os.path.join(current_dir, folder_path) if folder_path[0] != "/" else folder_path
            template_body, config_dict, config_file_path = validate_files(absolute_path, logger=logger)
            applied_parameters, cf_client = calculate_parameters(config_dict=config_dict, config_file_path=config_file_path, logger=logger)
            deployment(template_body, parameters=applied_parameters, ask_for_changes=args.ask, cf_client=cf_client, logger=logger)
            logger.info("{} was deployed".format(applied_parameters["StackName"]))
    except Exception as e:
        if args.debug:
            logger.exception(e)
        else:
            logger.error(e)
        logger.error("Deployment has failed due to an exception")
        exit(1)

    logger.info("Stacks were deployed successfully")
