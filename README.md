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
The program can be used in the following way:

    cloudformation-manager [YOUR_FOLDER_PATH_WITH_CLOUDFORMATION_FILES]

where the folder specified as argument contains two files: a config.yml and a template.yml

## Example
The following example creates two stacks from the templates stored in the example folder.

The first stack creates a sns topic to the email specified in terminal (change the [template](example/1_sns/config.yml) to add it as a literal if you prefer).
The second stack uses the exported variables created in the first stack (without being hard-linked as [import value does](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/intrinsic-function-reference-importvalue.html)).

    cloudformation-manager ~/WORKSPACE/cloudformation-manager/example/1_sns ~/WORKSPACE/cloudformation-manager/example/2_bucket
