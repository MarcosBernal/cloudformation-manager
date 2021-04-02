# Overview

Deploying CloudFormation stacks through an easy way

## Requirements

- Access to the aws account though awscli. Tools such as [aws-vault](https://github.com/99designs/aws-vault) are a nice option to consider
- Python dependencies located in *requirements.txt* they might be installed with the command:
    - `python3 -m pip install --user -r requirements.txt`

## Use

    # After cloning/downloading this repo
    git clone https://github.com/MarcosBernal/cloudformation-manager ~/WORKSPACE/cloudformation-manager
    cd ~/WORKSPACE/cloudformation-manager
    python3 cloudformation_manager.py [YOUR_PATH_FOLDER_WITH_CLOUDFORMATION_FILES]

    # Alternatively a linked executable file can be created. In a debian based OS might be achieved with:
    sudo ln -s ~/WORKSPACE/cloudformation-manager/cloudformation_manager.py /usr/local/bin/cloudformation-manager
    cloudformation-manager [YOUR_PATH_FOLDER_WITH_CLOUDFORMATION_FILES]
