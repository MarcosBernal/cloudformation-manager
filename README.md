# Overview

Deploying CloudFormation stacks through an easy way

## Requirements

- Access to the aws account though awscli. Tools such as [aws-vault](https://github.com/99designs/aws-vault) are a nice option to consider
- Python dependencies located in *requirements.txt* they might be installed with the command:
    - `python3 -m pip install --user -r requirements.txt`

## Installation on linux environment

    # Clone/download this repo
    git clone https://github.com/MarcosBernal/cloudformation-manager ~/WORKSPACE/cloudformation-manager
    # Alternatively a linked executable file can be created. In a debian based OS might be achieved with:
    sudo ln -s ~/WORKSPACE/cloudformation-manager/cloudformation_manager.py /usr/local/bin/cloudformation-manager

Tested on debian (ubuntu 18.04)

## Use
    cloudformation-manager [YOUR_PATH_FOLDER_WITH_CLOUDFORMATION_FILES]

## Example
The following example creates two stacks from the templates stored in the example folder.

The first stack creates a sns topic to the email specified in the [template](example/1_sns/config.yml) (change it to your own email)
The second stack uses the exported variables created in the first stack to show how they can be connected.

    cloudformation-manager ~/WORKSPACE/cloudformation-manager/example/1_sns ~/WORKSPACE/cloudformation-manager/example/2_bucket
