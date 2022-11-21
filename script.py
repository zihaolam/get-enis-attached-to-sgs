import json
import traceback
from typing import Dict, List, Optional, Union
import boto3


def start_session(aws_access_key_id: Optional[str] = None,
                  aws_secret_access_key: Optional[str] = None, profile_name: Optional[str] = None) -> boto3.Session:
    if aws_access_key_id is None and aws_secret_access_key is None:
        if profile_name is None:
            return boto3.Session()

        else:
            return boto3.Session(profile_name=profile_name)

    return boto3.Session(
        aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)


def get_credentials_input():
    profile_name = None
    aws_access_key_id = None
    aws_secret_access_key = None
    aws_configure_check = input(
        "Is your aws-cli setup with 'aws configure'? Y/N: [Y]").lower()

    while aws_configure_check != "y" and aws_configure_check != "n" and aws_configure_check != "":
        print("Invalid input, please select Y/N")
        aws_configure_check = input(
            "Is your aws-cli setup with 'aws configure'? Y/N ").lower()

    if aws_configure_check == "y" or aws_configure_check == "":
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


def get_and_verify_sg_input(session: boto3.Session) -> Union[str, List[str], None]:
    security_group_input = input(
        "Input security group id [example: sg-140123123], if there are multiple, delimit with a comma [example: sg-140123123,sg-398138123,sg-3912931]: ")

    security_group_ids = []
    if security_group_input.find(',') != '-1':
        security_group_ids.extend(security_group_input.split(','))
        sg_input_valid = verify_sg_input(session, security_group_ids)

        if sg_input_valid:
            return security_group_ids

        else:
            print(
                f"One of the Security Group ID {security_group_ids} is invalid")

    else:
        security_group_ids.append(security_group_input)

    return security_group_ids


def filter_response(data: Dict[str, any], wanted_fields: List[str]) -> dict:
    return {key: value for key, value in data.items() if key in wanted_fields}


def generate_eni_link(eni_id: str, region: str) -> str:
    return f"https://{region}.console.aws.amazon.com/ec2/home?region={region}#NetworkInterface:networkInterfaceId={eni_id}"


def describe_network_interface(session: boto3.Session, security_group_id: List[str]):
    response = session.client('ec2').describe_network_interfaces(
        Filters=[
            {
                'Name': 'group-id',
                'Values':
                    security_group_id
            },
        ],
    )

    response_fields = ['AvailabilityZone', 'Description', 'InterfaceType', 'NetworkInterfaceId', 'OwnerId',
                       'Status', 'VpcId']
    # available options: ['Attachment', 'AvailabilityZone', 'Description', 'Groups', 'InterfaceType', 'Ipv6Addresses', 'MacAddress', 'NetworkInterfaceId', 'OwnerId', 'PrivateIpAddress', 'PrivateIpAddresses', 'RequesterId', 'RequesterManaged', 'SourceDestCheck', 'Status', 'SubnetId', 'TagSet', 'VpcId', 'DenyAllIgwTraffic']
    # edit response_fields with fields that you want

    print(json.dumps(
        [dict(**filter_response(eni, response_fields), View=generate_eni_link(eni["NetworkInterfaceId"], boto3_session.region_name)) for eni in response["NetworkInterfaces"]], indent=4, default=str))


# --filters Name = group-id, Values = <security-group-id >

if __name__ == "__main__":
    print("Running script to get attached ENI...")
    try:
        profile_name, aws_access_key_id, aws_secret_access_key = get_credentials_input()

        if aws_access_key_id is not None and aws_secret_access_key is not None:
            boto3_session = start_session(
                aws_access_key_id, aws_secret_access_key)

        else:
            boto3_session = start_session(profile_name=profile_name)

        sg_ids = get_and_verify_sg_input(boto3_session)
        describe_network_interface(boto3_session, sg_ids)

    except Exception as e:
        traceback.print_exc()
        exit(0)
