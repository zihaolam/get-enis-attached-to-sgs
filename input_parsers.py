from typing import List
import boto3

from helpers import input_y_n


def get_credentials_input():
    profile_name = None
    aws_access_key_id = None
    aws_secret_access_key = None
    aws_is_configured = input_y_n(
        "Is your aws-cli setup with 'aws configure'? ")

    if aws_is_configured:
        profile_name_input = input("Enter Profile name: [default]")
        if profile_name_input:
            profile_name = profile_name_input
    else:
        aws_access_key_id = input("Enter AWS Access Key ID: ")
        aws_secret_access_key = input("Enter AWS Secret Access Key: ")

    return profile_name, aws_access_key_id, aws_secret_access_key


def verify_sg_input(session: boto3.Session, security_group_ids: List[str]) -> bool:
    # boto3 sends api call to check if sg exists, if does not exist then raises botocore.exceptions.ClientError
    session.client('ec2').describe_security_groups(
        GroupIds=security_group_ids)

    return security_group_ids
