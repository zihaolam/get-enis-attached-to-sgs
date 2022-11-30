import traceback
from typing import List, Optional
import boto3

from helpers import input_y_n


def start_session(aws_access_key_id: Optional[str] = None,
                  aws_secret_access_key: Optional[str] = None, profile_name: Optional[str] = None, region_name: Optional[str] = None) -> boto3.Session:
    if aws_access_key_id is None and aws_secret_access_key is None:
        if profile_name is None:
            return boto3.Session(region_name)

        else:
            return boto3.Session(profile_name=profile_name)

    return boto3.Session(
        aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key, region_name=region_name)


def get_credentials_input():
    profile_name = None
    aws_access_key_id = None
    aws_secret_access_key = None
    region_name = None
    aws_is_configured = input_y_n(
        "Is your aws-cli setup with 'aws configure'? ")

    if aws_is_configured:
        profile_name_input = input("Enter Profile name: [default]")
        if profile_name_input:
            profile_name = profile_name_input

    else:
        aws_access_key_id = input("Enter AWS Access Key ID: ")
        aws_secret_access_key = input("Enter AWS Secret Access Key: ")
        region_name = input("Enter region: [ap-southeast-1]")

    try:
        if aws_access_key_id is not None and aws_secret_access_key is not None:
            session = start_session(
                aws_access_key_id, aws_secret_access_key, region_name)

        else:
            session = start_session(
                profile_name=profile_name, region_name=region_name)

    except Exception as e:
        traceback.print_exc()
        exit(0)

    return session


def verify_sg_input(session: boto3.Session, security_group_ids: List[str]) -> bool:
    # boto3 sends api call to check if sg exists, if does not exist then raises botocore.exceptions.ClientError
    session.client('ec2').describe_security_groups(
        GroupIds=security_group_ids)

    return security_group_ids
